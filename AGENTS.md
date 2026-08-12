# Repository Guidelines

## Project Structure & Module Organization

TraceGraph AI has two applications. `backend/app/` contains the FastAPI service, organized into API routes, configuration, ingestion, graph, retrieval, and agent workflow packages. Unit tests belong in `backend/tests/`; root-level `backend/test_*.py`, `index_*.py`, `compare_*.py`, and `verify_*.py` files are integration or diagnostic scripts. `frontend/src/app/` holds the Next.js UI, `frontend/lib/` contains API clients, and `frontend/public/` stores static assets. Local data is not versioned.

## Build, Test, and Development Commands

Run commands from the indicated module directory.

- `cd backend && uv sync --dev`: install Python 3.11-3.13 dependencies from `uv.lock`.
- `uv run uvicorn app.main:app --reload`: serve the API locally with reload.
- `uv run pytest tests`: run the focused backend unit suite.
- `uv run pytest test_retrieval_router.py`: run one integration test; some require Neo4j, Qdrant, or Gemini.
- `cd frontend && npm ci`: install the locked frontend dependencies.
- `npm run dev`: start Next.js at `http://localhost:3000`.
- `npm run lint`: apply the Next.js TypeScript and Core Web Vitals lint rules.
- `npm run build`: create a production build; `npm run preview` tests Cloudflare/OpenNext locally.

## Coding Style & Naming Conventions

Use four spaces and type annotations in Python. Name modules and functions `snake_case`, classes `PascalCase`, and constants `UPPER_SNAKE_CASE`. In TypeScript, retain strict typing and two-space indentation; use `PascalCase` for components and types, and `camelCase` for functions and state. Prefer the `@/*` alias for `frontend/src/` imports.

## Testing Guidelines

Pytest is the backend test framework. Name files `test_<behavior>.py` and tests `test_<expected_outcome>`. Put deterministic unit tests in `backend/tests/`; document external prerequisites for integration tests. No frontend test runner is configured, so validate UI work with lint, a production build, and browser checks.

## Commit & Pull Request Guidelines

History uses concise Conventional Commit subjects such as `feat: add document upload and full indexing pipeline`. Use an imperative `type: summary` line (`feat`, `fix`, `test`, `docs`, or `refactor`) and keep commits scoped. Pull requests should explain the change and verification performed, link relevant issues, identify configuration or schema impacts, and include screenshots for visible UI changes.

## Security & Configuration

Copy `backend/.env.example` to `backend/.env` for local setup. Never commit credentials, uploaded documents, caches, or generated index data. Use placeholders in example configuration and rotate any credential that is accidentally exposed.
