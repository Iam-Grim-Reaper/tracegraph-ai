import json
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from evaluation.benchmark import load_benchmark
from evaluation.analyze import percentile
from evaluation.metrics import (
    calculate_metrics,
    ranked_chunk_metrics,
)
from evaluation.models import (
    BenchmarkCase,
    EvaluationResult,
    Evidence,
    RelationshipEvidence,
    RetrievalResult,
)
from evaluation.reporting import serialize_results
from evaluation.runner import EvaluationRunner, load_existing_results
from evaluation.variants import cosine_similarity
from evaluation import controlled
from app.core.config import settings
from app.retrieval.graph_hybrid_retriever import GraphHybridRetriever
from app.retrieval.hybrid_store import HybridStore


def make_case() -> BenchmarkCase:
    return BenchmarkCase(
        id="case-1",
        category="test",
        question="Who developed Grad-CAM?",
        document_ids=["doc-1"],
        expected_answer="R. R. Selvaraju",
        expected_entities=["Grad-CAM", "R. R. Selvaraju"],
        expected_relationships=[
            {
                "source": "Grad-CAM",
                "relationship": "DEVELOPED_BY",
                "target": "R. R. Selvaraju",
            }
        ],
        expected_chunk_ids=["chunk-2"],
        answer_must_contain=["R. R. Selvaraju"],
        requires_graph=True,
    )


def make_retrieval() -> RetrievalResult:
    return RetrievalResult(
        variant="graph",
        context=(
            "[Graph Evidence 1]\n"
            "Grad-CAM -[DEVELOPED_BY]-> R. R. Selvaraju"
        ),
        evidence=[
            Evidence(
                label="Graph Evidence 1",
                kind="graph",
                document_id="doc-1",
                chunk_id="chunk-2",
            )
        ],
        chunk_ids=["chunk-1", "chunk-2"],
        entities=["Grad-CAM", "R. R. Selvaraju"],
        relationships=[
            RelationshipEvidence(
                source="Grad-CAM",
                relationship="DEVELOPED_BY",
                target="R. R. Selvaraju",
                document_id="doc-1",
                chunk_id="chunk-2",
            )
        ],
        retrieval_latency_seconds=0.1,
        limits={"max_facts": 20},
    )


def test_load_benchmark(tmp_path):
    path = tmp_path / "benchmark.json"
    path.write_text(
        json.dumps([make_case().__dict__]),
        encoding="utf-8",
    )

    cases = load_benchmark(path)

    assert len(cases) == 1
    assert cases[0].id == "case-1"


