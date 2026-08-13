from types import SimpleNamespace

import pytest

from app.agents.adaptive_retrieval import (
    AdaptiveEvidenceRetriever,
    EvidenceArbitrator,
    EvidenceSignal,
)
from app.api.chat_models import ChatResponse
from app.graph.graph_query import GraphFact, GraphQueryResult
from app.graph.graph_query import GraphQueryRetriever


class FakeEmbeddingService:
    def __init__(self):
        self.calls = 0

    def embed_query(self, query):
        self.calls += 1
        return [0.1, 0.2]


class FakeHybridStore:
    def __init__(self, points=None, error=None):
        self.points = points or []
        self.error = error
        self.calls = 0
        self.document_ids = None

    def hybrid_search(self, **kwargs):
        self.calls += 1
        self.document_ids = kwargs["document_ids"]
        if self.error:
            raise self.error
        return self.points


class FakeGraphRetriever:
    def __init__(self, facts=None, error=None):
        self.facts = facts or []
        self.error = error
        self.calls = 0
        self.document_ids = None
        self.max_path_depth = None

    def retrieve(self, **kwargs):
        self.calls += 1
        self.document_ids = kwargs["document_ids"]
        self.max_path_depth = kwargs["max_path_depth"]
        if self.error:
            raise self.error
        return GraphQueryResult(kwargs["query"], [], self.facts)

    def retrieve_by_chunk_ids(self, **kwargs):
        self.document_ids = kwargs["document_ids"]
        return GraphQueryResult(kwargs["query"], [], self.facts)


class FakeReranker:
    def __init__(self, scores):
        self.scores = scores
        self.calls = 0
        self.texts = None

    def score_texts(self, query, texts):
        self.calls += 1
        self.texts = texts
        return self.scores[:len(texts)]


def point(text="text evidence"):
    return SimpleNamespace(
        id="chunk-1",
        payload={
            "text": text,
            "document_id": "doc-1",
            "filename": "sample.pdf",
            "page_number": 1,
            "chunk_index": 0,
        },
    )


def fact():
    return GraphFact(
        source_entity_id="method-1",
        source_name="Grad-CAM",
        source_type="Method",
        relationship_type="DEVELOPED_BY",
        target_entity_id="person-1",
        target_name="R. R. Selvaraju",
        target_type="Person",
        confidence=0.95,
        evidence_text="Grad-CAM was developed by Selvaraju et al.",
        source_document_id="doc-1",
        source_chunk_id="chunk-2",
        page_number=3,
        source_text="source",
    )


def build(hybrid_points, graph_facts, scores, hybrid_error=None, graph_error=None):
    embedding = FakeEmbeddingService()
    hybrid = FakeHybridStore(hybrid_points, hybrid_error)
    graph = FakeGraphRetriever(graph_facts, graph_error)
    reranker = FakeReranker(scores)
    node = AdaptiveEvidenceRetriever(embedding, hybrid, graph, reranker)
    return node, embedding, hybrid, graph, reranker


def strong(count=1):
    return EvidenceSignal(count, 5.0, 4.0, True)


def weak(count=0):
    return EvidenceSignal(count, None, None, False)


def test_arbitrator_channel_selection():
    arbitrator = EvidenceArbitrator()
    assert arbitrator.decide(strong(), weak(), False).route == "hybrid"
    assert arbitrator.decide(weak(), strong(), False).route == "graph"
    assert arbitrator.decide(strong(), strong(), False).route == "fused"
    assert arbitrator.decide(strong(), strong(), True).route == "fused"
    assert arbitrator.decide(weak(), weak(), False).route == "fused"


def test_arbitrator_selects_a_clearly_dominant_channel(monkeypatch):
    monkeypatch.setattr(
        "app.agents.adaptive_retrieval.settings.adaptive_evidence_dominance_margin",
        2.0,
    )
    arbitrator = EvidenceArbitrator()
    hybrid = EvidenceSignal(5, 0.5, 0.2, True)
    graph = EvidenceSignal(3, 4.0, 3.0, True)
    assert arbitrator.decide(hybrid, graph, False).route == "graph"
    assert arbitrator.decide(graph, hybrid, False).route == "hybrid"


def test_graph_fact_verbalization_preserves_fact():
    value = fact()
    text = AdaptiveEvidenceRetriever.verbalize_graph_fact(value)
    assert value.relationship_type == "DEVELOPED_BY"
    assert "Grad-CAM DEVELOPED_BY R. R. Selvaraju" in text
    assert value.evidence_text in text


