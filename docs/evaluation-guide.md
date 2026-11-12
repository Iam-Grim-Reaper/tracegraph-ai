# TraceGraph evaluation protocol (2026)

An investor-facing reliability claim needs **two** evidence sets:

1. **CI / structural safety:** deterministic JSONL fixtures and machine-readable result reports. The workflow runs `backend/tools/evaluate_offline.py` on a tiny synthetic smoke corpus. This tests the metric calculator and integrity gate, **not** real-world retrieval quality.
2. **Held-out real corpus:** label 50–100 realistic single- and multi-hop questions across documents. Include at least 15 unknown/unanswerable questions, source IDs, expected evidence, document scopes, and latency measured against a working backend. Capture complete JSON responses and compare the same queries and index state across builds.

## Measured automatically by the evaluation tool

- Recall@K: fraction of known-relevant chunks retrieved.
- Precision@K: share of returned top-K chunks that are relevant.
- MRR@K: reciprocal rank of the first relevant chunk.
- nDCG@K: ranking quality with binary relevance labels.
- Citation label validity: literal citations in the final text match returned evidence IDs. **This is not proof of semantic factuality**.
- Document-scope integrity: all returned evidence remains inside the allowed document IDs.
- Abstention agreement: expected vs reported abstentions; does not evaluate the natural-language contents.
- Latency p50/p95: only reported if every captured result includes a measured latency value.

## Usage

```bash
cd backend
uv run --no-sync python tools/evaluate_offline.py --input evaluation/smoke.jsonl --output evaluation-smoke-report.json --strict
```

For real evaluation, use a JSONL file with a case ID, `relevant_chunk_ids`, `allowed_document_ids`, `expect_abstention`, and a captured `result` containing `retrieved_chunk_ids`, `evidence_items`, `answer`, `answer_status`, and `latency_ms` (measured by a client). Keep PII out of public test fixtures.

## Release gates to adopt after a real gold set exists

Before merging retrieval-model or candidate-budget changes, compare quality on *held-out* questions. A speed gain must not hide scope leakage, invalid citations, a regression in abstention quality, or large multi-hop recall loss. Establish numerical budgets only after collecting baseline production telemetry. In particular, do not present CI smoke-fixture scores as external benchmark results.

## Research context

- Microsoft Research, AgenticRAG (May 2026): targeted tool-driven search and in-document navigation can substantially improve difficult information retrieval; model and task dependence matter, so include difficult cases in evaluation.
- RAGRouter-Bench (2026): no single retrieval paradigm wins across corpus/query contexts.
- Qdrant Hybrid Queries (current): use unweighted RRF unless weights have been tuned on a held-out evaluation set.

## Additional reliability invariants

- Query decomposition IDs are required to be consecutive `q1`/`q2`/`q3` identifiers, preserving the same citation format across model-generated plans and regex validation.
- When all subquestion retrieval attempts fail, the context is empty rather than a fabricated text placeholder. The researcher and verifier can abstain deterministically without treating that placeholder as evidence.
