"""The public demo may expose only the three content-addressed GitHub files."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.document_models import DocumentSummary
from app.api.routes import documents as documents_route
from app.core.config import Settings
from app.demo.public_corpus import (
    PUBLIC_DEMO_DOCUMENTS, PUBLIC_DEMO_IDS,
    is_public_demo_mode, validate_demo_file,
)
from app.main import create_app
from app.services import tracegraph_service as service_module
from tools.seed_public_demo import preflight


def test_public_demo_manifest_matches_real_repository_files():
    root = Path(__file__).resolve().parents[2]
    assert len(PUBLIC_DEMO_DOCUMENTS) == len(PUBLIC_DEMO_IDS) == 3
    assert [x.file_type.value for x in PUBLIC_DEMO_DOCUMENTS] == ["pdf", "docx", "pptx"]
    for item in PUBLIC_DEMO_DOCUMENTS:
        assert validate_demo_file(item, root).is_file()


def test_manifest_rejects_changed_or_missing_files(tmp_path):
    item = PUBLIC_DEMO_DOCUMENTS[0]
    with pytest.raises(FileNotFoundError):
        validate_demo_file(item, tmp_path)
    (tmp_path / item.filename).write_bytes(b"replacement-content")
    with pytest.raises(ValueError, match="checksum mismatch"):
        validate_demo_file(item, tmp_path)


def test_preflight_extracts_all_three_documents_without_cloud_calls():
    rows = preflight(Path(__file__).resolve().parents[2])
    assert len(rows) == 3
    assert all(row["status"] == "preflight_passed" for row in rows)
    assert all(row["chunks"] > 0 and row["text_characters"] > 0 for row in rows)


def prod_settings():
    return Settings(
        _env_file=None,
        app_env="production",
        gemini_api_key="dummy-gemini",
        qdrant_url="https://qdrant.invalid",
        qdrant_api_key="dummy-qdrant",
        qdrant_hybrid_collection="chunks",
        neo4j_uri="neo4j://neo4j.invalid",
        neo4j_username="neo4j",
        neo4j_password="dummy-pass",
        neo4j_database="neo4j",
        cors_allowed_origins="https://example.test",
        public_uploads_enabled=False,
    )


def test_production_is_hard_locked_to_public_corpus():
    assert is_public_demo_mode(prod_settings())
    assert not is_public_demo_mode(Settings(_env_file=None, app_env="test"))
    with pytest.raises(Exception, match="PUBLIC_DEMO_ONLY"):
        prod_settings().model_copy(update={"public_demo_only": False}).model_validate(
            {**prod_settings().model_dump(), "public_demo_only": False}
        )


def test_catalog_does_not_expose_unapproved_documents(monkeypatch):
    approved = PUBLIC_DEMO_DOCUMENTS[0]
    unexpected = "7be1c789-76f2-4cc7-a9a6-98a9a132f59e"
    docs = [
        DocumentSummary(document_id=approved.document_id, filename=approved.filename, file_type="pdf"),
        DocumentSummary(document_id=unexpected, filename="private.pdf", file_type="pdf"),
    ]
    monkeypatch.setattr(documents_route.DocumentCatalogService, "list_documents", lambda self: docs)
    monkeypatch.setattr(
        documents_route.DocumentCatalogService,
        "get_document",
        lambda self, doc_id: next((d for d in docs if d.document_id == doc_id), None),
    )
    with TestClient(create_app(prod_settings())) as client:
        catalog = client.get("/api/documents")
        hidden = client.get("/api/documents/" + unexpected)
        allowed = client.get("/api/documents/" + approved.document_id)
        upload = client.post(
            "/api/documents",
            files={"file": ("attempt.pdf", b"%PDF-1.4", "application/pdf")},
        )
    assert catalog.status_code == 200
    assert catalog.json()["total"] == 1
    assert catalog.json()["uploads_enabled"] is False
    assert catalog.json()["documents"][0]["document_id"] == approved.document_id
    assert hidden.status_code == 404
    assert allowed.status_code == 200
    assert upload.status_code == 403


def test_default_chat_scope_is_exactly_ready_demo_documents(monkeypatch):
    approved = PUBLIC_DEMO_DOCUMENTS[0]
    seen = []

    class Catalog:
        def get_ready_filenames(self, document_ids):
            seen.append(set(document_ids))
            return {approved.document_id: approved.filename}

    monkeypatch.setattr(service_module, "settings", SimpleNamespace(app_env="production", public_demo_only=True))
    monkeypatch.setattr(service_module, "DocumentCatalogService", Catalog)
    service = service_module.TraceGraphService.__new__(service_module.TraceGraphService)
    question, selected = service._prepare_request(" Which author? ", None)
    assert question == "Which author?"
    assert selected == [approved.document_id]
    assert seen == [set(PUBLIC_DEMO_IDS)]


def test_chat_rejects_other_document_ids_even_when_ready(monkeypatch):
    class Catalog:
        def get_ready_filenames(self, document_ids):
            return {doc_id: "private.pdf" for doc_id in document_ids}

    monkeypatch.setattr(service_module, "settings", SimpleNamespace(app_env="production", public_demo_only=True))
    monkeypatch.setattr(service_module, "DocumentCatalogService", Catalog)
    service = service_module.TraceGraphService.__new__(service_module.TraceGraphService)
    with pytest.raises(ValueError, match="not available in the public demo"):
        service._prepare_request("What is in private.pdf?", ["private-document-id"])


def test_chat_fails_closed_until_an_approved_document_is_ready(monkeypatch):
    class Catalog:
        def get_ready_filenames(self, document_ids):
            return {}

    monkeypatch.setattr(service_module, "settings", SimpleNamespace(app_env="production", public_demo_only=True))
    monkeypatch.setattr(service_module, "DocumentCatalogService", Catalog)
    service = service_module.TraceGraphService.__new__(service_module.TraceGraphService)
    with pytest.raises(ValueError, match="not ready"):
        service._prepare_request("Who developed this?", None)


def test_seed_cli_invocation_from_backend_directory():
    """The operator workflow must resolve app imports with no PYTHONPATH."""
    import subprocess
    import sys

    backend = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "tools/seed_public_demo.py", "--mode", "preflight"],
        cwd=backend,
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-1500:]
    import json
    output = json.loads(result.stdout)
    assert output["approved_document_count"] == 3
    assert all(row["status"] == "preflight_passed" for row in output["results"])