def test_adaptive_retrieval_reuses_probes_and_scope(monkeypatch):
    monkeypatch.setattr(
        "app.agents.adaptive_retrieval.settings.adaptive_evidence_relevance_threshold",
        0.0,
    )
    node, embedding, hybrid, graph, reranker = build(
        [point()], [fact()], [4.0, 5.0]
    )
    result = node({"question": "who was behind grad cam", "document_ids": ["doc-1"]})
    assert result["retrieval_route"] == "fused"
    assert embedding.calls == hybrid.calls == graph.calls == reranker.calls == 1
    assert result["query_embedding_call_count"] == 1
    assert hybrid.document_ids == graph.document_ids == ["doc-1"]
    assert "Graph Evidence" in result["research_context"]
    assert result["evidence_items"][0] == {
        "label": "Evidence 1",
        "kind": "text",
        "text": "text evidence",
        "document_id": "doc-1",
        "filename": "sample.pdf",
        "chunk_id": "chunk-1",
        "chunk_index": 0,
        "page_number": 1,
        "retrieval_route": "hybrid",
        "relevance": 4.0,
    }
    graph_item = result["evidence_items"][1]
    assert graph_item["graph_fact"] == {
        "source": "Grad-CAM",
        "relationship": "DEVELOPED_BY",
        "target": "R. R. Selvaraju",
    }
    assert graph_item["text"] == "Grad-CAM was developed by Selvaraju et al."


def test_graph_only_and_hybrid_only_routes(monkeypatch):
    monkeypatch.setattr(
        "app.agents.adaptive_retrieval.settings.adaptive_evidence_relevance_threshold", 0.0
    )
    graph_node, *_ = build([point()], [fact()], [-5.0, 3.0])
    hybrid_node, *_ = build([point()], [fact()], [3.0, -5.0])
    assert graph_node({"question": "q"})["retrieval_route"] == "graph"
    assert hybrid_node({"question": "q"})["retrieval_route"] == "hybrid"


def test_no_usable_evidence_uses_abstention_context(monkeypatch):
    monkeypatch.setattr(
        "app.agents.adaptive_retrieval.settings.adaptive_evidence_relevance_threshold", 0.0
    )
    node, *_ = build([point()], [fact()], [-5.0, -4.0])
    result = node({"question": "missing answer"})
    assert result["retrieval_route"] == "fused"
    assert result["retrieved_chunk_ids"] == []
    assert result["research_context"].startswith("No document-scoped")


def test_one_channel_failure_degrades_and_both_fail_raise(monkeypatch):
    monkeypatch.setattr(
        "app.agents.adaptive_retrieval.settings.adaptive_evidence_relevance_threshold", 0.0
    )
    graph_failed, *_ = build([point()], [], [3.0], graph_error=RuntimeError("neo4j"))
    hybrid_failed, *_ = build([], [fact()], [3.0], hybrid_error=RuntimeError("qdrant"))
    both_failed, *_ = build([], [], [], RuntimeError("qdrant"), RuntimeError("neo4j"))
    first = graph_failed({"question": "q"})
    second = hybrid_failed({"question": "q"})
    assert first["retrieval_route"] == "hybrid" and first["degraded"]
    assert second["retrieval_route"] == "graph" and second["degraded"]
    with pytest.raises(RuntimeError, match="both evidence channels"):
        both_failed({"question": "q"})


def test_complex_question_uses_two_hops_and_fused(monkeypatch):
    monkeypatch.setattr(
        "app.agents.adaptive_retrieval.settings.adaptive_evidence_relevance_threshold", 0.0
    )
    node, _, _, graph, _ = build([point()], [fact()], [3.0, 4.0])
    result = node({"question": "Which method is discussed and who developed it?"})
    assert result["requires_decomposition"] is True
    assert result["retrieval_route"] == "fused"
    assert graph.max_path_depth == 2


def test_routing_metadata_is_api_compatible():
    payload = ChatResponse(
        answer="answer", route="graph", strategy="adaptive_evidence",
        initial_route="graph", final_route="graph", verified=True,
        retry_count=0, retrieved_chunk_ids=[], graph_fact_count=1,
        used_evidence_labels=[],
    ).model_dump()
    assert payload["route"] == "graph"
    assert payload["strategy"] == "adaptive_evidence"


def test_graph_neighborhood_query_is_bounded_and_scoped():
    class RecordingStore:
        def __init__(self):
            self.cypher = None
            self.parameters = None

        def query(self, cypher, parameters):
            self.cypher = cypher
            self.parameters = parameters
            return []

    store = RecordingStore()
    retriever = GraphQueryRetriever(store)
    retriever._retrieve_facts(
        entity_id="entity-1",
        limit=7,
        document_ids=["doc-1"],
        max_path_depth=1,
    )

    assert "[rels*1..1]" in store.cypher
    assert ".source_document_id" in store.cypher
    assert "IN $document_ids" in store.cypher
    assert store.parameters["document_ids"] == ["doc-1"]
    assert store.parameters["limit"] == 7


def test_chunk_seeded_graph_probe_is_bounded_and_scoped():
    class RecordingStore:
        def query(self, cypher, parameters):
            self.cypher = cypher
            self.parameters = parameters
            return []

    store = RecordingStore()
    result = GraphQueryRetriever(store).retrieve_by_chunk_ids(
        query="complex question",
        chunk_ids=["chunk-1", "chunk-1"],
        document_ids=["doc-1"],
        max_facts=6,
    )
    assert result.facts == []
    assert "source_chunk_id IN $chunk_ids" in store.cypher
    assert "source_document_id IN $document_ids" in store.cypher
    assert store.parameters == {
        "chunk_ids": ["chunk-1"],
        "document_ids": ["doc-1"],
        "limit": 6,
    }
