import json

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.document_catalog_service import DocumentCatalogService
from app.services.tracegraph_service import TraceGraphService


class FakeWorkflow:
    def __init__(self, complex_query=False):
        self.complex_query = complex_query
        self.input = None

    def stream(self, state, stream_mode):
        self.input = state
        retrieval = {
            "retrieval_route": "fused" if self.complex_query else "hybrid",
            "routing_strategy": "adaptive_evidence",
            "routing_reason": "Both evidence channels were useful." if self.complex_query else "Document evidence was useful.",
            "research_context": "[Evidence 1]\ntext",
            "retrieved_chunk_ids": ["chunk-1"],
            "evidence_items": [],
            "query_embedding_latency_ms": 123.0,
            "reranker_latency_ms": 456.0,
            "reranker_input_count": 5,
            "reranker_total_chars": 6789,
            "reranker_max_chars": 2345,
            "decomposition_used": self.complex_query,
            "subquestions": ([
                {"id": "q1", "question": "Find the method", "route": "hybrid", "evidence_count": 1},
                {"id": "q2", "question": "Find its creator", "route": "graph", "evidence_count": 1},
            ] if self.complex_query else []),
        }
        yield {"adaptive_retrieval": retrieval}
        yield {"research_agent": {"draft_answer": "private draft", "used_evidence_labels": ["Evidence 1"]}}
        yield {"verification_agent": {
            "verification_passed": True,
            "verification_reason": "Supported.",
            "final_answer": "verified answer",
        }}


def service(complex_query=False):
    instance = TraceGraphService.__new__(TraceGraphService)
    instance.workflow = FakeWorkflow(complex_query)
    instance._validate_document_ids = lambda ids: None
    return instance


@pytest.fixture
def empty_document_catalog(monkeypatch):
    monkeypatch.setattr(
        DocumentCatalogService,
        "list_documents",
        lambda self: [],
    )


def test_service_event_order_and_verified_answer_is_terminal(empty_document_catalog):
    instance = service()
    events = list(instance.stream_events("question", ["doc-1"]))
    assert [event["type"] for event in events] == [
        "retrieval", "routing", "research", "research",
        "verification", "verification", "completed",
    ]
    assert all("private draft" not in json.dumps(event) for event in events[:-1])
    assert events[-1]["response"]["answer"] == "verified answer"
    response = events[-1]["response"]
    assert response["query_embedding_latency_ms"] == 123.0
    assert response["reranker_latency_ms"] == 456.0
    assert response["reranker_input_count"] == 5
    assert response["reranker_total_chars"] == 6789
    assert response["reranker_max_chars"] == 2345
    assert instance.workflow.input["document_ids"] == ["doc-1"]
    assert not any(event["type"] == "decomposition" for event in events)


def test_complex_service_events_include_decomposition_and_subquestions(
    empty_document_catalog,
):
    events = list(service(True).stream_events("complex question"))
    assert [event["type"] for event in events].count("decomposition") == 1
    subquestions = [event for event in events if event["type"] == "subquestion"]
    assert [(event["id"], event["route"]) for event in subquestions] == [
        ("q1", "hybrid"), ("q2", "graph")
    ]


def test_stream_endpoint_has_typed_sse_and_safe_error(monkeypatch):
    class FailingService:
        def stream_events(self, *args, **kwargs):
            raise RuntimeError("secret database detail")

    monkeypatch.setattr(
        "app.api.routes.chat.get_tracegraph_service",
        lambda: FailingService(),
    )
    with TestClient(app) as client:
        response = client.post("/api/chat/stream", json={"question": "hello"})
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: started" in response.text
    assert "event: error" in response.text
    assert "secret database detail" not in response.text
