# TraceGraph Retrieval Evaluation

TraceGraph was evaluated with a controlled matched-corpus benchmark designed to compare retrieval architectures fairly. Dense and Hybrid used the same five documents and all 35 stable chunks, every variant received identical document scopes and questions, GraphRAG applied the same document-provenance boundary, and Fused combined the controlled Hybrid index with that graph. The benchmark executed 15 cases across four variants for 60 retrieval-only runs.

## Results at a Glance

| Variant | Recall@K | Precision@K | MRR | Entity Hit | Relationship Hit | Multi-hop | Avg. Latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Dense | 0.962 | 0.654 | 0.808 | 0.000 | 0.000 | 0.250 | 1.563s |
| Hybrid | 0.846 | 0.623 | 0.872 | 0.000 | 0.000 | 0.250 | 0.854s |
| GraphRAG | 1.000 | 0.758 | 0.819 | 1.000 | 1.000 | 1.000 | 0.310s |
| Fused | 1.000 | 0.631 | 0.879 | 1.000 | 1.000 | 1.000 | 1.352s |

Dense retrieval provided strong direct-text coverage. It found every applicable expected chunk except half of the research multi-hop evidence and achieved perfect recall on the career, policy, contract, composed-ontology, and negative cases.

Hybrid retrieval combined contextualized embeddings, BM25, reciprocal-rank fusion, and cross-encoder reranking. It did not improve aggregate recall over Dense in this small corpus, but improved MRR from 0.808 to 0.872 and reduced average latency from 1.563s to 0.854s. It ranked specific research facts first even where aggregate recall was lower.

GraphRAG supplied the clearest relational advantage. It achieved complete applicable entity, relationship, and multi-hop coverage, retrieving structured facts unavailable to chunk-only methods—for example Grad-CAM authorship and career, policy, contract, and composed-ontology relationships. Its 0.310s average retrieval latency was also the lowest measured latency in this environment.

Fused retrieval preserved GraphRAG's complete recall and relational coverage while adding source chunks from the controlled Hybrid index. This is useful when an answer needs both an explicit relationship and supporting document text. The tradeoff was latency: Fused averaged 1.352s versus GraphRAG's 0.310s, without improving aggregate retrieval-quality scores in this benchmark.

## Engineering Findings

The strongest measured distinction was relational and multi-hop retrieval. Dense and Hybrid reached only 0.250 multi-hop completeness, while GraphRAG and Fused reached 1.000. This supports using graph evidence when questions depend on explicit entity relationships or connected facts, while chunk retrieval remains effective for direct textual questions.

Document provenance held across the entire benchmark. All four variants recorded zero scope leakage and zero out-of-scope evidence across all 60 runs. This validates stable document IDs and provenance filtering as meaningful product safeguards rather than UI-only filtering.

The evaluation also exposed a semantic-quality limitation. GraphRAG and Fused each retrieved the known questionable relationship `Data Protection Policy -[PROHIBITS]-> Encryption Control` once. The source text may not support that edge. TraceGraph therefore treats graph extraction and validation quality as an explicit limitation: graph structure improves relational retrieval, but extracted relationships must still be verified against source evidence.

These figures describe retrieval behavior on the controlled corpus. They do not by themselves establish end-user answer quality or claim that one architecture is universally superior. The complete benchmark implementation and historical report remain preserved in the `tracegraph-benchmark-complete` Git tag.
