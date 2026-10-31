"""Small, dependency-free latency benchmark for TraceGraph's live endpoints.

Usage:
  python tools/benchmark_live.py --base https://tracegraph-ai-backend.vercel.app
  python tools/benchmark_live.py --base https://... --requests 10 \
    --chat-question "Whose resume is this?" --document-id YOUR_ID --chat-runs 2 \
    --output results/benchmark.json

Chat calls use AI provider quotas and are opt-in. Run against authorized services only.
Results are observational (not a load/stress test). The first request is
reported separately so cold-start behavior is not hidden in warm averages.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def percentile(sorted_samples: list[float], percentile_number: float) -> float | None:
    if not sorted_samples:
        return None
    position = (len(sorted_samples) - 1) * percentile_number / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    return sorted_samples[lower] + (sorted_samples[upper] - sorted_samples[lower]) * (position - lower)


def summary(samples: list[float]) -> dict:
    ordered = sorted(samples)
    if not ordered:
        return {"count": 0}
    return {
        "count": len(samples),
        "first_ms": round(samples[0], 2),
        "median_ms": round(statistics.median(samples), 2),
        "mean_ms": round(statistics.mean(samples), 2),
        "p95_ms": round(percentile(ordered, 95), 2),
        "min_ms": round(ordered[0], 2),
        "max_ms": round(ordered[-1], 2),
        "warm_median_ms": round(statistics.median(samples[1:]), 2) if len(samples) > 1 else None,
    }


def call(url: str, payload: dict | None = None, timeout: int = 120) -> tuple[float, int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST" if data is not None else "GET",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read()
    except urllib.error.HTTPError as error:
        status = error.code
        body = error.read()
    elapsed = (time.perf_counter() - started) * 1000
    try:
        decoded = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        decoded = {"raw": body[:150].decode("utf-8", errors="replace")}
    return elapsed, status, decoded


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="API origin, without a path")
    parser.add_argument("--requests", type=int, default=6, help="GET repeats per endpoint")
    parser.add_argument("--chat-question", help="Opt-in question for billed Gemini calls")
    parser.add_argument("--document-id", action="append", default=[], help="Optional selected document")
    parser.add_argument("--chat-runs", type=int, default=2, help="Limit repeated AI calls (max 3)")
    parser.add_argument("--output", default="benchmark-results.json")
    args = parser.parse_args()

    if not args.base.startswith("https://"):
        parser.error("Only HTTPS endpoints are supported")
    if not 1 <= args.requests <= 30 or not 0 <= args.chat_runs <= 3:
        parser.error("--requests must be 1..30 and --chat-runs 0..3")

    base = args.base.rstrip("/")
    results = {
        "base": base,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "note": "Sequential single-client samples; not a concurrency or cost-capacity test.",
        "endpoints": {},
    }

    for endpoint in ("/health", "/ready", "/api/documents"):
        durations = []
        codes = []
        for _ in range(args.requests):
            ms, status, _ = call(base + endpoint)
            codes.append(status)
            durations.append(ms)
        results["endpoints"][endpoint] = {"latency": summary(durations), "statuses": codes}

    if args.chat_question and args.chat_runs:
        durations = []
        codes = []
        answer_statuses = []
        verification = []
        payload = {"question": args.chat_question}
        if args.document_id:
            payload["document_ids"] = args.document_id
        for _ in range(args.chat_runs):
            ms, code, response = call(base + "/api/chat", payload)
            durations.append(ms)
            codes.append(code)
            answer_statuses.append(response.get("answer_status"))
            verification.append(response.get("verified"))
        results["endpoints"]["/api/chat"] = {
            "latency": summary(durations),
            "statuses": codes,
            "answer_statuses": answer_statuses,
            "verified": verification,
        }

    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
