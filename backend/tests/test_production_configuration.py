from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from app.api.routes import health as health_module
from app.core.config import ProductionConfigurationError, Settings
from app.core import provider_resilience
from app.main import create_app


def production_values(reranker_path: Path) -> dict:
    return {
        "app_env": "production",
        "gemini_api_key": "test-gemini-key",
        "qdrant_url": "https://qdrant.invalid",
        "qdrant_api_key": "test-qdrant-key",
        "qdrant_hybrid_collection": "chunks",
        "neo4j_uri": "neo4j://neo4j.invalid",
        "neo4j_username": "neo4j-user",
        "neo4j_password": "test-neo4j-password",
        "neo4j_database": "neo4j",
        "reranker_model_name": str(reranker_path),
        "cors_allowed_origins": "https://app.example,https://preview.example",
        "public_uploads_enabled": False,
    }


def settings_for(**values) -> Settings:
    return Settings(_env_file=None, **values)


@pytest.fixture
def reranker_path(tmp_path):
    model_path = tmp_path / "reranker"
    model_path.mkdir()
    (model_path / "config.json").write_text("{}", encoding="utf-8")
    (model_path / "model.safetensors").write_bytes(b"model")
    (model_path / "tokenizer.json").write_text("{}", encoding="utf-8")
    (model_path / "tokenizer_config.json").write_text("{}", encoding="utf-8")
    return model_path


@pytest.fixture
def local_settings(tmp_path, reranker_path):
    return settings_for(
        app_env="test",
        gemini_api_key="test-gemini-key",
        qdrant_url="https://qdrant.invalid",
        qdrant_api_key="test-qdrant-key",
        qdrant_hybrid_collection="chunks",
        neo4j_uri="neo4j://neo4j.invalid",
        neo4j_username="neo4j-user",
        neo4j_password="test-neo4j-password",
        neo4j_database="neo4j",
        reranker_model_name=str(reranker_path),
        graph_extraction_cache_dir=tmp_path / "cache",
    )


@pytest.fixture
def local_client_constructors(monkeypatch):
    class LocalClient:
        def close(self):
            pass

        def query(self, *args, **kwargs):
            raise AssertionError("remote Qdrant query called")

    class LocalDriver:
        def close(self):
            pass

        def verify_connectivity(self):
            raise AssertionError("Neo4j connectivity called")

    monkeypatch.setattr(health_module, "QdrantClient", lambda **kwargs: LocalClient())
    monkeypatch.setattr(
        health_module.GraphDatabase,
        "driver",
        lambda *args, **kwargs: LocalDriver(),
    )


def test_development_config_remains_usable():
    config = settings_for(app_env="development")
    assert config.debug is True
    assert config.public_uploads_enabled is True
    assert config.allowed_cors_origins == ["http://localhost:3000"]


def test_test_config_remains_usable_and_defaults_debug_false():
    config = settings_for(app_env="test")
    assert config.debug is False


def test_production_with_required_settings_validates(reranker_path):
    config = settings_for(**production_values(reranker_path))
    assert config.app_env == "production"
    assert config.debug is False


@pytest.mark.parametrize(
    "field_name,variable_name",
    [
        ("gemini_api_key", "GEMINI_API_KEY"),
        ("qdrant_url", "QDRANT_URL"),
        ("neo4j_password", "NEO4J_PASSWORD"),
    ],
)
def test_missing_production_setting_fails_safely(
    reranker_path,
    field_name,
    variable_name,
):
    values = production_values(reranker_path)
    values[field_name] = "   "
    with pytest.raises(ProductionConfigurationError, match=variable_name):
        settings_for(**values)


def test_configuration_error_does_not_include_secret_values(reranker_path):
    values = production_values(reranker_path)
    values["gemini_api_key"] = None
    values["neo4j_password"] = "do-not-expose-this-password"
    with pytest.raises(ProductionConfigurationError) as caught:
        settings_for(**values)
    assert "GEMINI_API_KEY" in str(caught.value)
    assert "do-not-expose-this-password" not in str(caught.value)


def test_production_debug_true_is_rejected(reranker_path):
    values = production_values(reranker_path)
    values["debug"] = True
    with pytest.raises(ProductionConfigurationError, match="DEBUG"):
        settings_for(**values)


def test_production_public_uploads_enabled_is_rejected(reranker_path):
    values = production_values(reranker_path)
    values["public_uploads_enabled"] = True
    with pytest.raises(ProductionConfigurationError, match="PUBLIC_UPLOADS_ENABLED"):
        settings_for(**values)


