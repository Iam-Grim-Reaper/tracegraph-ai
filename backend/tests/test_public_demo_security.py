import logging

from fastapi.testclient import TestClient

from app.api.routes import documents as documents_module
from app.core.config import Settings
from app.core.observability import JsonFormatter
from app.core import provider_resilience
from app.graph import store as graph_store
from app.main import create_app
from app.retrieval import hybrid_store


def public_demo_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="production",
        gemini_api_key="test-gemini-key",
        qdrant_url="https://qdrant.invalid",
        qdrant_api_key="test-qdrant-key",
        qdrant_hybrid_collection="chunks",
        neo4j_uri="neo4j://neo4j.invalid",
        neo4j_username="neo4j-user",
        neo4j_password="test-neo4j-password",
        neo4j_database="neo4j",
        cors_allowed_origins="https://app.example",
        public_uploads_enabled=False,
    )


def test_public_demo_upload_rejection_prevents_parsing_and_indexing(monkeypatch, caplog):
    attempted_operations: list[str] = []

    def forbidden(name: str):
        def fail(*args, **kwargs):
            attempted_operations.append(name)
            raise AssertionError(f"{name} must not run when uploads are disabled")

        return fail

    monkeypatch.setattr(documents_module, "DocumentIndexingService", forbidden("indexing"))
    monkeypatch.setattr(provider_resilience, "create_gemini_client", forbidden("gemini"))
    monkeypatch.setattr(hybrid_store, "QdrantClient", forbidden("qdrant"))
    monkeypatch.setattr(graph_store.GraphDatabase, "driver", forbidden("neo4j"))

    document_contents = "document-contents-must-not-be-logged"
    caplog.set_level(logging.INFO, logger="app.main")
    with TestClient(create_app(public_demo_settings())) as client:
        response = client.post(
            "/api/documents",
            content=(
                b"--missing\r\n"
                b"Content-Disposition: form-data; name=\"file\"; filename=\"demo.txt\"\r\n\r\n"
                + document_contents.encode()
                + b"\r\n--missing--\r\n"
            ),
            headers={"Content-Type": "multipart/form-data; boundary=missing"},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Document upload is disabled in the public demo."}
    assert attempted_operations == []
    rendered = "\n".join(JsonFormatter().format(record) for record in caplog.records)
    assert "document_upload_rejected" in rendered
    assert document_contents not in rendered


def test_public_demo_document_catalog_reports_uploads_disabled(monkeypatch):
    monkeypatch.setattr(documents_module.DocumentCatalogService, "list_documents", lambda self: [])

    with TestClient(create_app(public_demo_settings())) as client:
        response = client.get("/api/documents")

    assert response.status_code == 200
    assert response.json() == {"documents": [], "total": 0, "uploads_enabled": False}


def test_development_uploads_still_reach_the_indexing_route(monkeypatch):
    indexed_paths = []

    class IndexingService:
        def index_file(self, path):
            indexed_paths.append(path)
            return type(
                "Result",
                (),
                {
                    "document_id": "document-1",
                    "filename": "demo.txt",
                    "file_type": "txt",
                    "title": None,
                    "ontology_profile": "general",
                    "ontology_version": "1",
                    "ontology_profiles": ["general"],
                    "ontology_confidence": 1.0,
                    "ontology_method": "deterministic",
                    "ontology_reason": "test",
                    "ontology_scores": {},
                    "chunk_count": 1,
                    "graph_entity_count": 0,
                    "graph_relationship_count": 0,
                    "qdrant_indexed_chunks": 1,
                    "graph_rejected_relationship_count": 0,
                    "graph_cached_chunks": 0,
                    "graph_extracted_chunks": 1,
                },
            )()

    monkeypatch.setattr(documents_module, "DocumentIndexingService", IndexingService)
    with TestClient(create_app(Settings(_env_file=None, app_env="development"))) as client:
        response = client.post(
            "/api/documents",
            files={"file": ("demo.txt", b"development document", "text/plain")},
        )

    assert response.status_code == 201
    assert len(indexed_paths) == 1


def test_production_disables_fastapi_docs_and_openapi():
    with TestClient(create_app(public_demo_settings())) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_development_keeps_fastapi_docs_and_openapi_available():
    with TestClient(create_app(Settings(_env_file=None, app_env="development"))) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200
        assert client.get("/openapi.json").status_code == 200
