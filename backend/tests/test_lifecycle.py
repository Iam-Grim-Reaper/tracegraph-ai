import json
import logging
from threading import Event, Lock, Thread
from time import monotonic
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.lifecycle import StreamWorker, StreamWorkerRegistry
from app.core.observability import JsonFormatter, get_request_id
from app.main import create_app
from app.services.tracegraph_service import TraceGraphService


def _service_with_resources(resources):
    service = TraceGraphService.__new__(TraceGraphService)
    service._owned_resources = resources
    service._close_lock = Lock()
    service._closed = False
    return service


def test_lifespan_starts_and_closes_service_once(monkeypatch):
    calls = []
    monkeypatch.setattr("app.main.close_tracegraph_service", lambda: calls.append("close"))
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        assert client.get("/health").status_code == 200
    assert calls == ["close"]


def test_resource_cleanup_is_idempotent_and_continues_after_failure():
    calls = []

    class Failing:
        def close(self):
            calls.append("failing")
            raise RuntimeError("private connection detail")

    class Later:
        def close(self):
            calls.append("later")

    service = _service_with_resources([Failing(), Later()])
    service.close()
    service.close()
    assert calls == ["failing", "later"]


def test_owned_qdrant_neo4j_and_supported_provider_clients_close():
    closed = []
    qdrant = SimpleNamespace(close=lambda: closed.append("qdrant"))
    neo4j = SimpleNamespace(close=lambda: closed.append("neo4j"))
    provider = SimpleNamespace(close=lambda: closed.append("provider"))
    unsupported_provider = object()
    _service_with_resources([qdrant, neo4j, provider, unsupported_provider]).close()
    assert closed == ["qdrant", "neo4j", "provider"]


def test_registry_registers_and_unregisters_without_request_content():
    registry = StreamWorkerRegistry()
    cancelled = Event()
    thread = Thread(target=lambda: None, daemon=True)
    worker = StreamWorker("safe-request-id", cancelled, thread)
    assert registry.register(worker)
    assert registry.active_workers() == (worker,)
    assert set(vars(worker)) == {"request_id", "cancelled", "thread"}
    registry.unregister(thread)
    assert registry.active_workers() == ()


def test_shutdown_signals_all_workers_and_rejects_new_registrations():
    registry = StreamWorkerRegistry()
    events = [Event(), Event()]
    threads = [Thread(target=lambda: None, daemon=True) for _ in events]
    for index, (event, thread) in enumerate(zip(events, threads)):
        assert registry.register(StreamWorker(f"request-{index}", event, thread))
    active, stopped, remaining = registry.shutdown(0)
    assert (active, stopped, remaining) == (2, 2, 0)
    assert all(event.is_set() for event in events)
    assert not registry.register(StreamWorker("late", Event(), Thread(target=lambda: None)))


def test_stuck_daemon_worker_cannot_block_bounded_shutdown():
    registry = StreamWorkerRegistry()
    release = Event()
    cancelled = Event()
    thread = Thread(target=release.wait, daemon=True)
    assert registry.register(StreamWorker("stuck", cancelled, thread))
    thread.start()
    started = monotonic()
    active, stopped, remaining = registry.shutdown(0.02)
    elapsed = monotonic() - started
    release.set()
    thread.join(1)
    registry.unregister(thread)
    assert (active, stopped, remaining) == (1, 0, 1)
    assert cancelled.is_set()
    assert elapsed < 0.5


def test_clean_worker_unregisters_even_when_service_raises(monkeypatch):
    from app.api.routes import chat as chat_route

    registry = StreamWorkerRegistry()
    monkeypatch.setattr(chat_route, "stream_workers", registry)

    class FailingService:
        def stream_events(self, *args, **kwargs):
            raise RuntimeError("private provider detail")
            yield

    monkeypatch.setattr(chat_route, "get_tracegraph_service", lambda: FailingService())
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        response = client.post(
            "/api/chat/stream",
            headers={"X-Request-ID": "error-stream"},
            json={"question": "private question"},
        )
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    terminal = [event["type"] for event in events if event["type"] in {"completed", "error"}]
    assert terminal == ["error"]
    assert registry.active_workers() == ()
    assert all(event["request_id"] == "error-stream" for event in events)


def test_normal_stream_has_one_completed_and_unregisters(monkeypatch):
    from app.api.routes import chat as chat_route

    registry = StreamWorkerRegistry()
    seen_request_ids = []
    monkeypatch.setattr(chat_route, "stream_workers", registry)

    class Service:
        def stream_events(self, *args, **kwargs):
            seen_request_ids.append(get_request_id())
            yield {"type": "research", "status": "complete", "message": "verified later"}
            yield {
                "type": "completed", "status": "complete", "message": "done",
                "response": {
                    "answer": "verified answer", "route": "hybrid", "strategy": "adaptive_evidence",
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
                },
            }

    monkeypatch.setattr(chat_route, "get_tracegraph_service", lambda: Service())
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        response = client.post(
            "/api/chat/stream",
            headers={"X-Request-ID": "complete-stream"},
            json={"question": "private question"},
        )
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    terminal = [event["type"] for event in events if event["type"] in {"completed", "error"}]
    assert terminal == ["completed"]
    assert events[-1]["response"]["answer"] == "verified answer"
    assert seen_request_ids == ["complete-stream"]
    assert registry.active_workers() == ()


def test_cancellation_checkpoint_prevents_completed_event():
    cancelled = Event()

    class Workflow:
        def stream(self, state, stream_mode):
            yield {"research_agent": {"draft_answer": "private draft"}}
            yield {"verification_agent": {"verification_passed": True}}

    service = TraceGraphService.__new__(TraceGraphService)
    service.workflow = Workflow()
    service._validate_document_ids = lambda ids: None
    events = service.stream_events("question", cancelled=cancelled)
    first = next(events)
    cancelled.set()
    assert first["type"] == "research"
    assert list(events) == []


def test_health_ready_and_request_id_regression(monkeypatch):
    monkeypatch.setattr("app.api.routes.health.readiness_failures", lambda settings: [])
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        health = client.get("/health", headers={"X-Request-ID": "lifecycle-check"})
        ready = client.get("/ready")
    assert health.status_code == 200
    assert health.headers.get_list("x-request-id") == ["lifecycle-check"]
    assert ready.status_code == 200
    assert ready.headers["x-request-id"]


def test_lifecycle_logs_are_structured_and_exclude_content(caplog):
    caplog.set_level(logging.INFO, logger="app.core.lifecycle")
    application_logger = logging.getLogger("app")
    application_logger.addHandler(caplog.handler)
    registry = StreamWorkerRegistry()
    marker = "private-question-document-evidence"
    try:
        thread = Thread(target=lambda: None, daemon=True)
        registry.register(StreamWorker("safe-lifecycle-id", Event(), thread))
        registry.unregister(thread)
    finally:
        application_logger.removeHandler(caplog.handler)
    rendered = "\n".join(JsonFormatter().format(record) for record in caplog.records)
    assert marker not in rendered
    assert "safe-lifecycle-id" in rendered
