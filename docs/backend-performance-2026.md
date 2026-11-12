# Backend performance and resilience (November 2026)

## Why this change

TraceGraph's production audit found a 56.6-second `GET /api/documents` failure during a Neo4j Aura DNS outage. The adaptive workflow also constructed unused legacy retrieval clients, including redundant graph connectivity probes. This changes startup work and failure behavior without changing indexing, ranking, retrieval thresholds, or prompting.

## Changes

- Deterministically validate citation labels in the verifier's final output against retrieved context, rejecting unavailable or silently removed draft citations.

1. Compile only the configured routing branch. The adaptive path does not create unused legacy Qdrant, Gemini, and Neo4j clients.
2. Start query embedding inside the hybrid retrieval task, concurrently with Neo4j graph probing. This removes the embedding-first dependency on the graph path while preserving the same evidence/reranking inputs.
2. Defer Neo4j connectivity to the actual graph probe so the existing Qdrant-only degraded route remains available if graph access is down.
3. Set bounded Neo4j driver connection/acquisition/retry settings (5s/8s/3s by default). This is not a universal HTTP request deadline and DNS/platform timeouts can differ.
4. Propagate partial decomposition and degraded sub-retrieval information instead of marking incomplete composite answers as fully verified.
5. Resolve requested ready document IDs and missing source filenames using a targeted indexed lookup instead of a full graph-counting document catalog query.
6. Remove a frontend state-reset effect that prevented the shared GitHub Actions quality job from running to completion.

## Measurement plan (before claiming a speedup)

- Collect >=30 cold/warm catalog calls and 30 safe, representative chat queries when Neo4j is available.
- Segment p50/p95 into service initialization, embedding, Qdrant, Neo4j, reranking, generation, verification, and browser end-to-end.
- Compare success/error/degraded rates and verification/citation quality on the same fixed corpus and question set.
- Use `python backend/tools/benchmark_live.py --base https://tracegraph-ai-backend.vercel.app --requests 6` for a small smoke sample; chat calls spend provider quota and require explicit opt-in flags.
- Exercise a simulated Neo4j failure in unit tests, and test actual outage behavior in a controlled non-production environment.

## Research applied

- Neo4j Python driver manual: explicit database selection, connection pooling, routing, and profiling, https://neo4j.com/docs/python-manual/current/performance/
- Neo4j driver API: acquisition, TCP connection, and retry budget configuration, https://neo4j.com/docs/api/python-driver/current/api.html
- RAGRouter-Bench (2026): retrieval selection should consider quality/latency trade-offs by query and corpus, https://arxiv.org/abs/2602.00296
- Qdrant hybrid query API: existing parallel dense/BM25 prefetch and RRF are retained, https://qdrant.tech/documentation/search/hybrid-queries/

## Release

Keep this on a feature branch until backend unit tests, frontend lint/typecheck/build, and the preview deployment pass. No database migration or credential rotation is required.

- Skip loading the CPU cross-encoder entirely when both retrieval channels return zero candidates. This avoids unnecessary model initialization on empty collections and abstention paths.

- Empty retrieval results now return a genuinely empty context instead of synthetic placeholder text, allowing the existing research and verification fast paths to avoid unnecessary provider calls on unsupported questions.
