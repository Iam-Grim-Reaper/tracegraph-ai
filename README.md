# TraceGraph AI

**Evidence-first document intelligence with hybrid retrieval, knowledge graphs, and explicit verification.**

[Live workspace](https://tracegraph-ai.vercel.app/app) · [Evaluation summary](docs/evaluation-summary.md) · [Evaluation protocol](docs/evaluation-guide.md) · [Demo readiness](docs/investor-demo-readiness.md)

TraceGraph answers questions about indexed documents and lets users inspect the source passages and graph relationships behind an answer. It is designed to abstain when supporting evidence is missing, rather than treating a fluent model response as sufficient proof.

## Why it exists

A conventional document chatbot can retrieve relevant passages but struggle with relationships spread across multiple files. TraceGraph combines semantic/lexical retrieval with a provenance-linked entity graph, then asks a separate verifier to check the answer. The result includes the actual source evidence, retrieval route, degradation state and execution diagnostics.

## Architecture

```text
Next.js 16 / React 19 research workspace
        |
   FastAPI HTTP + SSE
        |
   LangGraph orchestration
        |
    [Question]
        |
    Adaptive retrieval / optional decomposition
      /                             \
 Qdrant: Gemini embeddings     Neo4j Aura: entities,
 + BM25 + native RRF           relationships + provenance
      \                             /
       Candidate evidence + cross-encoder
                    |
          Gemini research draft
                    |
      Verification + citation checks
                    |
          Verified, partial, degraded,
          or abstained response + sources
```

### Capabilities

- PDF, plain text, Markdown, DOCX, PPTX and XLSX ingestion with stable document and chunk IDs.
- Contextualized dense embeddings, BM25, RRF fusion and local cross-encoder reranking.
- Ontology-aware graph extraction and scoped multi-hop Neo4j retrieval.
- Conditional multi-part query decomposition, one bounded verification retry, and failure-aware routing.
- Source passages, graph facts, citation validation, safe abstention, and user-visible processing stages.
- Browser-visible end-to-end timing and backend-stage diagnostic metrics.
- Explicit document readiness states across Qdrant and Neo4j.

**Deployment notice:** The public version is a read-only portfolio demonstration. Visitor uploads are disabled. Production authentication, per-tenant data isolation, quotas and service-level guarantees are **not yet implemented**, and should be completed before accepting real customer documents.

## Run locally

Prerequisites: Python 3.11, [uv](https://docs.astral.sh/uv/), Node.js 22, and credentials for Gemini, Neo4j and Qdrant.

```bash
cd backend
cp .env.example .env
# Set APP_ENV=development, configure provider/database values and local CORS origin.
uv sync --frozen --group dev
uv run uvicorn app.main:app --reload
```

In a separate terminal:

```bash
cd frontend
npm ci
# Configure frontend/.env.local:
# NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
# NEXT_PUBLIC_UPLOADS_ENABLED=true
npm run dev
```

The frontend runs at `http://localhost:3000`. The API responds on `http://127.0.0.1:8000`.

## Verify quality

```bash
cd backend
uv run --no-sync pytest -q tests
uv run --no-sync python tools/evaluate_offline.py --input evaluation/smoke.jsonl --output evaluation-smoke-report.json --strict
# Optional read-only endpoint checks against an authorized running service:
uv run --no-sync python tools/benchmark_live.py --base https://tracegraph-ai-backend.vercel.app --requests 6
```

```bash
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

GitHub Actions runs both suites and publishes a **synthetic structural evaluation** artifact. The evaluation tool computes Recall@K, Precision@K, MRR, nDCG, citation-label validity, scope integrity, abstention agreement and latency percentiles from captured results.

**Evaluation caveat:** The [historical comparison](docs/evaluation-summary.md) used 15 cases across 4 variants (60 retrieval-only runs) on a small controlled corpus. Those results are not a general accuracy guarantee. The CI smoke fixtures are synthetic and do not establish semantic faithfulness or live latency. A held-out real-document evaluation is required before publishing quality or performance claims.

## Performance strategy

1. Start graph search concurrently with query embedding and Qdrant retrieval.
2. Avoid constructing unused graph clients in adaptive mode and bound Neo4j connection waits.
3. Validate selected document scopes through indexed lookups, not a full graph catalog aggregation.
4. Keep the CPU reranker lazy and skip it when there are no evidence candidates.
5. Do not present partially retrieved answers as completely verified.
6. Compare proposed retrieval changes on the **same labeled questions** using quality and p50/p95 metrics; only ship changes whose trade-offs are acceptable.

Technical notes: [backend optimization](docs/backend-performance-2026.md) · [evaluation guide](docs/evaluation-guide.md).

## Roadmap toward production

- Restore and monitor database availability, and populate an authorized demo corpus.
- Build a held-out 50–100-question benchmark covering direct, relational, multi-hop, negative, and failure cases.
- Add authenticated ingestion, tenant-aware access control, rate limiting, and audit requirements.
- Profile Neo4j entity linking and catalog aggregation using `PROFILE` on a representative database.
- Introduce cost-per-query, uptime, throughput and first-response monitoring; set SLOs from observed baselines.

No unverified “best RAG” or percentage speedup claims are made here; the project is intended to be **measurable, auditable and continuously improvable**.
