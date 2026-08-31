import json
import logging
import inspect
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient
from google.genai import errors

from app.core.config import Settings, settings
from app.core.observability import (
    JsonFormatter,
    RequestContextMiddleware,
    get_request_id,
    log_event,
    run_with_request_id,
    configure_logging,
)
from app.graph.extractor import GraphExtractor
from app.services.document_indexing_service import DocumentIndexingService
from app.core.provider_resilience import call_with_provider_resilience
from app.main import create_app


@pytest.fixture(autouse=True)
def capture_application_logs(caplog):
    loggers = [logging.getLogger("app"), logging.getLogger("tracegraph")]
    for application_logger in loggers:
        application_logger.addHandler(caplog.handler)
    try:
        yield
    finally:
        for application_logger in loggers:
            application_logger.removeHandler(caplog.handler)


def test_request_without_id_gets_generated_header():
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        response = client.get("/")
    assert response.headers["x-request-id"]
    assert len(response.headers["x-request-id"]) == 36


def test_valid_incoming_request_id_is_preserved():
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        response = client.get("/", headers={"X-Request-ID": "safe.id-_123"})
    assert response.headers["x-request-id"] == "safe.id-_123"


def test_invalid_incoming_request_id_is_replaced():
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        response = client.get("/", headers={"X-Request-ID": "unsafe value\n"})
    assert response.headers["x-request-id"] != "unsafe value\n"


def test_oversized_incoming_request_id_is_replaced():
    incoming = "a" * 129
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        response = client.get("/", headers={"X-Request-ID": incoming})
    assert response.headers["x-request-id"] != incoming


def test_request_log_has_id_and_latency(caplog):
    caplog.set_level(logging.INFO, logger="tracegraph.http")
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        response = client.get("/", headers={"X-Request-ID": "correlation-1"})
    record = next(record for record in caplog.records if record.message == "request_completed")
    assert record.structured_fields["request_id"] == "correlation-1"
    assert record.structured_fields["latency_ms"] >= 0
    assert response.headers["x-request-id"] == "correlation-1"


def test_generated_ids_are_unique_and_context_does_not_leak(caplog):
    caplog.set_level(logging.INFO, logger="tracegraph.http")
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        first = client.get("/")
        second = client.get("/")
    assert first.headers["x-request-id"] != second.headers["x-request-id"]
    assert get_request_id() is None


def test_stream_and_worker_use_http_request_id(monkeypatch):
    seen = []

    class Service:
        def stream_events(self, *args, **kwargs):
            seen.append(get_request_id())
            yield {"type": "completed", "status": "complete", "message": "done", "response": {"answer": "ok"}}

    monkeypatch.setattr("app.api.routes.chat.get_tracegraph_service", lambda: Service())
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        response = client.post("/api/chat/stream", headers={"X-Request-ID": "stream-123"}, json={"question": "private question"})
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert response.headers["x-request-id"] == "stream-123"
    assert all(event["request_id"] == "stream-123" for event in events)
    assert seen == ["stream-123"]


def test_thread_context_helper_restores_context():
    assert run_with_request_id("worker-id", get_request_id) == "worker-id"
    assert get_request_id() is None


def test_upload_completion_log_includes_document_id(monkeypatch, caplog):
    result = SimpleNamespace(
        document_id="doc-safe-1", filename="private.txt", file_type="txt", title="title",
        ontology_profile="general", ontology_version="1", ontology_profiles=["general"],
        ontology_confidence=1.0, ontology_method="deterministic", ontology_reason="test", ontology_scores={},
        chunk_count=1, graph_entity_count=0, graph_relationship_count=0, qdrant_indexed_chunks=1,
        graph_rejected_relationship_count=0, graph_cached_chunks=0, graph_extracted_chunks=1,
    )
    monkeypatch.setattr("app.api.routes.documents.DocumentIndexingService", lambda: SimpleNamespace(index_file=lambda path: result))
    caplog.set_level(logging.INFO, logger="app.api.routes.documents")
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        response = client.post("/api/documents", files={"file": ("private.txt", b"private document body", "text/plain")})
    assert response.status_code == 201
    record = next(record for record in caplog.records if record.message == "document_ingestion_completed")
    assert record.structured_fields["document_id"] == "doc-safe-1"
    rendered = "\n".join(JsonFormatter().format(item) for item in caplog.records)
    assert "private.txt" not in rendered
    assert "private document body" not in rendered


