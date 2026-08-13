FROM ghcr.io/astral-sh/uv:0.9.24 AS uv

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    GRAPH_EXTRACTION_CACHE_DIR="/app/runtime/cache/graph_extractions" \
    PORT=8080

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./

RUN uv sync --frozen --no-dev --no-install-project \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/runtime/cache/graph_extractions \
    && chown -R appuser:appuser /app/runtime

COPY --chown=appuser:appuser app ./app

USER appuser

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
