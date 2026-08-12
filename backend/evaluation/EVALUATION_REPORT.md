# TraceGraph Evaluation Report

> This report contains only actually executed runs. A smoke run is not a full benchmark.

- Executed cases: 1
- Retrieval-only: False
- Token usage available: false
- Cost: not computed; no verified pricing table is configured.

## Variant Summary

| Variant | Correctness | Faithfulness | Citation Accuracy | Multi-hop | Recall@K | Avg Retrieval Latency | Avg Total Latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| graph | 1.000 | 1.000 | 1.000 | N/A | 1.000 | 0.330 | 3.605 |

## Executed Cases

| Case | Category | Variant | Correct | Verified | Recall@K | Scope Leaks | Latency |
|---|---|---|---:|---:|---:|---:|---:|
| research_gradcam_developer | research_graph | graph | True | True | 1.0 | 0 | 3.605s |