def test_chat_logs_exclude_question_and_evidence(monkeypatch, caplog):
    secret_question = "raw-question-must-not-appear"
    secret_evidence = "raw-evidence-must-not-appear"
    response = {
        "answer": "safe", "route": "hybrid", "strategy": "adaptive_evidence",
        "initial_route": "hybrid", "final_route": "hybrid", "hybrid_evidence_count": 1,
        "graph_evidence_count": 0, "requires_decomposition": False, "degraded": False,
        "decomposition_used": False, "decomposition_degraded": False, "decomposition_call_count": 0,
        "subquestion_count": 0, "subquestions": [], "qdrant_call_count": 1, "neo4j_call_count": 0,
        "crossencoder_call_count": 1, "evidence_items": [], "answer_status": "verified_abstention",
        "verified": True, "retry_count": 0, "retrieved_chunk_ids": [], "graph_fact_count": 0,
        "used_evidence_labels": [], "document_ids": None,
    }
    monkeypatch.setattr("app.api.routes.chat.get_tracegraph_service", lambda: SimpleNamespace(ask=lambda **kwargs: response))
    caplog.set_level(logging.INFO)
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        result = client.post("/api/chat", json={"question": secret_question})
    rendered = "\n".join(
        JsonFormatter().format(record)
        for record in caplog.records
        if record.name.startswith("tracegraph.") or record.name.startswith("app.")
    )
    assert result.status_code == 200
    assert secret_question not in rendered
    assert secret_evidence not in rendered


def test_provider_retry_log_is_safe(monkeypatch, caplog):
    monkeypatch.setattr(settings, "provider_retry_base_delay_seconds", 0.0)
    monkeypatch.setattr(settings, "provider_retry_max_delay_seconds", 0.0)
    provider_body = "provider-body-secret"
    failures = [errors.ServerError(503, {"message": provider_body}, httpx.Response(503)), "ok"]
    caplog.set_level(logging.WARNING, logger="app.core.provider_resilience")

    def operation():
        value = failures.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    assert call_with_provider_resilience(operation, sleep=lambda _: None) == "ok"
    record = next(record for record in caplog.records if record.message == "provider_retry")
    assert record.structured_fields["attempt"] == 2
    assert record.structured_fields["status_code"] == 503
    assert provider_body not in JsonFormatter().format(record)


def test_headers_and_query_values_are_not_logged(caplog):
    api_key = "api-key-like-secret"
    password = "password-like-secret"
    caplog.set_level(logging.INFO, logger="tracegraph.http")
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        client.get(f"/?password={password}", headers={"Authorization": f"Bearer {api_key}"})
    rendered = "\n".join(
        JsonFormatter().format(record)
        for record in caplog.records
        if record.name == "tracegraph.http"
    )
    assert api_key not in rendered
    assert password not in rendered


def test_successful_health_is_suppressed(caplog):
    caplog.set_level(logging.INFO, logger="tracegraph.http")
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        assert client.get("/health").status_code == 200
    assert not any(record.message == "request_completed" for record in caplog.records)


def test_successful_ready_is_suppressed(caplog):
    application = FastAPI()
    application.add_middleware(RequestContextMiddleware)

    @application.get("/ready")
    def ready():
        return {"status": "ready"}

    caplog.set_level(logging.INFO, logger="tracegraph.http")
    with TestClient(application) as client:
        assert client.get("/ready").status_code == 200
    assert not any(record.message == "request_completed" for record in caplog.records)


def test_exception_log_contains_type_not_message(caplog):
    application = FastAPI()
    application.add_middleware(RequestContextMiddleware)

    @application.get("/failure")
    def failure():
        raise RuntimeError("sensitive exception detail")

    caplog.set_level(logging.ERROR, logger="tracegraph.http")
    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/failure")
    rendered = "\n".join(JsonFormatter().format(record) for record in caplog.records)
    assert response.status_code == 500
    assert "RuntimeError" in rendered
    assert "sensitive exception detail" not in rendered
    assert get_request_id() is None


