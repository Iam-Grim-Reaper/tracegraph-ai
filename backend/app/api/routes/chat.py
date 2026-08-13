import asyncio
from threading import Event, Thread
from uuid import uuid4

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


router = APIRouter(
    prefix="/api",
    tags=["TraceGraph"],
)


def _sse(event: ChatStreamEvent) -> str:
    return f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"


@router.post("/chat/stream")
async def chat_stream(request_body: ChatRequest, request: Request):
    request_id = str(uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    cancelled = Event()
    loop = asyncio.get_running_loop()

    def publish(payload):
        event = ChatStreamEvent(request_id=request_id, **payload)
        loop.call_soon_threadsafe(queue.put_nowait, event)

    def run():
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
        except Exception:
            publish({
                "type": "error",
                "status": "failed",
                "message": "TraceGraph could not complete this request.",
            })
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    async def events():
        yield _sse(ChatStreamEvent(
            type="started",
            request_id=request_id,
            status="started",
            message="Understanding the question.",
        ))
        Thread(target=run, daemon=True).start()
        try:
            while True:
                if await request.is_disconnected():
                    cancelled.set()
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
            "X-Request-ID": request_id,
        },
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
) -> ChatResponse:
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

        return ChatResponse(
            **result
        )

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
        print(
            "TraceGraph chat error:",
            repr(
                exc
            ),
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),

            detail=(
                "TraceGraph could not process "
                "the request."
            ),
        ) from exc
