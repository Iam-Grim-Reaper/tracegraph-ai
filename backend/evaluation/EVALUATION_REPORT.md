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

## Historical Coverage Benchmark

This benchmark reflects the indexes as they existed during development and therefore includes index-coverage differences between retrieval variants. It must not be interpreted as a controlled comparison of retrieval architectures. The section summarizes the complete 15-case, four-variant retrieval-only run (60 runs); answer-generation metrics are intentionally not included.

### Overall comparison

| Variant | Recall@K | Precision@K | Hit@K | MRR | Entity Hit | Relationship Hit | Multi-hop Completeness | Scope Leaks | Out-of-scope | Empty | Avg Latency | Median | P95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dense | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0 | 15 | 1.294s | 1.111s | 2.021s |
| hybrid | 0.154 | 0.046 | 0.231 | 0.179 | 0.000 | 0.000 | 0.083 | 0 | 0 | 10 | 0.744s | 0.676s | 1.235s |
| graph | 1.000 | 0.758 | 1.000 | 0.819 | 1.000 | 1.000 | 1.000 | 0 | 0 | 2 | 0.367s | 0.343s | 0.605s |
| fused | 1.000 | 0.746 | 1.000 | 0.879 | 1.000 | 1.000 | 1.000 | 0 | 0 | 1 | 1.162s | 1.026s | 1.621s |

### Results by category

| Category | Variant | Recall@K | Precision@K | Hit@K | MRR | Entity Hit | Relationship Hit | Multi-hop Completeness | Scope Leaks | Out-of-scope | Empty | Avg Latency | Median | P95 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| career | dense | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | N/A | 0 | 0 | 2 | 1.164s | 1.164s | 1.254s |
| career | fused | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 1.148s | 1.148s | 1.257s |
| career | graph | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0.417s | 0.417s | 0.550s |
| career | hybrid | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | N/A | 0 | 0 | 2 | 0.633s | 0.633s | 0.672s |
| composed | dense | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0 | 3 | 1.077s | 1.073s | 1.110s |
| composed | fused | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 0.977s | 0.959s | 1.017s |
| composed | graph | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 0.336s | 0.274s | 0.446s |
| composed | hybrid | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0 | 3 | 0.604s | 0.604s | 0.657s |
| contract | dense | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | N/A | 0 | 0 | 2 | 1.085s | 1.085s | 1.099s |
| contract | fused | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 1.123s | 1.123s | 1.215s |
| contract | graph | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0.319s | 0.319s | 0.359s |
| contract | hybrid | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | N/A | 0 | 0 | 2 | 0.617s | 0.617s | 0.636s |
| negative | dense | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | N/A | N/A | 0 | 0 | 1 | 1.011s | 1.011s | 1.011s |
| negative | fused | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | N/A | 0 | 0 | 0 | 1.089s | 1.089s | 1.089s |
| negative | graph | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | N/A | 0 | 0 | 0 | 0.408s | 0.408s | 0.408s |
| negative | hybrid | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | N/A | N/A | 0 | 0 | 1 | 0.683s | 0.683s | 0.683s |
| policy | dense | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | N/A | 0 | 0 | 1 | 1.161s | 1.161s | 1.161s |
| policy | fused | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0.965s | 0.965s | 0.965s |
| policy | graph | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0.271s | 0.271s | 0.271s |
| policy | hybrid | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | N/A | 0 | 0 | 1 | 0.710s | 0.710s | 0.710s |
| research_factual | dense | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | N/A | 0 | 0 | 2 | 1.356s | 1.356s | 1.479s |
| research_factual | fused | 1.000 | 0.174 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 1.440s | 1.440s | 1.487s |
| research_factual | graph | 1.000 | 0.214 | 1.000 | 0.250 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0.590s | 0.590s | 0.688s |
| research_factual | hybrid | 0.750 | 0.200 | 1.000 | 1.000 | 0.000 | 0.000 | N/A | 0 | 0 | 0 | 0.982s | 0.982s | 1.163s |
| research_graph | dense | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | N/A | 0 | 0 | 1 | 1.603s | 1.603s | 1.603s |
| research_graph | fused | 1.000 | 0.100 | 1.000 | 0.100 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 1.920s | 1.920s | 1.920s |
| research_graph | graph | 1.000 | 0.143 | 1.000 | 0.143 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0.343s | 0.343s | 0.343s |
| research_graph | hybrid | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | N/A | 0 | 0 | 0 | 1.358s | 1.358s | 1.358s |
| research_multihop | dense | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0 | 1 | 1.111s | 1.111s | 1.111s |
| research_multihop | fused | 1.000 | 0.250 | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 1.419s | 1.419s | 1.419s |
| research_multihop | graph | 1.000 | 0.286 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 0.470s | 0.470s | 0.470s |
| research_multihop | hybrid | 0.500 | 0.200 | 1.000 | 0.333 | 0.000 | 0.000 | 0.167 | 0 | 0 | 0 | 0.740s | 0.740s | 0.740s |
| scope_isolation | dense | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0 | 0 | 2 | 2.045s | 2.045s | 2.900s |
| scope_isolation | fused | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0 | 0 | 1 | 0.844s | 0.844s | 0.941s |
| scope_isolation | graph | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0 | 0 | 2 | 0.174s | 0.174s | 0.207s |
| scope_isolation | hybrid | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0 | 0 | 1 | 0.699s | 0.699s | 0.741s |

## Controlled Matched-Corpus Benchmark

Not yet executed. This future benchmark will compare dense, hybrid, graph, and fused retrieval over the same five-document, 35-chunk corpus using isolated evaluation-only Qdrant collections. No controlled metrics are reported until the evaluation indexes are approved, built, and measured.
