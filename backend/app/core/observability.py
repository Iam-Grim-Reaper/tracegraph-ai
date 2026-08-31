import json
import logging
import re
from contextvars import ContextVar
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable, TypeVar
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send


_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
T = TypeVar("T")

SAFE_STRUCTURED_FIELDS = frozenset({
    "active_worker_count",
    "attempt",
    "chunk_count",
    "chunk_index",
    "classification_method",
    "degraded",
    "delay_ms",
    "document_id",
    "document_scope_count",
    "entity_count",
    "error_type",
    "graph_evidence_count",
    "hybrid_evidence_count",
    "latency_ms",
    "method",
    "model",
    "ontology_profile",
    "operation",
    "provider",
    "relationship_count",
    "remaining_worker_count",
    "request_id",
    "route",
    "status",
    "status_code",
    "verified",
    "workers_stopped",
})


def valid_request_id(value: str | None) -> bool:
    return bool(value and _REQUEST_ID_PATTERN.fullmatch(value))


def new_request_id(value: str | None = None) -> str:
    return value if valid_request_id(value) else str(uuid4())


def get_request_id() -> str | None:
    return _request_id.get()


def run_with_request_id(request_id: str, operation: Callable[[], T]) -> T:
    token = _request_id.set(request_id)
    try:
        return operation()
    finally:
        _request_id.reset(token)


def log_event(logger: logging.Logger, level: int, message: str, **fields: Any) -> None:
    values = {
        key: value
        for key, value in fields.items()
        if key in SAFE_STRUCTURED_FIELDS and value is not None
    }
    request_id = get_request_id()
    if request_id:
        values.setdefault("request_id", request_id)
    logger.log(level, message, extra={"structured_fields": values})


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        payload.update(getattr(record, "structured_fields", {}))
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging(level: str = "INFO") -> None:
    configured_level = getattr(logging, level.upper(), logging.INFO)
    for logger_name in ("app", "tracegraph"):
        application_logger = logging.getLogger(logger_name)
        application_logger.setLevel(configured_level)
        application_logger.propagate = False
        if any(
            getattr(handler, "tracegraph_json", False)
            for handler in application_logger.handlers
        ):
            continue
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler.tracegraph_json = True  # type: ignore[attr-defined]
        application_logger.addHandler(handler)


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = logging.getLogger("tracegraph.http")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        incoming = headers.get(b"x-request-id", b"").decode("ascii", errors="ignore")
        request_id = new_request_id(incoming)
        scope.setdefault("state", {})["request_id"] = request_id
        started = perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = [
                    header
                    for header in message.get("headers", [])
                    if header[0].lower() != b"x-request-id"
                ]
                response_headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = response_headers
            await send(message)

        token = _request_id.set(request_id)
        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception as exc:
            log_event(self.logger, logging.ERROR, "request_failed", operation="http_request", method=scope.get("method"), route=scope.get("path"), status="failed", error_type=type(exc).__name__)
            raise
        finally:
            latency_ms = round((perf_counter() - started) * 1000, 3)
            path = scope.get("path", "")
            if status_code >= 400 or path not in {"/health", "/ready"}:
                log_event(self.logger, logging.INFO if status_code < 500 else logging.ERROR, "request_completed", operation="http_request", method=scope.get("method"), route=path, status="success" if status_code < 400 else "failed", status_code=status_code, latency_ms=latency_ms)
            _request_id.reset(token)