def test_load_benchmark_rejects_duplicate_ids(tmp_path):
    item = make_case().__dict__
    path = tmp_path / "benchmark.json"
    path.write_text(
        json.dumps([item, item]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unique"):
        load_benchmark(path)


def test_ranked_chunk_metrics():
    metrics = ranked_chunk_metrics(
        ["wrong", "expected"],
        ["expected"],
    )

    assert metrics["recall_at_k"] == 1.0
    assert metrics["precision_at_k"] == 0.5
    assert metrics["hit_at_k"] is True
    assert metrics["mrr"] == 0.5


def test_cosine_similarity_for_dense_local_scope():
    assert cosine_similarity(
        [1.0, 0.0],
        [1.0, 0.0],
    ) == pytest.approx(1.0)
    assert cosine_similarity(
        [1.0, 0.0],
        [0.0, 1.0],
    ) == pytest.approx(0.0)


def test_percentile_uses_linear_interpolation():
    assert percentile(
        [1.0, 2.0, 3.0, 4.0],
        0.5,
    ) == pytest.approx(2.5)


def test_evaluation_collection_names_are_isolated():
    assert controlled.EVAL_DENSE_COLLECTION not in (
        controlled.production_collection_names()
    )
    assert controlled.EVAL_HYBRID_COLLECTION not in (
        controlled.production_collection_names()
    )
    with pytest.raises(ValueError, match="production"):
        controlled.assert_evaluation_collection(
            settings.qdrant_hybrid_collection
        )


def test_controlled_adapter_factories_use_eval_collections(
    monkeypatch,
):
    calls = {}

    class FakeDense:
        def __init__(self, collection_name):
            calls["dense"] = collection_name

    class FakeHybrid:
        def __init__(self, collection_name):
            calls["hybrid"] = collection_name

    class FakeFused:
        def __init__(self, hybrid_collection_name):
            calls["fused"] = hybrid_collection_name

    monkeypatch.setattr(controlled, "DenseAdapter", FakeDense)
    monkeypatch.setattr(controlled, "HybridAdapter", FakeHybrid)
    monkeypatch.setattr(controlled, "FusedAdapter", FakeFused)

    controlled.create_controlled_dense_adapter()
    controlled.create_controlled_hybrid_adapter()
    controlled.create_controlled_fused_adapter()

    assert calls == {
        "dense": controlled.EVAL_DENSE_COLLECTION,
        "hybrid": controlled.EVAL_HYBRID_COLLECTION,
        "fused": controlled.EVAL_HYBRID_COLLECTION,
    }


def test_controlled_runner_selects_controlled_factories(monkeypatch):
    calls = []

    class FakeAdapter:
        def close(self):
            return None

    def factory(name):
        calls.append(name)
        return FakeAdapter()

    runner = EvaluationRunner(
        retrieval_only=True,
        adapter_factory=factory,
    )
    for variant in ("dense", "hybrid", "graph", "fused"):
        assert runner._adapter(variant) is runner._adapter(variant)
    assert calls == ["dense", "hybrid", "graph", "fused"]


def test_controlled_factory_keeps_graph_neo4j_based(monkeypatch):
    marker = object()
    monkeypatch.setattr(controlled, "GraphAdapter", lambda: marker)
    assert controlled.create_controlled_adapter("graph") is marker


def test_normal_runner_uses_production_factory(monkeypatch):
    marker = object()
    monkeypatch.setattr(
        "evaluation.runner.create_adapter",
        lambda name: marker,
    )
    runner = EvaluationRunner(retrieval_only=True)
    assert runner._adapter("dense") is marker


def test_runner_preserves_document_ids():
    observed = []

    class FakeAdapter:
        def retrieve(self, question, document_ids):
            observed.extend(document_ids)
            return RetrievalResult(
                variant="dense",
                context="",
                evidence=[],
                chunk_ids=[],
                entities=[],
                relationships=[],
                retrieval_latency_seconds=0.0,
                limits={},
            )

        def close(self):
            return None

    case = make_case()
    runner = EvaluationRunner(
        retrieval_only=True,
        adapter_factory=lambda name: FakeAdapter(),
    )
    runner.run_case(case, "dense")
    assert observed == case.document_ids


def test_controlled_factory_cannot_accept_collection_override():
    signature = inspect.signature(
        controlled.create_controlled_adapter
    )
    assert list(signature.parameters) == ["name"]
    with pytest.raises(TypeError):
        controlled.create_controlled_adapter(
            "dense",
            collection_name=settings.qdrant_collection,
        )


def test_production_defaults_remain_optional():
    hybrid_default = inspect.signature(
        HybridStore.__init__
    ).parameters["collection_name"].default
    fused_default = inspect.signature(
        GraphHybridRetriever.__init__
    ).parameters["hybrid_store"].default

    assert hybrid_default is None
    assert fused_default is None


def test_controlled_corpus_preserves_stable_ids():
    corpus = controlled.load_controlled_corpus(
        paths=(
            Path("../data/career_fixture.txt"),
        )
    )

    assert str(corpus[0].document.id) == (
        "04685d93-3225-52a4-a22d-b9adfc05a058"
    )
    assert str(corpus[0].chunks[0].id) == (
        "d8b5ecda-f60d-5dad-b6d5-141253d48b61"
    )


def test_controlled_plan_preserves_all_chunks():
    corpus = controlled.load_controlled_corpus(
        paths=(
            Path("../data/career_fixture.txt"),
            Path("../data/policy_fixture.txt"),
        )
    )
    plan = controlled.build_controlled_index_plan(corpus)

    assert plan.document_count == 2
    assert plan.chunk_count == 2
    assert plan.dense_embeddings_required == 2
    assert plan.dense_qdrant_writes == 2
    assert plan.hybrid_qdrant_writes == 2
    assert plan.dense_embedding_api_calls == 2
    assert plan.hybrid_embedding_api_calls == 2
    assert plan.hybrid_contextualization_api_calls == 2


def test_dense_and_hybrid_representations_are_distinct():
    chunk = SimpleNamespace(
        text="Original chunk text",
        contextual_text=(
            "Document context\n\nOriginal chunk text"
        ),
    )

    assert controlled.dense_representation(chunk) == (
        "Original chunk text"
    )
    assert controlled.hybrid_representation(chunk).startswith(
        "Document context"
    )


def test_hybrid_representation_requires_context():
    chunk = SimpleNamespace(
        text="Original",
        contextual_text=None,
    )
    with pytest.raises(ValueError, match="contextualized"):
        controlled.hybrid_representation(chunk)


def test_controlled_plan_has_exact_provider_call_estimate():
    plan = controlled.build_controlled_index_plan(
        controlled.load_controlled_corpus()
    )

    assert plan.document_count == 5
    assert plan.chunk_count == 35
    assert plan.dense_embedding_api_calls == 6
    assert plan.hybrid_embedding_api_calls == 4
    assert plan.hybrid_contextualization_api_calls == 4
    assert plan.total_provider_calls == 14


def test_controlled_stable_point_ids_match_chunks():
    corpus = controlled.load_controlled_corpus(
        paths=(Path("../data/career_fixture.txt"),)
    )
    assert controlled.stable_point_ids(corpus) == tuple(
        str(chunk.id) for chunk in corpus[0].chunks
    )


def test_controlled_builder_refuses_recreation():
    with pytest.raises(ValueError, match="never"):
        controlled.assert_non_destructive(True)


def test_controlled_builder_dry_run_has_no_external_calls(
    monkeypatch,
    capsys,
):
    from evaluation import build_controlled

    def forbidden(*args, **kwargs):
        raise AssertionError("external build path was called")

    monkeypatch.setattr(
        build_controlled,
        "build_controlled_indexes",
        forbidden,
    )
    assert build_controlled.main(["--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "documents: 5" in output
    assert "chunks: 35" in output
    assert "estimated total provider calls: 14" in output
    assert "no collections created" in output


def test_stable_qdrant_ids_make_reruns_idempotent():
    corpus = controlled.load_controlled_corpus(
        paths=(Path("../data/policy_fixture.txt"),)
    )
    first = controlled.stable_point_ids(corpus)
    second = controlled.stable_point_ids(
        controlled.load_controlled_corpus(
            paths=(Path("../data/policy_fixture.txt"),)
        )
    )
    assert first == second


def test_controlled_variants_share_document_scope_values():
    document_ids = ["doc-a", "doc-b"]
    normalized = HybridStore._normalize_document_ids(
        document_ids
    )

    assert normalized == document_ids


def test_metrics_detect_facts_citations_and_scope():
    metrics = calculate_metrics(
        case=make_case(),
        retrieval=make_retrieval(),
        answer=(
            "R. R. Selvaraju developed Grad-CAM "
            "[Graph Evidence 1]."
        ),
        verified=True,
    )

    assert metrics["answer_correctness"] is True
    assert metrics["expected_entity_hit_rate"] == 1.0
    assert metrics["expected_relationship_retrieved"] is True
    assert metrics["citation_correctness"] == 1.0
    assert metrics["document_scope_leakage_count"] == 0


def test_positive_answer_with_expected_name_inside_abstention_is_incorrect():
    metrics = calculate_metrics(
        make_case(),
        make_retrieval(),
        answer=(
            "The provided evidence does not state who developed "
            "Grad-CAM, although R. R. Selvaraju appears in a reference."
        ),
        verified=True,
    )
    assert metrics["answer_correctness"] is False


def test_qualified_abstention_with_expected_name_is_incorrect():
    metrics = calculate_metrics(
        make_case(),
        make_retrieval(),
        answer=(
            "The evidence mentions R. R. Selvaraju, but does not "
            "explicitly state who developed Grad-CAM."
        ),
        verified=True,
    )
    assert metrics["answer_correctness"] is False


def test_positive_affirmative_answer_is_correct():
    metrics = calculate_metrics(
        make_case(),
        make_retrieval(),
        answer=(
            "R. R. Selvaraju developed Grad-CAM "
            "[Graph Evidence 1]."
        ),
        verified=True,
    )
    assert metrics["answer_correctness"] is True


def test_expected_scope_abstention_is_correct():
    case = make_case()
    case.negative = True
    metrics = calculate_metrics(
        case,
        make_retrieval(),
        answer="The available evidence is insufficient.",
        verified=True,
    )
    assert metrics["answer_correctness"] is True
    assert metrics["abstention_correctness"] is True


def test_wrong_affirmative_answer_is_incorrect():
    metrics = calculate_metrics(
        make_case(),
        make_retrieval(),
        answer="John Doe developed Grad-CAM [Graph Evidence 1].",
        verified=False,
        unsupported_claims=["John Doe developed Grad-CAM"],
    )
    assert metrics["answer_correctness"] is False


def test_supported_uncited_answer_is_faithful_but_not_cited():
    metrics = calculate_metrics(
        make_case(),
        make_retrieval(),
        answer="R. R. Selvaraju developed Grad-CAM.",
        verified=True,
    )
    assert metrics["faithfulness"] is True
    assert metrics["citation_correctness"] == 0.0
    assert metrics["citation_coverage"] == 0.0


def test_cited_unsupported_claim_is_not_faithful():
    metrics = calculate_metrics(
        make_case(),
        make_retrieval(),
        answer="John Doe developed Grad-CAM [Graph Evidence 1].",
        verified=False,
        unsupported_claims=["John Doe developed Grad-CAM"],
    )
    assert metrics["faithfulness"] is False


def test_supported_cited_claim_is_faithful_and_cited():
    metrics = calculate_metrics(
        make_case(),
        make_retrieval(),
        answer=(
            "R. R. Selvaraju developed Grad-CAM "
            "[Graph Evidence 1]."
        ),
        verified=True,
    )
    assert metrics["faithfulness"] is True
    assert metrics["citation_correctness"] == 1.0
    assert metrics["citation_coverage"] == 1.0


def test_verified_abstention_needs_no_fabricated_citation():
    case = make_case()
    case.negative = True
    metrics = calculate_metrics(
        case,
        make_retrieval(),
        answer="The evidence is insufficient.",
        verified=True,
    )
    assert metrics["faithfulness"] is True
    assert metrics["citation_correctness"] == 1.0
    assert metrics["citation_coverage"] == 1.0


def test_metrics_detect_scope_leakage():
    retrieval = make_retrieval()
    retrieval.evidence.append(
        Evidence(
            label="Evidence 2",
            kind="chunk",
            document_id="other-doc",
        )
    )

    metrics = calculate_metrics(
        make_case(),
        retrieval,
    )

    assert metrics["out_of_scope_evidence_count"] == 1
    assert metrics["document_scope_leakage_count"] == 1


def test_multi_hop_evidence_completeness():
    case = make_case()
    case.multi_hop = True

    metrics = calculate_metrics(
        case,
        make_retrieval(),
    )

    assert metrics["multi_hop_evidence_completeness"] == 1.0


def test_result_serialization(tmp_path):
    retrieval = make_retrieval()
    result = EvaluationResult(
        case_id="case-1",
        category="test",
        variant="graph",
        question="Question?",
        document_ids=["doc-1"],
        answer="Answer [Graph Evidence 1]",
        verified=True,
        verification_reason="Grounded",
        unsupported_claims=[],
        retry_count=0,
        used_evidence_labels=["Graph Evidence 1"],
        retrieval=retrieval,
        metrics={"answer_correctness": True},
        total_latency_seconds=0.2,
    )
    json_path = tmp_path / "result.json"
    csv_path = tmp_path / "result.csv"

    serialize_results(
        [result],
        json_path,
        csv_path,
        {"smoke": True},
    )

    payload = json.loads(
        json_path.read_text(encoding="utf-8")
    )
    assert payload["results"][0]["case_id"] == "case-1"
    assert "case-1" in csv_path.read_text(encoding="utf-8")

    restored = load_existing_results(
        json_path
    )
    assert restored[0].retrieval.evidence[0].document_id == "doc-1"
    assert restored[0].metrics["answer_correctness"] is True
