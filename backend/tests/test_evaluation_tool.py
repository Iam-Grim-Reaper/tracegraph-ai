"""Reproducible retrieval metrics are deterministic and honest about coverage."""

import pytest

from tools.evaluate_offline import evaluate, evaluate_case, percentile


def make_case(case_id="a", *, ids=None, relevant=None, answer="Claim [Evidence 1]", evidence=None, latency=20):
    return {
        "id": case_id,
        "relevant_chunk_ids": relevant if relevant is not None else ["chunk-a", "chunk-b"],
        "allowed_document_ids": ["doc-a"],
        "expect_abstention": False,
        "result": {
            "retrieved_chunk_ids": ids if ids is not None else ["chunk-a", "other"],
            "evidence_items": evidence if evidence is not None else [
                {"label": "Evidence 1", "document_id": "doc-a", "chunk_id": "chunk-a"}
            ],
            "answer": answer,
            "answer_status": "verified_answer",
            "latency_ms": latency,
        },
    }


def test_retrieval_metrics_and_latency():
    result = evaluate([make_case(), make_case("b", ids=["chunk-b", "chunk-a"], latency=60)])
    summary = result["summary"]
    assert summary["recall_at_k"] == 0.75
    assert summary["precision_at_k"] == 0.75
    assert summary["mrr_at_k"] == 1.0
    assert summary["latency_p50_ms"] == 40.0
    assert summary["latency_p95_ms"] == 58.0
    assert summary["scope_integrity_rate"] == 1.0
    assert summary["citation_validity_rate"] == 1.0


def test_unknown_citation_and_cross_document_leak_fail_integrity():
    case = make_case(
        answer="False [Graph Evidence 55]",
        evidence=[{"label": "Evidence 1", "document_id": "doc-other"}],
    )
    row = evaluate_case(case)
    assert row["unknown_citations"] == ["graph evidence 55"]
    assert row["scope_violations"] == ["doc-other"]
    assert evaluate([case])["summary"]["integrity_failures"] == ["a"]


def test_negative_cases_excluded_from_relevance_average_and_can_score_abstention():
    case = make_case(
        ids=[], relevant=[], answer="Insufficient evidence", evidence=[], latency=2,
    )
    case["expect_abstention"] = True
    case["result"]["answer_status"] = "grounded_abstention"
    report = evaluate([case])
    assert report["summary"]["recall_at_k"] is None
    assert report["summary"]["abstention_agreement"] == 1.0


def test_requires_unique_case_ids_and_valid_inputs():
    with pytest.raises(ValueError, match="unique"):
        evaluate([make_case(), make_case()])
    with pytest.raises(ValueError, match="No cases"):
        evaluate([])
    with pytest.raises(ValueError, match="k must be positive"):
        evaluate([make_case()], k=0)
    with pytest.raises(ValueError, match="latency"):
        evaluate([make_case(latency=-1)])


def test_percentile_monotonic():
    assert percentile([100, 200, 300, 400], 0) == 100
    assert percentile([100, 200, 300, 400], 95) == pytest.approx(385)
