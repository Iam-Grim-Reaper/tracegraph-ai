import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from evaluation.models import EvaluationResult


def serialize_results(
    results: list[EvaluationResult],
    json_path: str | Path,
    csv_path: str | Path,
    metadata: dict[str, Any],
) -> None:
    json_output = Path(json_path)
    csv_output = Path(csv_path)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    csv_output.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "metadata": metadata,
        "results": [item.to_dict() for item in results],
    }
    json_output.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    rows = []
    for item in results:
        row = {
            "case_id": item.case_id,
            "category": item.category,
            "variant": item.variant,
            "question": item.question,
            "document_ids": "|".join(item.document_ids),
            "answer": item.answer or "",
            "verified": item.verified,
            "retry_count": item.retry_count,
            "retrieval_latency_seconds": (
                item.retrieval.retrieval_latency_seconds
            ),
            "total_latency_seconds": item.total_latency_seconds,
            "retrieved_chunk_count": len(item.retrieval.chunk_ids),
            "graph_fact_count": len(item.retrieval.relationships),
            "evidence_labels": "|".join(item.used_evidence_labels),
            "token_usage_available": item.token_usage_available,
            "error": item.error or "",
        }
        row.update(item.metrics)
        rows.append(row)

    fieldnames = sorted(
        {key for row in rows for key in row}
    ) if rows else ["case_id", "variant"]
    with csv_output.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def _average(
    results: list[EvaluationResult],
    metric: str,
) -> float | None:
    values = [
        item.metrics.get(metric)
        for item in results
        if isinstance(
            item.metrics.get(metric),
            (int, float, bool),
        )
    ]
    return mean(float(value) for value in values) if values else None


def _format(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.3f}"


def write_report(
    results: list[EvaluationResult],
    report_path: str | Path,
    metadata: dict[str, Any],
) -> None:
    grouped: dict[str, list[EvaluationResult]] = defaultdict(list)
    for result in results:
        grouped[result.variant].append(result)

    lines = [
        "# TraceGraph Evaluation Report",
        "",
        "> This report contains only actually executed runs. "
        "A smoke run is not a full benchmark.",
        "",
        f"- Executed cases: {len(results)}",
        f"- Retrieval-only: {metadata.get('retrieval_only', False)}",
        "- Token usage available: false",
        "- Cost: not computed; no verified pricing table is configured.",
        "",
        "## Variant Summary",
        "",
        "| Variant | Correctness | Faithfulness | Citation Accuracy | Multi-hop | Recall@K | Avg Retrieval Latency | Avg Total Latency |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant in sorted(grouped):
        items = grouped[variant]
        lines.append(
            "| " + " | ".join(
                [
                    variant,
                    _format(_average(items, "answer_correctness")),
                    _format(_average(items, "faithfulness")),
                    _format(_average(items, "citation_correctness")),
                    _format(_average(items, "multi_hop_answer_success")),
                    _format(_average(items, "recall_at_k")),
                    _format(mean(item.retrieval.retrieval_latency_seconds for item in items)),
                    _format(mean(item.total_latency_seconds for item in items)),
                ]
            ) + " |"
        )

    lines.extend(
        [
            "",
            "## Executed Cases",
            "",
            "| Case | Category | Variant | Correct | Verified | Recall@K | Scope Leaks | Latency |",
            "|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for item in results:
        lines.append(
            f"| {item.case_id} | {item.category} | {item.variant} | "
            f"{item.metrics.get('answer_correctness', 'N/A')} | "
            f"{item.verified if item.verified is not None else 'N/A'} | "
            f"{item.metrics.get('recall_at_k', 'N/A')} | "
            f"{item.metrics.get('document_scope_leakage_count', 0)} | "
            f"{item.total_latency_seconds:.3f}s |"
        )

    output = Path(report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
