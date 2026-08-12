import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from evaluation.benchmark import (
    DEFAULT_BENCHMARK_PATH,
    load_benchmark,
)
from evaluation.metrics import calculate_metrics
from evaluation.reporting import serialize_results
from evaluation.runner import load_existing_results


SECTION_MARKER = "## FULL RETRIEVAL BENCHMARK"


def percentile(
    values: list[float],
    fraction: float,
) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return (
        ordered[lower] * (1.0 - weight)
        + ordered[upper] * weight
    )


def metric_mean(results, metric):
    values = [
        item.metrics.get(metric)
        for item in results
        if isinstance(item.metrics.get(metric), (int, float, bool))
    ]
    return mean(float(value) for value in values) if values else None


def format_metric(value):
    return "N/A" if value is None else f"{value:.3f}"


def summary_row(name, results):
    latencies = [
        item.retrieval.retrieval_latency_seconds
        for item in results
    ]
    return {
        "name": name,
        "recall": metric_mean(results, "recall_at_k"),
        "precision": metric_mean(results, "precision_at_k"),
        "hit": metric_mean(results, "hit_at_k"),
        "mrr": metric_mean(results, "mrr"),
        "entity": metric_mean(results, "expected_entity_hit_rate"),
        "relationship": metric_mean(results, "expected_relationship_hit_rate"),
        "multi_hop": metric_mean(results, "multi_hop_evidence_completeness"),
        "scope_leaks": sum(
            int(item.metrics["document_scope_leakage_count"])
            for item in results
        ),
        "out_of_scope": sum(
            int(item.metrics["out_of_scope_evidence_count"])
            for item in results
        ),
        "average_latency": mean(latencies),
        "median_latency": median(latencies),
        "p95_latency": percentile(latencies, 0.95),
        "empty_results": sum(
            not item.retrieval.evidence
            for item in results
        ),
    }


def build_full_retrieval_section(results) -> str:
    by_variant = defaultdict(list)
    by_category_variant = defaultdict(list)
    for item in results:
        by_variant[item.variant].append(item)
        by_category_variant[(item.category, item.variant)].append(item)

    lines = [
        SECTION_MARKER,
        "",
        "This section summarizes the complete 15-case, four-variant retrieval-only run (60 runs). Answer-generation metrics are intentionally not included.",
        "",
        "### Overall comparison",
        "",
        "| Variant | Recall@K | Precision@K | Hit@K | MRR | Entity Hit | Relationship Hit | Multi-hop Completeness | Scope Leaks | Out-of-scope | Empty | Avg Latency | Median | P95 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant in ("dense", "hybrid", "graph", "fused"):
        row = summary_row(variant, by_variant[variant])
        lines.append(
            f"| {variant} | {format_metric(row['recall'])} | {format_metric(row['precision'])} | {format_metric(row['hit'])} | {format_metric(row['mrr'])} | {format_metric(row['entity'])} | {format_metric(row['relationship'])} | {format_metric(row['multi_hop'])} | {row['scope_leaks']} | {row['out_of_scope']} | {row['empty_results']} | {row['average_latency']:.3f}s | {row['median_latency']:.3f}s | {row['p95_latency']:.3f}s |"
        )

    lines.extend([
        "",
        "### Results by category",
        "",
        "| Category | Variant | Recall@K | Precision@K | Hit@K | MRR | Entity Hit | Relationship Hit | Multi-hop Completeness | Scope Leaks | Out-of-scope | Empty | Avg Latency | Median | P95 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for category, variant in sorted(by_category_variant):
        row = summary_row(
            f"{category}/{variant}",
            by_category_variant[(category, variant)],
        )
        lines.append(
            f"| {category} | {variant} | {format_metric(row['recall'])} | {format_metric(row['precision'])} | {format_metric(row['hit'])} | {format_metric(row['mrr'])} | {format_metric(row['entity'])} | {format_metric(row['relationship'])} | {format_metric(row['multi_hop'])} | {row['scope_leaks']} | {row['out_of_scope']} | {row['empty_results']} | {row['average_latency']:.3f}s | {row['median_latency']:.3f}s | {row['p95_latency']:.3f}s |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--csv-output", required=True)
    parser.add_argument("--benchmark", default=str(DEFAULT_BENCHMARK_PATH))
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    payload = json.loads(
        Path(args.results).read_text(encoding="utf-8")
    )
    results = load_existing_results(args.results)
    cases = {case.id: case for case in load_benchmark(args.benchmark)}
    for result in results:
        result.metrics = calculate_metrics(
            cases[result.case_id],
            result.retrieval,
            answer=result.answer,
            verified=result.verified,
            unsupported_claims=result.unsupported_claims,
        )

    serialize_results(
        results,
        args.results,
        args.csv_output,
        payload.get("metadata", {}),
    )
    report_path = Path(args.report)
    existing = (
        report_path.read_text(encoding="utf-8")
        if report_path.exists()
        else "# TraceGraph Evaluation Report\n"
    )
    prefix = existing.split(SECTION_MARKER, 1)[0].rstrip()
    report_path.write_text(
        prefix + "\n\n" + build_full_retrieval_section(results),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
