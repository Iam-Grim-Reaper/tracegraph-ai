"""Regression tests for low-latency, failure-tolerant adaptive execution."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.graph import store as graph_store_module
from app.agents import adaptive_retrieval as adaptive_module
from app.agents import workflow as workflow_module
from app.agents.query_decomposition import (
    ConditionalDecompositionRetriever,
    DecompositionPlan,
    SubQuestion,
)
from app.services.tracegraph_service import TraceGraphService


def test_neo4j_driver_uses_explicit_connection_budgets(monkeypatch):
    captured = {}

    class Driver:
        def close(self):
            pass

    def create_driver(uri, **kwargs):
        captured.update({"uri": uri, **kwargs})
        return Driver()

    config = Settings(
        _env_file=None,
        app_env="test",
        neo4j_uri="neo4j+s://example.invalid",
        neo4j_username="neo4j",
        neo4j_password="test",
        neo4j_connection_timeout_seconds=4.0,
        neo4j_acquisition_timeout_seconds=7.0,
        neo4j_max_transaction_retry_seconds=2.0,
    )
    monkeypatch.setattr(graph_store_module, "settings", config)
    monkeypatch.setattr(graph_store_module.GraphDatabase, "driver", create_driver)

    graph_store_module.Neo4jGraphStore().close()
    assert captured["connection_timeout"] == 4.0
    assert captured["connection_acquisition_timeout"] == 7.0
    assert captured["max_transaction_retry_time"] == 2.0


def test_neo4j_acquisition_budget_cannot_be_shorter_than_connection_budget():
    with pytest.raises(ValidationError, match="NEO4J_ACQUISITION_TIMEOUT_SECONDS"):
        Settings(
            _env_file=None,
            neo4j_connection_timeout_seconds=10.0,
            neo4j_acquisition_timeout_seconds=5.0,
        )


def test_adaptive_graph_client_does_not_verify_connectivity_at_startup(monkeypatch):
    class Store:
        def verify_connectivity(self):
            raise AssertionError("no eager graph network call")

    monkeypatch.setattr(adaptive_module, "GeminiEmbeddingService", lambda: object())
    monkeypatch.setattr(adaptive_module, "HybridStore", lambda: object())
    monkeypatch.setattr(adaptive_module, "Neo4jGraphStore", lambda: Store())

    node = adaptive_module.AdaptiveEvidenceRetriever()
    assert node.graph_retriever.store.__class__ is Store


def test_adaptive_workflow_does_not_construct_unused_legacy_clients(monkeypatch):
    def forbidden():
        raise AssertionError("legacy clients should not be initialized")

    class Agent:
        client = object()

        def __call__(self, state):
            return state

        def rewrite_for_retry(self, state):
            return state

    class Adaptive:
        def __call__(self, state):
            return state

    class Decomposition:
        def __init__(self):
            self.adaptive = SimpleNamespace(
                embedding_service=SimpleNamespace(client=object()),
                hybrid_store=SimpleNamespace(client=object()),
                graph_retriever=SimpleNamespace(store=object()),
            )
            self.decomposer = SimpleNamespace(client=object())

        def __call__(self, state):
            return state

    monkeypatch.setattr(workflow_module.settings, "query_routing_mode", "adaptive")
    monkeypatch.setattr(workflow_module, "RetrievalNodes", forbidden)
    monkeypatch.setattr(workflow_module, "RetrievalRouter", forbidden)
    monkeypatch.setattr(workflow_module, "ResearchAgent", Agent)
    monkeypatch.setattr(workflow_module, "VerificationAgent", Agent)
    monkeypatch.setattr(workflow_module, "ConditionalDecompositionRetriever", Decomposition)
    resources = []
    workflow = workflow_module.build_tracegraph_workflow(resources)
    assert workflow is not None
    assert len(resources) == 6


def test_partial_decomposition_never_becomes_fully_verified():
    result = TraceGraphService._serialize_result(
        {
            "verification_passed": True,
            "used_evidence_labels": ["Evidence q1-1"],
            "decomposition_degraded": True,
            "final_answer": "Partial response [Evidence q1-1]",
        },
        None,
    )
    assert result["answer_status"] == "partial_grounded_answer"


def test_decomposition_propagates_degraded_retrieval_channel():
    class Decomposer:
        def decompose(self, question):
            return DecompositionPlan(
                subquestions=[
                    SubQuestion(id="q1", question="Who developed it?"),
                    SubQuestion(id="q2", question="What is its purpose?"),
                ]
            )

    class Adaptive:
        _requires_decomposition = staticmethod(lambda question: True)

        def __call__(self, state):
            return {
                "retrieval_route": "hybrid",
                "degraded": True,
                "degradation_reason": "graph_unavailable",
                "research_context": "[Evidence 1]\\nsource",
                "retrieved_chunk_ids": ["chunk-1"],
                "evidence_items": [],
                "grounded_entities": [],
            }

    result = ConditionalDecompositionRetriever(Adaptive(), Decomposer())(
        {"question": "Which model and what does it do?"}
    )
    assert result["degraded"] is True
    assert result["degradation_reason"] == "graph_unavailable"
    assert result["decomposition_degraded"] is False
