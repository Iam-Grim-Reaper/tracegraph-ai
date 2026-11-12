"""Deterministic retrieval/provenance evaluation of captured TraceGraph responses.

Accepts JSONL cases from real or synthetic, authorized, labeled evaluations.
No external API calls, credentials or LLM-based grading. Citation integrity
is *structural*, not a claim about factual faithfulness.

Usage:
  python tools/evaluate_offline.py --input evaluation/smoke.jsonl \
      --output evaluation-smoke-report.json --strict
"""

import argparse
import json
import math
import re
import statistics
from pathlib import Path

CITATION_RE = re.compile(r"\\[((?:Graph )?Evidence (?:[a-z]\\d+-)?\\d+)\\]", re.IGNORECASE)
ABSTENTION_STATUSES = {"grounded_abstention", "verified_abstention"}


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    samples = sorted(values)
    index = (len(samples) - 1) * pct / 100
    low = math.floor(index)
    high = math.ceil(index)
    return samples[low] + (samples[high] - samples[low]) * (index - low)


def evaluate_case(case: dict, *, k: int = 5) -> dict:
    if not case.get("id") or "result" not in case:
        raise ValueError("Each case needs an id and result.")
    result = case["result"]
    retrieved = [str(value) for value in result.get("retrieved_chunk_ids", [])][:k]
    relevant = {str(value) for value in case.get("relevant_chunk_ids", [])}
    retrieved_unique = list(dict.fromkeys(retrieved))
    hits = relevant.intersection(retrieved_unique)
    first_relevant = next((i for i, doc in enumerate(retrieved, 1) if doc in relevant), None)
    reciprocal_rank = (1.0 / first_relevant) if first_relevant else 0.0
    dcg = sum(1.0 / math.log2(i + 1) for i, doc in enumerate(retrieved, 1) if doc in relevant)
    ideal_count = min(k, len(relevant))
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_count + 1))

    evidence = result.get("evidence_items", [])
    labels = {str(e.get("label", "")).casefold() for e in evidence}
    cited_labels = {
        match.casefold() for match in CITATION_RE.findall(str(result.get("answer", "")))
    }
    unknown_citations = sorted(cited_labels - labels)

    scope = case.get("allowed_document_ids")
    scope_violation = []
    if scope is not None:
        allowed = {str(value) for value in scope}
        scope_violation = sorted({
            str(e.get("document_id"))
            for e in evidence
            if e.get("document_id") not in allowed
        })

    expected_abstention = case.get("expect_abstention")
    abstained = result.get("answer_status") in ABSTENTION_STATUSES
    abstention_match = (
        None if expected_abstention is None
        else abstained == bool(expected_abstention)
    )
    duration = result.get("latency_ms")
    if duration is not None and (not isinstance(duration, (int, float)) or duration < 0):
        raise ValueError(f"Invalid latency_ms for {case['id']}")

    return {
        "id": str(case["id"]),
        "has_relevance_labels": bool(relevant),
        "recall_at_k": len(hits) / len(relevant) if relevant else None,
        "precision_at_k": len(hits) / len(retrieved_unique) if relevant and retrieved_unique else (0.0 if relevant else None),
        "mrr_at_k": reciprocal_rank if relevant else None,
        "ndcg_at_k": dcg / ideal if ideal else None,
        "citations_used": len(cited_labels),
        "unknown_citations": unknown_citations,
        "scope_violations": scope_violation,
        "abstention_match": abstention_match,
        "degraded": bool(result.get("degraded") or result.get("decomposition_degraded")),
        "latency_ms": duration,
    }


def evaluate(cases: list[dict], *, k: int = 5) -> dict:
    if k < 1:
        raise ValueError("k must be positive.")
    if not cases:
        raise ValueError("No cases supplied.")
    rows = [evaluate_case(case, k=k) for case in cases]
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Case IDs must be unique.")

    def mean_of(key: str):
        values = [float(row[key]) for row in rows if row[key] is not None]
        return round(statistics.mean(values), 4) if values else None

    latency = [float(row["latency_ms"]) for row in rows if row["latency_ms"] is not None]
    relevant_count = sum(1 for row in rows if row["has_relevance_labels"])
    abstention_cases = [row for row in rows if row["abstention_match"] is not None]
    failures = [
        row["id"] for row in rows
        if row["unknown_citations"] or row["scope_violations"]
    ]
    return {
        "meta": {
            "cases": len(rows),
            "labeled_retrieval_cases": relevant_count,
            "k": k,
            "evaluation": "structural_offline",
            "warning": "Does not measure semantic faithfulness or live production latency.",
        },
        "summary": {
            "recall_at_k": mean_of("recall_at_k"),
            "precision_at_k": mean_of("precision_at_k"),
            "mrr_at_k": mean_of("mrr_at_k"),
            "ndcg_at_k": mean_of("ndcg_at_k"),
            "citation_validity_rate": round(
                sum(not row["unknown_citations"] for row in rows) / len(rows), 4
            ),
            "scope_integrity_rate": round(
                sum(not row["scope_violations"] for row in rows) / len(rows), 4
            ),
            "abstention_agreement": (
                round(sum(row["abstention_match"] for row in abstention_cases) / len(abstention_cases), 4)
                if abstention_cases else None
            ),
            "degraded_cases": sum(row["degraded"] for row in rows),
            "latency_p50_ms": round(statistics.median(latency), 2) if latency else None,
            "latency_p95_ms": round(percentile(latency, 95), 2) if latency else None,
            "integrity_failures": failures,
        },
        "cases": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--strict", action="store_true", help="Exit nonzero on citation or scope integrity violations.")
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    report = evaluate(cases, k=args.k)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    if args.strict and report["summary"]["integrity_failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
