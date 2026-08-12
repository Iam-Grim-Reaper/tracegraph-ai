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

This is the fair architecture comparison: Dense and Hybrid both contain all 35 stable chunks from the same five-document corpus; all variants receive identical document scope; Graph uses the same document-provenance scope; and Fused combines the controlled Hybrid index with that graph. This is a 15-case, four-variant retrieval-only run (60 runs).

### Overall comparison

| Variant | Recall@K | Precision@K | Hit@K | MRR | Entity Hit | Relationship Hit | Multi-hop Completeness | Forbidden | Scope Leaks | Out-of-scope | Empty | Avg Latency | Median | P95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dense | 0.962 | 0.654 | 1.000 | 0.808 | 0.000 | 0.000 | 0.250 | 0 | 0 | 0 | 0 | 1.563s | 1.253s | 2.507s |
| hybrid | 0.846 | 0.623 | 0.923 | 0.872 | 0.000 | 0.000 | 0.250 | 0 | 0 | 0 | 0 | 0.854s | 0.676s | 1.373s |
| graph | 1.000 | 0.758 | 1.000 | 0.819 | 1.000 | 1.000 | 1.000 | 1 | 0 | 0 | 2 | 0.310s | 0.271s | 0.592s |
| fused | 1.000 | 0.631 | 1.000 | 0.879 | 1.000 | 1.000 | 1.000 | 1 | 0 | 0 | 0 | 1.352s | 1.000s | 2.879s |

### Results by category

| Category | Variant | Recall@K | Precision@K | Hit@K | MRR | Entity Hit | Relationship Hit | Multi-hop Completeness | Forbidden | Scope Leaks | Out-of-scope | Empty | Avg Latency | Median | P95 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| career | dense | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | N/A | 0 | 0 | 0 | 0 | 1.228s | 1.228s | 1.236s |
| career | fused | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0 | 0.985s | 0.985s | 1.043s |
| career | graph | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0 | 0.234s | 0.234s | 0.248s |
| career | hybrid | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | N/A | 0 | 0 | 0 | 0 | 0.637s | 0.637s | 0.640s |
| composed | dense | 1.000 | 0.667 | 1.000 | 1.000 | 0.000 | 0.000 | 0.333 | 0 | 0 | 0 | 0 | 1.222s | 1.230s | 1.234s |
| composed | fused | 1.000 | 0.667 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 0 | 0.928s | 1.000s | 1.002s |
| composed | graph | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 0 | 0.293s | 0.271s | 0.373s |
| composed | hybrid | 1.000 | 0.667 | 1.000 | 1.000 | 0.000 | 0.000 | 0.333 | 0 | 0 | 0 | 0 | 0.675s | 0.676s | 0.680s |
| contract | dense | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | N/A | 0 | 0 | 0 | 0 | 1.226s | 1.226s | 1.251s |
| contract | fused | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0 | 0.826s | 0.826s | 0.848s |
| contract | graph | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0 | 0.218s | 0.218s | 0.221s |
| contract | hybrid | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | N/A | 0 | 0 | 0 | 0 | 0.660s | 0.660s | 0.698s |
| negative | dense | 1.000 | 0.500 | 1.000 | 1.000 | 0.000 | N/A | N/A | 0 | 0 | 0 | 0 | 1.199s | 1.199s | 1.199s |
| negative | fused | 1.000 | 0.500 | 1.000 | 1.000 | 1.000 | N/A | N/A | 1 | 0 | 0 | 0 | 0.981s | 0.981s | 0.981s |
| negative | graph | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | N/A | 1 | 0 | 0 | 0 | 0.335s | 0.335s | 0.335s |
| negative | hybrid | 1.000 | 0.500 | 1.000 | 1.000 | 0.000 | N/A | N/A | 0 | 0 | 0 | 0 | 0.675s | 0.675s | 0.675s |
| policy | dense | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | N/A | 0 | 0 | 0 | 0 | 1.283s | 1.283s | 1.283s |
| policy | fused | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0 | 0.855s | 0.855s | 0.855s |
| policy | graph | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0 | 0.271s | 0.271s | 0.271s |
| policy | hybrid | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | N/A | 0 | 0 | 0 | 0 | 0.647s | 0.647s | 0.647s |
| research_factual | dense | 1.000 | 0.300 | 1.000 | 0.250 | 0.000 | 0.000 | N/A | 0 | 0 | 0 | 0 | 2.667s | 2.667s | 3.508s |
| research_factual | fused | 1.000 | 0.174 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0 | 3.142s | 3.142s | 4.087s |
| research_factual | graph | 1.000 | 0.214 | 1.000 | 0.250 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0 | 0.484s | 0.484s | 0.567s |
| research_factual | hybrid | 0.750 | 0.200 | 1.000 | 1.000 | 0.000 | 0.000 | N/A | 0 | 0 | 0 | 0 | 1.275s | 1.275s | 1.292s |
| research_graph | dense | 1.000 | 0.200 | 1.000 | 0.500 | 0.000 | 0.000 | N/A | 0 | 0 | 0 | 0 | 1.934s | 1.934s | 1.934s |
| research_graph | fused | 1.000 | 0.100 | 1.000 | 0.100 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0 | 2.317s | 2.317s | 2.317s |
| research_graph | graph | 1.000 | 0.143 | 1.000 | 0.143 | 1.000 | 1.000 | N/A | 0 | 0 | 0 | 0 | 0.383s | 0.383s | 0.383s |
| research_graph | hybrid | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | N/A | 0 | 0 | 0 | 0 | 1.509s | 1.509s | 1.509s |
| research_multihop | dense | 0.500 | 0.200 | 1.000 | 0.500 | 0.000 | 0.000 | 0.167 | 0 | 0 | 0 | 0 | 1.687s | 1.687s | 1.687s |
| research_multihop | fused | 1.000 | 0.250 | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 0 | 1.601s | 1.601s | 1.601s |
| research_multihop | graph | 1.000 | 0.286 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 0 | 0.629s | 0.629s | 0.629s |
| research_multihop | hybrid | 0.500 | 0.200 | 1.000 | 0.333 | 0.000 | 0.000 | 0.167 | 0 | 0 | 0 | 0 | 1.315s | 1.315s | 1.315s |
| scope_isolation | dense | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 | 1.718s | 1.718s | 2.006s |
| scope_isolation | fused | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 | 0.919s | 0.919s | 1.062s |
| scope_isolation | graph | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 2 | 0.137s | 0.137s | 0.161s |
| scope_isolation | hybrid | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 | 0.750s | 0.750s | 0.865s |

