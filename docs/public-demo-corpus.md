# TraceGraph fixed public demo corpus

The repository contains **exactly three approved public demo documents**:

| File | Stable document ID | Original extracted chunks |
|---|---|---|
| `SHREY DOC FINAL.pdf` | `05d5c184-d8cf-5e93-9117-f86a47a0da38` | 173 |
| `Team 16 12 (1).docx` | `c3b3b47a-cfbb-52be-9b7a-58f7d342fc95` | 592 |
| `Team 33 Final PPT.pptx` | `f9c77928-151c-5170-8c8a-d7e2315140eb` | 35 |

These chunk counts are from the exact repository files as parsed with the existing loaders and 1000-character chunker; they are **not proof of indexed/ready status**.

## Security model

- Production visitor `POST /api/documents` remains disabled before multipart parsing.
- Production `GET /api/documents` displays only the three approved stable document IDs.
- `GET /api/documents/{id}` refuses any other ID (HTTP 404).
- Both `/api/chat` and `/api/chat/stream` enforce the allowlist server-side, including when a visitor omits document_ids. Arbitrary client-provided IDs cannot bypass this.
- Files are SHA256-verified against `backend/app/demo/public_corpus.py` before any indexing writes. Replacing a file requires deliberate manifest maintenance.
- Never expose Gemini, Qdrant, or Neo4j credentials in the browser or GitHub source. Indexing is an administrative CLI, not a public upload route.

## Preflight and indexing

Run from the repository's backend directory:

```bash
uv sync --frozen
uv run python tools/seed_public_demo.py --mode preflight
```

To index on trusted infrastructure with the matching production Gemini/Qdrant/Neo4j environment:

```bash
uv run python tools/seed_public_demo.py --mode index
uv run python tools/seed_public_demo.py --mode verify
```

**GitHub Actions:** Open **Actions → Public demo corpus — controlled indexing → Run workflow**. Select `preflight`, then `index`, then `verify`. Index and verify require six matching repository or environment secrets: `GEMINI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`. The workflow deliberately fails before accessing databases when any secret is missing.

Match the Vercel backend's production `QDRANT_HYBRID_COLLECTION`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `NEO4J_DATABASE`, and optional model configuration using GitHub Actions **variables** if they differ from script defaults.

### Cost and runtime

The source corpus extracts about **800 chunks**. Contextualizing, embedding and graph-indexing this corpus can create substantial provider requests and take much longer than a typical web request. Run the CLI as an operator job, **never** from a public request or a Vercel serverless function. If rate-limited, stop and retry after provider quota recovers. Stable document IDs and the ready-state guard make completed documents safe to revisit without reindexing.

### Final checks

1. Confirm Neo4j Aura is running and `/ready?deep=true` succeeds.
2. Confirm `GET /api/documents` reports `uploads_enabled: false` and exactly these three ready documents.
3. Ask a source-specific question from each file, and open its evidence citation.
4. Send an explicit ID outside the approved set to `/api/chat`; it must return HTTP 400.
5. Upload attempt to `POST /api/documents` must return HTTP 403.

Do not describe the demo as ready until the production catalog and real questions are verified.