def test_unknown_and_sensitive_structured_fields_are_dropped():
    logger = logging.getLogger("app.safety-test")
    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = Capture()
    logger.addHandler(handler)
    try:
        log_event(
            logger,
            logging.INFO,
            "safe_event",
            operation="test",
            unknown_field="must-not-appear",
            password="password-marker",
            api_key="api-key-marker",
            question="question-marker",
        )
    finally:
        logger.removeHandler(handler)
    rendered = JsonFormatter().format(records[0])
    assert json.loads(rendered)["operation"] == "test"
    assert "must-not-appear" not in rendered
    assert "password-marker" not in rendered
    assert "api-key-marker" not in rendered
    assert "question-marker" not in rendered


def test_document_derived_graph_and_ontology_values_are_not_logged():
    extractor_source = inspect.getsource(GraphExtractor)
    indexing_source = inspect.getsource(DocumentIndexingService)
    assert "print(" not in extractor_source
    assert "print(" not in indexing_source


def test_application_logging_is_configured_once_without_propagation():
    configure_logging("INFO")
    configure_logging("INFO")
    for logger_name in ("app", "tracegraph"):
        application_logger = logging.getLogger(logger_name)
        handlers = [
            handler
            for handler in application_logger.handlers
            if getattr(handler, "tracegraph_json", False)
        ]
        assert len(handlers) == 1
        assert application_logger.propagate is False


def test_application_response_request_id_is_replaced_without_duplicates():
    application = FastAPI()
    application.add_middleware(RequestContextMiddleware)

    @application.get("/header")
    def header():
        return PlainTextResponse("ok", headers={"X-Request-ID": "application-id"})

    with TestClient(application) as client:
        response = client.get("/header", headers={"X-Request-ID": "correlation-id"})
    assert response.headers.get_list("x-request-id") == ["correlation-id"]


def test_stream_order_is_preserved_with_correlated_request_id(monkeypatch):
    event_types = ["retrieval", "routing", "research", "verification", "completed"]

    class Service:
        def stream_events(self, *args, **kwargs):
            for event_type in event_types:
                payload = {"type": event_type, "status": "complete", "message": event_type}
                if event_type == "completed":
                    payload["response"] = {
                        "answer": "ok", "route": "hybrid", "strategy": "adaptive_evidence",
                        "initial_route": "hybrid", "final_route": "hybrid",
                        "hybrid_evidence_count": 0, "graph_evidence_count": 0,
                        "requires_decomposition": False, "degraded": False,
                        "decomposition_used": False, "decomposition_degraded": False,
                        "decomposition_call_count": 0, "subquestion_count": 0,
                        "subquestions": [], "qdrant_call_count": 1, "neo4j_call_count": 0,
                        "crossencoder_call_count": 0, "evidence_items": [],
                        "answer_status": "verified_answer", "verified": True,
                        "retry_count": 0, "retrieved_chunk_ids": [], "graph_fact_count": 0,
                        "used_evidence_labels": [], "document_ids": None,
                    }
                yield payload

    monkeypatch.setattr("app.api.routes.chat.get_tracegraph_service", lambda: Service())
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        response = client.post(
            "/api/chat/stream",
            headers={"X-Request-ID": "ordered-stream"},
            json={"question": "private"},
        )
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert [event["type"] for event in events] == ["started", *event_types]
    assert all(event["request_id"] == "ordered-stream" for event in events)


def test_json_formatter_emits_one_line_required_fields():
    logger = logging.getLogger("format-test")
    record = logger.makeRecord("format-test", logging.INFO, __file__, 1, "operation_done", (), None)
    record.structured_fields = {"request_id": "rid", "operation": "test", "status": "complete", "latency_ms": 1.5}
    rendered = JsonFormatter().format(record)
    payload = json.loads(rendered)
    assert "\n" not in rendered
    assert {"timestamp", "level", "message", "request_id", "operation", "status", "latency_ms"} <= payload.keys()