### Measured architecture behavior

- Dense retrieved every applicable expected chunk except half of the research multi-hop evidence. It achieved perfect recall on career, policy, contract, composed, and negative cases.
- Hybrid did not improve aggregate recall over Dense (0.846 versus 0.962), but improved aggregate MRR (0.872 versus 0.808), ranked the validation-accuracy and evaluation-dataset evidence first, and was faster on average (0.854s versus 1.563s).
- Graph reached 1.000 applicable recall, entity hit, relationship hit, and multi-hop completeness. Its structured facts supplied relationships unavailable to Dense and Hybrid, especially Grad-CAM development, career, policy, contract, and composed-ontology cases.
- Fused matched Graph's 1.000 recall/entity/relationship/multi-hop scores and added chunk evidence to the two scope-isolation cases where Graph correctly returned no evidence. It did not improve Graph's aggregate retrieval-quality scores and increased average latency from 0.310s to 1.352s.
- Contextual/lexical evidence remains useful as supporting source text even where Graph succeeds, but this retrieval-only benchmark does not measure whether the extra context improves generated answers.
- No variant returned out-of-scope evidence: scope leakage and out-of-scope counts were zero across all 60 runs.
- Graph and Fused each retrieved the forbidden `Data Protection Policy -[PROHIBITS]-> Encryption Control` relationship once. This is a graph semantic-quality limitation; the source graph was intentionally left unchanged.
- Graph's only empty retrievals were the two deliberately unsupported scope-isolation cases. Dense, Hybrid, and Fused always returned in-scope chunks, including for unsupported questions; answer-level abstention remains to be evaluated.