def test_invalid_app_env_is_rejected():
    with pytest.raises(ValidationError):
        settings_for(app_env="staging")


def test_invalid_routing_mode_is_rejected():
    with pytest.raises(ValidationError):
        settings_for(query_routing_mode="unsupported")


@pytest.mark.parametrize(
    "values",
    [
        {"provider_max_attempts": 0},
        {"provider_default_timeout_seconds": 0},
        {
            "provider_retry_base_delay_seconds": 2,
            "provider_retry_max_delay_seconds": 1,
        },
    ],
)
def test_invalid_provider_controls_are_rejected(values):
    with pytest.raises(ValidationError):
        settings_for(**values)


def test_development_localhost_origin_is_configured():
    config = settings_for(app_env="development")
    assert "http://localhost:3000" in config.allowed_cors_origins


def test_multiple_production_origins_are_parsed(reranker_path):
    config = settings_for(**production_values(reranker_path))
    assert config.allowed_cors_origins == [
        "https://app.example",
        "https://preview.example",
    ]


def test_production_wildcard_origin_is_rejected(reranker_path):
    values = production_values(reranker_path)
    values["cors_allowed_origins"] = "*"
    with pytest.raises(ProductionConfigurationError, match="CORS_ALLOWED_ORIGINS"):
        settings_for(**values)


def test_unconfigured_origin_receives_no_cors_authorization():
    with TestClient(create_app(settings_for(app_env="test"))) as client:
        response = client.options(
            "/api/chat/stream",
            headers={
                "Origin": "https://foreign.example",
                "Access-Control-Request-Method": "POST",
            },
        )
    assert "access-control-allow-origin" not in response.headers


def test_configured_origin_and_sse_post_are_cors_compatible(reranker_path):
    config = settings_for(**production_values(reranker_path))
    with TestClient(create_app(config)) as client:
        response = client.options(
            "/api/chat/stream",
            headers={
                "Origin": "https://app.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.example"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_health_is_local_and_returns_200(monkeypatch):
    monkeypatch.setattr(
        health_module,
        "QdrantClient",
        lambda **kwargs: pytest.fail("Qdrant constructed by health"),
    )
    monkeypatch.setattr(
        health_module.GraphDatabase,
        "driver",
        lambda *args, **kwargs: pytest.fail("Neo4j constructed by health"),
    )
    with TestClient(create_app(settings_for(app_env="test"))) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_valid_local_configuration_returns_ready(
    monkeypatch,
    local_settings,
    local_client_constructors,
):
    monkeypatch.setattr(health_module, "settings", local_settings)
    with TestClient(create_app(local_settings)) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "tracegraph-api"}


def test_readiness_does_not_construct_gemini_client(
    monkeypatch,
    local_settings,
    local_client_constructors,
):
    monkeypatch.setattr(
        provider_resilience,
        "create_gemini_client",
        lambda *args, **kwargs: pytest.fail("Gemini client constructed by readiness"),
    )
    assert health_module.readiness_failures(local_settings) == []


def test_missing_reranker_path_returns_not_ready(
    monkeypatch,
    local_settings,
    local_client_constructors,
    tmp_path,
):
    config = local_settings.model_copy(
        update={"reranker_model_name": str(tmp_path / "missing")}
    )
    monkeypatch.setattr(health_module, "settings", config)
    with TestClient(create_app(config)) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["checks"][0]["component"] == "reranker"


def test_invalid_cache_path_returns_not_ready(
    monkeypatch,
    local_settings,
    local_client_constructors,
    tmp_path,
):
    invalid_path = tmp_path / "not-a-directory"
    invalid_path.write_text("file", encoding="utf-8")
    config = local_settings.model_copy(
        update={"graph_extraction_cache_dir": invalid_path}
    )
    monkeypatch.setattr(health_module, "settings", config)
    with TestClient(create_app(config)) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert any(
        check["component"] == "graph_cache"
        for check in response.json()["checks"]
    )


def test_readiness_uses_no_remote_operations_or_secrets(
    monkeypatch,
    local_settings,
    local_client_constructors,
):
    monkeypatch.setattr(health_module, "settings", local_settings)
    with TestClient(create_app(local_settings)) as client:
        response = client.get("/ready")
    body = response.text
    assert response.status_code == 200
    assert local_settings.gemini_api_key not in body
    assert local_settings.qdrant_api_key not in body
    assert local_settings.neo4j_password not in body


def test_mock_external_outage_does_not_fail_local_readiness(
    local_settings,
    local_client_constructors,
):
    assert health_module.readiness_failures(local_settings) == []
