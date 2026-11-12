# Investor demo readiness — TraceGraph AI

The strongest demo is an answer whose sources can be inspected, then a multi-hop question whose graph relationship is traced, followed by a deliberately unanswerable question that abstains.

## Pre-flight checks

- [ ] Neo4j Aura instance is RUNNING (AuraDB Free may pause after prolonged inactivity). The configured URI resolves and credentials are valid.
- [ ] Qdrant Cloud collection exists, is responsive, and uses the intended embedding dimensions and indexed document/status payloads.
- [ ] The backend's `/health` is live **and** `GET /api/documents` returns HTTP 200 with at least one ready document. `/health` alone does not test storage dependencies.
- [ ] The frontend shows the same documents, with no endless loading placeholders.
- [ ] At least three authorized, non-sensitive indexed files contain known supporting passages and entity relationships. Do not represent fabricated fixtures as real customer records.
- [ ] Backend, frontend and synthetic evaluation CI checks pass on the commit being deployed.
- [ ] All representative answers return valid source references, and the source drawer displays the original relevant excerpt.
- [ ] A difficult negative question is answered with an honest abstention, not invented evidence.
- [ ] Degraded behavior during a temporary Neo4j interruption is demonstrated on a nonproduction environment.
- [ ] A repeatable `benchmark_live.py` report exists for that **exact** deployment and corpus, with a labeled set of real questions and first vs warm samples reported separately.

## Four-minute demonstration narrative

1. **Problem:** ordinary document search finds paragraphs but cannot reliably follow relationships, and generative answers alone are not verifiable.
2. **Direct search:** ask a fact question from a known document, inspect the quoted passage and page or cell locator.
3. **Multi-hop:** ask how two concepts or people relate across documents, showing graph evidence and linked provenance.
4. **Trust:** ask an intentionally unsupported question. Show the abstention and/or partial evidence rather than a confident invented answer.
5. **Engineering:** show routing, Qdrant/Neo4j/reranker stage times, response status, and a real held-out evaluation report.

## What an investor can verify in the current repository

- Quality gates: backend tests, frontend lint/typecheck/build, and synthetic source-integrity smoke tests.
- Existing controlled comparison: 15 labeled cases × 4 retrieval methods (60 retrieval-only runs), with graph-related benefits and limitations documented.
- Source support: final-citation validation and read-only ingestion status boundaries.
- Reliability: adaptive degraded retrieval, Neo4j timeout settings and skipped unnecessary model loading on empty evidence.

## Open risks — disclose them

- No proof of production-scale accuracy, availability or p95 latency until measurements are captured with a populated database.
- Graph extraction can produce questionable relationships; source-level verification and human checks are essential.
- The public portfolio API has no comprehensive auth/tenant isolation or distributed rate limits. Do **not** onboard external customers with sensitive data until those are built.
- A paused Neo4j instance can temporarily make the library unavailable. The static ONLINE indicator only means the API process responded.
- Cloud model and database quotas/costs must be measured under concurrent load.

## Before claiming product-market readiness

Secure a small real-document pilot (with consent), label evaluation questions, measure Recall@K and independently reviewed citation faithfulness, track cost per successful response and reliability over time, then compare against a plain hybrid RAG baseline. Use the [evaluation guide](evaluation-guide.md) to avoid reporting synthetic test scores as business impact.

## Storage diagnostics

Run `GET /ready?deep=true` during demo preflight to check live Neo4j connectivity and the configured Qdrant collection. This is a bounded, opt-in network probe; plain `/health` is liveness and plain `/ready` checks local configuration. The deep result uses sanitized component names and generic failures. It must not be continuously polled on a paused/free database or mistaken for an uptime SLO.
