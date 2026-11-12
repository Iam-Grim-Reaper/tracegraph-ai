from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile

from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

from app.core.config import Settings, settings

router = APIRouter(
    tags=["Health"],
)


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "tracegraph-api",
    }


def readiness_failures(app_settings: Settings) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []

    def failed(component: str, reason: str) -> None:
        failures.append({
            "component": component,
            "status": "failed",
            "reason": reason,
        })

    configuration_valid = (
        app_settings.app_env in {"development", "test", "production"}
        and app_settings.query_routing_mode in {"adaptive", "legacy"}
        and 0 < app_settings.embedding_dimensions <= 4096
        and 1 <= app_settings.provider_max_attempts <= 3
        and app_settings.provider_default_timeout_seconds > 0
        and app_settings.provider_long_timeout_seconds > 0
        and app_settings.provider_retry_base_delay_seconds >= 0
        and app_settings.provider_retry_max_delay_seconds
        >= app_settings.provider_retry_base_delay_seconds
    )
    if not configuration_valid:
        failed("configuration", "invalid_local_settings")

    reranker = Path(app_settings.reranker_model_name)
    requires_local_reranker = (
        app_settings.app_env == "production"
        or reranker.is_absolute()
        or app_settings.reranker_model_name.startswith(".")
    )
    if requires_local_reranker:
        if not reranker.is_dir():
            failed("reranker", "model_path_unavailable")
        elif (
            not (reranker / "config.json").is_file()
            or not (reranker / "tokenizer_config.json").is_file()
            or not (reranker / "tokenizer.json").is_file()
            or not any(
                (reranker / filename).is_file()
                for filename in ("model.safetensors", "pytorch_model.bin")
            )
        ):
            failed("reranker", "required_model_files_unavailable")

    try:
        cache_dir = app_settings.graph_extraction_cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=cache_dir):
            pass
    except (OSError, ValueError):
        failed("graph_cache", "path_unavailable")

    try:
        with tempfile.NamedTemporaryFile(dir=tempfile.gettempdir()):
            pass
    except (OSError, ValueError):
        failed("upload_runtime", "temporary_path_unavailable")

    if not app_settings.gemini_api_key or not app_settings.gemini_api_key.strip():
        failed("gemini", "missing_configuration")

    if (
        not app_settings.qdrant_url
        or not app_settings.qdrant_api_key
        or not app_settings.qdrant_hybrid_collection.strip()
    ):
        failed("qdrant", "missing_configuration")
    else:
        try:
            client = QdrantClient(
                url=app_settings.qdrant_url,
                api_key=app_settings.qdrant_api_key,
            )
            client.close()
        except Exception:
            failed("qdrant", "invalid_configuration")

    if (
        not app_settings.neo4j_uri
        or not app_settings.neo4j_username
        or not app_settings.neo4j_password
        or not app_settings.neo4j_database.strip()
    ):
        failed("neo4j", "missing_configuration")
    else:
        try:
            driver = GraphDatabase.driver(
                app_settings.neo4j_uri,
                auth=(app_settings.neo4j_username, app_settings.neo4j_password),
            )
            driver.close()
        except Exception:
            failed("neo4j", "invalid_configuration")

    return failures


def dependency_failures(app_settings: Settings) -> list[dict[str, str]]:
    """Optional network-level readiness probe. Never expose driver exceptions."""

    def qdrant_check() -> dict[str, str] | None:
        client = None
        try:
            client = QdrantClient(
                url=app_settings.qdrant_url,
                api_key=app_settings.qdrant_api_key,
                timeout=5,
            )
            client.get_collection(app_settings.qdrant_hybrid_collection)
            return None
        except Exception:
            return {
                "component": "qdrant",
                "status": "failed",
                "reason": "storage_unavailable",
            }
        finally:
            if client is not None:
                client.close()

    def neo4j_check() -> dict[str, str] | None:
        driver = None
        try:
            driver = GraphDatabase.driver(
                app_settings.neo4j_uri,
                auth=(app_settings.neo4j_username, app_settings.neo4j_password),
                connection_timeout=app_settings.neo4j_connection_timeout_seconds,
                connection_acquisition_timeout=app_settings.neo4j_acquisition_timeout_seconds,
                max_transaction_retry_time=app_settings.neo4j_max_transaction_retry_seconds,
            )
            driver.verify_connectivity()
            return None
        except Exception:
            return {
                "component": "neo4j",
                "status": "failed",
                "reason": "storage_unavailable",
            }
        finally:
            if driver is not None:
                driver.close()

    # Parallel probes avoid adding database latencies together. This is
    # operator-triggered, not run by the cheap /health or default /ready.
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(qdrant_check), pool.submit(neo4j_check)]
        return [result for future in futures if (result := future.result())]


@router.get("/ready")
async def readiness_check(
    deep: bool = Query(default=False, description="Opt-in live storage checks."),
):
    failures = readiness_failures(settings)
    if deep and not failures:
        failures.extend(await run_in_threadpool(dependency_failures, settings))
    if failures:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": "tracegraph-api",
                "checks": failures,
            },
        )
    return {
        "status": "ready",
        "service": "tracegraph-api",
    }
