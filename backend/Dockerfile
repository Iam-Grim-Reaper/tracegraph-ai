FROM ghcr.io/astral-sh/uv:0.9.24 AS uv

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    GRAPH_EXTRACTION_CACHE_DIR="/app/runtime/cache/graph_extractions" \
    RERANKER_MODEL_NAME="/app/models/reranker" \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    PORT=8080

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./

RUN uv sync --frozen --no-dev --no-install-project \
    && HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 .venv/bin/python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L6-v2').save('/app/models/reranker')" \
    && rm -rf /root/.cache/uv /root/.cache/huggingface \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/runtime/cache/graph_extractions \
    && chown -R appuser:appuser /app/runtime /app/models

COPY --chown=appuser:appuser app ./app

USER appuser

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
