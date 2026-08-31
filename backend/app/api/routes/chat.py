import asyncio
import logging
from threading import Event, Thread
from time import perf_counter

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import StreamingResponse
from google.genai.errors import (
    ClientError,
)

from app.api.chat_models import (
    ChatRequest,
    ChatResponse,
    ChatStreamEvent,
)
from app.services.tracegraph_service import (
    get_tracegraph_service,
)
from app.core.observability import log_event, run_with_request_id
from app.core.lifecycle import StreamWorker, stream_workers


router = APIRouter(
    prefix="/api",
    tags=["TraceGraph"],
)
logger = logging.getLogger(__name__)


def _sse(event: ChatStreamEvent) -> str:
    return f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"


@router.post("/chat/stream")
async def chat_stream(request_body: ChatRequest, request: Request):
    request_id = request.state.request_id
    queue: asyncio.Queue = asyncio.Queue()
    cancelled = Event()
    loop = asyncio.get_running_loop()
    terminal_event_type: str | None = None

    def publish(payload):
        nonlocal terminal_event_type
        if cancelled.is_set():
            return False
        event_type = payload.get("type")
        if event_type in {"completed", "error"}:
            if terminal_event_type is not None:
                return False
            terminal_event_type = event_type
        event = ChatStreamEvent(request_id=request_id, **payload)
        loop.call_soon_threadsafe(queue.put_nowait, event)
        return True

    def execute_stream():
        started = perf_counter()
        log_event(logger, logging.INFO, "stream_started", operation="chat_stream", status="started")
        try:
            service = get_tracegraph_service()
            for payload in service.stream_events(
                request_body.question,
                request_body.document_ids,
                cancelled,
            ):
                if cancelled.is_set():
                    break
                publish(payload)
                if payload.get("type") in {"completed", "error"}:
                    break
            if cancelled.is_set():
                log_event(logger, logging.INFO, "stream_worker_cancelled", operation="chat_stream", status="cancelled", latency_ms=round((perf_counter() - started) * 1000, 3))
            else:
                log_event(logger, logging.INFO, "stream_completed", operation="chat_stream", status="complete", latency_ms=round((perf_counter() - started) * 1000, 3))
        except Exception as exc:
            log_event(logger, logging.ERROR, "stream_error", operation="chat_stream", status="failed", error_type=type(exc).__name__, latency_ms=round((perf_counter() - started) * 1000, 3))
            if not cancelled.is_set():
                publish({
                    "type": "error",
                    "status": "failed",
                    "message": "TraceGraph could not complete this request.",
                })
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    def run():
        try:
            run_with_request_id(request_id, execute_stream)
        finally:
            stream_workers.unregister(worker)

    worker = Thread(target=run, daemon=True)

    async def events():
        if not stream_workers.register(StreamWorker(request_id, cancelled, worker)):
            cancelled.set()
            return
        worker.start()
        yield _sse(ChatStreamEvent(
            type="started",
            request_id=request_id,
            status="started",
            message="Understanding the question.",
        ))
        try:
            while True:
                if await request.is_disconnected():
                    cancelled.set()
                    log_event(logger, logging.INFO, "stream_disconnected", operation="chat_stream", status="cancelled")
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                if event is None:
                    break
                yield _sse(event)
        finally:
            cancelled.set()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
) -> ChatResponse:
    started = perf_counter()
    log_event(logger, logging.INFO, "chat_started", operation="chat", status="started")
    try:
        service = (
            get_tracegraph_service()
        )

        result = (
            service.ask(
                question=(
                    request.question
                ),

                document_ids=(
                    request.document_ids
                ),
            )
        )

        response = ChatResponse(
            **result
        )
        log_event(logger, logging.INFO, "chat_completed", operation="chat", status="complete", route=result.get("route"), degraded=result.get("degraded"), latency_ms=round((perf_counter() - started) * 1000, 3))
        return response

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                exc
            ),
        ) from exc

    except ClientError as exc:
        if (
            getattr(
                exc,
                "code",
                None,
            )
            == 429
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_503_SERVICE_UNAVAILABLE
                ),

                detail=(
                    "The AI provider is "
                    "temporarily rate limited. "
                    "Please try again shortly."
                ),
            ) from exc

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),

            detail=(
                "The AI provider returned "
                "an error."
            ),
        ) from exc

    except Exception as exc:
        log_event(logger, logging.ERROR, "chat_failed", operation="chat", status="failed", error_type=type(exc).__name__, latency_ms=round((perf_counter() - started) * 1000, 3))

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),

            detail=(
                "TraceGraph could not process "
                "the request."
            ),
        ) from exc
