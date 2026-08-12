import json

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
from evaluation.runner import load_existing_results
from evaluation.variants import cosine_similarity


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
