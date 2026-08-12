import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from evaluation.benchmark import (
    DEFAULT_BENCHMARK_PATH,
    load_benchmark,
)
from evaluation.reporting import (
    serialize_results,
    write_report,
)
from evaluation.runner import (
    EvaluationRunner,
    load_existing_results,
)
from evaluation.controlled import (
    EVAL_DENSE_COLLECTION,
    EVAL_HYBRID_COLLECTION,
    create_controlled_adapter,
)
from evaluation.variants import VARIANT_NAMES, create_adapter


EVALUATION_DIR = Path(__file__).parent
DEFAULT_RESULTS_DIR = EVALUATION_DIR / "results"
DEFAULT_REPORT = EVALUATION_DIR / "EVALUATION_REPORT.md"


def parse_variants(value: str) -> list[str]:
    variants = list(
        dict.fromkeys(
            item.strip().casefold()
            for item in value.split(",")
            if item.strip()
        )
    )
    invalid = set(variants) - set(VARIANT_NAMES)
    if invalid:
        raise argparse.ArgumentTypeError(
            "Unknown variants: " + ", ".join(sorted(invalid))
        )
    return variants


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate existing TraceGraph retrieval variants."
    )
    parser.add_argument(
        "--benchmark",
        default=str(DEFAULT_BENCHMARK_PATH),
    )
    parser.add_argument(
        "--variants",
        type=parse_variants,
        default=list(VARIANT_NAMES),
        help="Comma-separated: dense,hybrid,graph,fused",
    )
    parser.add_argument(
        "--variant",
        choices=VARIANT_NAMES,
        help="Evaluate one variant; overrides --variants.",
    )
    parser.add_argument("--category")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--retrieval-only", action="store_true")
    parser.add_argument(
        "--controlled",
        action="store_true",
        help="Use isolated matched-corpus evaluation collections.",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_RESULTS_DIR / "latest.json"),
    )
    parser.add_argument(
        "--csv-output",
        default=str(DEFAULT_RESULTS_DIR / "latest.csv"),
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    cases = load_benchmark(args.benchmark)
    if args.category:
        cases = [
            case for case in cases
            if case.category == args.category
        ]
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be at least 1")
        cases = cases[:args.limit]
    variants = [args.variant] if args.variant else args.variants
    run_count = len(cases) * len(variants)
    embedding_calls = len(cases) * sum(
        variant in {"dense", "hybrid", "fused"}
        for variant in variants
    )
    generation_calls = 0 if args.retrieval_only else run_count * 2
    print("Cases:", len(cases))
    print("Categories:", dict(Counter(case.category for case in cases)))
    print("Variants:", ", ".join(variants))
    print("Planned variant runs:", run_count)
    print("Estimated embedding calls:", embedding_calls)
    print("Estimated generation/verification calls:", generation_calls)
    print("Token usage available: false")
    if args.controlled:
        print("Retrieval mode: controlled matched corpus")
        print("Dense collection:", EVAL_DENSE_COLLECTION)
        print("Hybrid collection:", EVAL_HYBRID_COLLECTION)
        print("Graph: existing Neo4j (read-only retrieval)")
    else:
        print("Retrieval mode: production defaults")
    if args.dry_run:
        for case in cases:
            print(f"- {case.id}: {case.question}")
        return

    existing_results = (
        load_existing_results(args.output)
        if args.resume
        else []
    )
    completed = {
        (item.case_id, item.variant)
        for item in existing_results
        if not item.error
    }
    results = list(existing_results)
    runner = EvaluationRunner(
        retrieval_only=args.retrieval_only,
        adapter_factory=(
            create_controlled_adapter
            if args.controlled
            else create_adapter
        ),
    )
    try:
        for case in cases:
            for variant in variants:
                if (case.id, variant) in completed:
                    print("Skipping completed:", case.id, variant)
                    continue
                print("Running:", case.id, variant)
                results.append(
                    runner.run_case(case, variant)
                )
    finally:
        runner.close()

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "benchmark": str(args.benchmark),
        "variants": variants,
        "retrieval_only": args.retrieval_only,
        "controlled": args.controlled,
        "token_usage_available": False,
        "cost_computed": False,
        "retrieval_limits": {
            item.variant: item.retrieval.limits
            for item in results
        },
    }
    serialize_results(
        results,
        args.output,
        args.csv_output,
        metadata,
    )
    write_report(results, args.report, metadata)
    print("Wrote:", args.output)
    print("Wrote:", args.csv_output)
    print("Wrote:", args.report)


if __name__ == "__main__":
    main()
