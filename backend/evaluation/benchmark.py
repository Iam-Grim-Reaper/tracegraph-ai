import json
from pathlib import Path

from evaluation.models import BenchmarkCase


DEFAULT_BENCHMARK_PATH = (
    Path(__file__).with_name("benchmark.json")
)


def load_benchmark(
    path: str | Path = DEFAULT_BENCHMARK_PATH,
) -> list[BenchmarkCase]:
    benchmark_path = Path(path)
    payload = json.loads(
        benchmark_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(payload, list):
        raise ValueError(
            "Benchmark root must be a list."
        )

    cases = [
        BenchmarkCase(**item)
        for item in payload
    ]

    identifiers = [case.id for case in cases]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(
            "Benchmark IDs must be unique."
        )

    for case in cases:
        if not case.question.strip():
            raise ValueError(
                f"Benchmark {case.id} has no question."
            )
        if not case.document_ids:
            raise ValueError(
                f"Benchmark {case.id} has no document scope."
            )

    return cases
