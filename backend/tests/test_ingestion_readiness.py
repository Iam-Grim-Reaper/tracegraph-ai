from types import SimpleNamespace

import pytest
from qdrant_client import models

from app.graph.graph_query import GraphQueryRetriever
from app.graph.ontology import GENERAL_ONTOLOGY
from app.models.document import Document, DocumentChunk, FileType
from app.retrieval.hybrid_store import HybridStore
from app.services.document_indexing_service import DocumentIndexingService
from app.services.document_readiness_service import (
    FAILED,
    INDEXING,
    READY,
    DocumentReadinessService,
)


class FakeGraphStore:
    def __init__(self):
        self.statuses = {}
        self.legacy = []
        self.queries = []

    def query(self, query, parameters=None):
        parameters = parameters or {}
        self.queries.append((query, parameters))
        document_id = parameters.get("document_id")
        if "RETURN d.indexing_status = $ready AS ready" in query:
            status = self.statuses.get(document_id)
            return [] if status is None else [{"ready": status == READY}]
        if "RETURN already_ready" in query:
            already = self.statuses.get(document_id) == READY
            if not already:
                self.statuses[document_id] = INDEXING
            return [{"already_ready": already}]
        if "SET d.indexing_status = $failed" in query:
            if self.statuses.get(document_id) != READY:
                self.statuses[document_id] = FAILED
            return []
        if "SET d.indexing_status = $ready" in query and document_id:
            if self.statuses.get(document_id) in {None, INDEXING}:
                self.statuses[document_id] = READY
            return []
        if "WHERE d.indexing_status IS NULL" in query and "RETURN DISTINCT" in query:
            return [{"document_id": value} for value in self.legacy[: parameters["limit"]]]
        return []

    def close(self):
        pass

    def verify_connectivity(self):
        pass


class FakeHybridStore:
    def __init__(self):
        self.statuses = {}
        self.calls = []

    def set_document_status(self, document_id, status):
        self.calls.append((document_id, status))
        self.statuses[document_id] = status
        return 4

    def ensure_collection(self):
        self.calls.append(("ensure_collection", None))


def document(document_id="00000000-0000-0000-0000-000000000001"):
    return Document(id=document_id, filename="fixture.txt", file_type=FileType.TXT)


def test_new_indexing_starts_non_ready():
    graph = FakeGraphStore()
    service = DocumentReadinessService(graph, FakeHybridStore())
    assert service.begin_indexing(document()) is True
    assert graph.statuses[str(document().id)] == INDEXING


def test_qdrant_payload_written_during_indexing_is_non_ready():
    store = HybridStore.__new__(HybridStore)
    store.collection_name = "chunks"
    store.vector_size = 2
    captured = {}
    store.client = SimpleNamespace(upsert=lambda **kwargs: captured.update(kwargs))
    chunk = DocumentChunk(document_id=document().id, chunk_index=0, text="evidence")
    store.upsert_chunks(document(), [chunk], [[0.1, 0.2]])
    assert captured["points"][0].payload["indexing_status"] == INDEXING


@pytest.mark.parametrize("document_ids", [None, ["doc-1"]])
def test_hybrid_retrieval_always_filters_ready(document_ids):
    store = HybridStore.__new__(HybridStore)
    filter_ = store._build_document_filter(document_ids)
    conditions = {condition.key: condition.match for condition in filter_.must}
    assert conditions["indexing_status"].value == READY
    if document_ids:
        assert conditions["document_id"].any == document_ids


def test_exact_qdrant_retrieval_fails_closed_for_unknown_status():
    store = HybridStore.__new__(HybridStore)
    store.collection_name = "chunks"
    store.client = SimpleNamespace(retrieve=lambda **kwargs: [
        SimpleNamespace(payload={"indexing_status": READY}),
        SimpleNamespace(payload={"indexing_status": INDEXING}),
        SimpleNamespace(payload={}),
    ])
    assert len(store.retrieve_by_ids(["1", "2", "3"])) == 1


def test_graph_queries_require_ready_document():
    graph = FakeGraphStore()
    retriever = GraphQueryRetriever(graph)
    retriever.link_entities("Orion")
    retriever._retrieve_facts("entity", 2)
    retriever.retrieve_by_chunk_ids("question", ["chunk"])
    assert all("indexing_status = 'ready'" in query for query, _ in graph.queries)


def test_catalog_queries_exclude_indexing_and_failed(monkeypatch):
    from app.services import document_catalog_service as module

    graph = FakeGraphStore()
    monkeypatch.setattr(module, "Neo4jGraphStore", lambda: graph)
    module.DocumentCatalogService().list_documents()
    module.DocumentCatalogService().get_document("doc-1")
    assert all("indexing_status" in query and "'ready'" in query for query, _ in graph.queries)


def test_scope_validation_rejects_non_ready_document(monkeypatch):
    from app.services import tracegraph_service as module

    monkeypatch.setattr(module.DocumentCatalogService, "list_documents", lambda self: [])
    with pytest.raises(ValueError, match="do not exist"):
        module.TraceGraphService._validate_document_ids(["indexing-doc"])


def test_failed_document_remains_non_ready_everywhere():
    graph = FakeGraphStore()
    hybrid = FakeHybridStore()
    service = DocumentReadinessService(graph, hybrid)
    service.begin_indexing(document())
    service.mark_failed(str(document().id))
    assert service.is_ready(str(document().id)) is False
    assert hybrid.calls == []


def test_success_finalizes_qdrant_before_catalog():
    events = []
    graph = FakeGraphStore()
    hybrid = FakeHybridStore()
    original_query = graph.query
    graph.query = lambda query, parameters=None: (
        events.append("neo4j_ready") or original_query(query, parameters)
        if "SET d.indexing_status = $ready" in query
        else original_query(query, parameters)
    )
    hybrid.set_document_status = lambda document_id, status: events.append("qdrant_ready") or 4
    service = DocumentReadinessService(graph, hybrid)
    service.begin_indexing(document())
    assert service.finalize(str(document().id)) == 4
    assert events == ["qdrant_ready", "neo4j_ready"]
    assert service.is_ready(str(document().id))


def test_ready_qdrant_vectors_are_retrievable():
    store = HybridStore.__new__(HybridStore)
    store.collection_name = "chunks"
    ready = SimpleNamespace(payload={"indexing_status": READY})
    store.client = SimpleNamespace(retrieve=lambda **kwargs: [ready])
    assert store.retrieve_by_ids(["stable-id"]) == [ready]


def test_ready_document_is_never_marked_failed():
    graph = FakeGraphStore()
    graph.statuses[str(document().id)] = READY
    service = DocumentReadinessService(graph, FakeHybridStore())
    service.mark_failed(str(document().id))
    assert graph.statuses[str(document().id)] == READY


def test_failed_document_can_retry_to_ready():
    graph = FakeGraphStore()
    hybrid = FakeHybridStore()
    service = DocumentReadinessService(graph, hybrid)
    assert service.begin_indexing(document())
    service.mark_failed(str(document().id))
    assert service.begin_indexing(document())
    service.finalize(str(document().id))
    assert graph.statuses[str(document().id)] == READY


def test_stable_ids_do_not_change_across_failed_retry(tmp_path):
    path = tmp_path / "stable.txt"
    path.write_text("Stable enterprise evidence", encoding="utf-8")
    service = DocumentIndexingService(ontology_profile=GENERAL_ONTOLOGY)
    first = service.ingestion_service.ingest(path)
    second = service.ingestion_service.ingest(path)
    assert first.document.id == second.document.id
    assert [item.id for item in first.chunks] == [item.id for item in second.chunks]


def test_stable_qdrant_ids_replace_instead_of_duplicate():
    store = HybridStore.__new__(HybridStore)
    store.collection_name = "chunks"
    store.vector_size = 2
    points = {}
    store.client = SimpleNamespace(
        upsert=lambda **kwargs: points.update({str(p.id): p for p in kwargs["points"]})
    )
    chunk = DocumentChunk(document_id=document().id, chunk_index=0, text="same")
    store.upsert_chunks(document(), [chunk], [[0.1, 0.2]])
    store.upsert_chunks(document(), [chunk], [[0.1, 0.2]])
    assert len(points) == 1


@pytest.mark.parametrize("failure_point", ["graph_extraction", "neo4j_midway"])
def test_failure_after_qdrant_never_finalizes(failure_point):
    graph = FakeGraphStore()
    hybrid = FakeHybridStore()
    service = DocumentReadinessService(graph, hybrid)
    service.begin_indexing(document())
    hybrid.statuses[str(document().id)] = INDEXING
    service.mark_failed(str(document().id))
    assert graph.statuses[str(document().id)] == FAILED
    assert hybrid.statuses[str(document().id)] == INDEXING
    assert not service.is_ready(str(document().id))


def test_legacy_migration_marks_only_catalog_candidates_ready():
    graph = FakeGraphStore()
    graph.legacy = ["catalog-doc"]
    hybrid = FakeHybridStore()
    hybrid.statuses["orphan-doc"] = INDEXING
    result = DocumentReadinessService(graph, hybrid).migrate_legacy_ready_documents()
    assert result.documents_migrated == 1
    assert hybrid.statuses["catalog-doc"] == READY
    assert hybrid.statuses["orphan-doc"] == INDEXING


def test_legacy_migration_is_idempotent():
    graph = FakeGraphStore()
    graph.legacy = ["catalog-doc"]
    hybrid = FakeHybridStore()
    service = DocumentReadinessService(graph, hybrid)
    first = service.migrate_legacy_ready_documents()
    graph.legacy = []
    second = service.migrate_legacy_ready_documents()
    assert first.documents_migrated == 1
    assert second.documents_migrated == 0
    assert [call for call in hybrid.calls if call[1] == READY] == [("catalog-doc", READY)]


def test_migration_is_bounded():
    graph = FakeGraphStore()
    graph.legacy = ["a", "b", "c"]
    result = DocumentReadinessService(graph, FakeHybridStore()).migrate_legacy_ready_documents(limit=2)
    assert result.documents_migrated == 2


def test_status_index_creation_is_idempotent():
    store = HybridStore.__new__(HybridStore)
    store.collection_name = "chunks"
    calls = []
    store.client = SimpleNamespace(
        get_collection=lambda name: SimpleNamespace(payload_schema={"indexing_status": {}}),
        create_payload_index=lambda **kwargs: calls.append(kwargs),
    )
    store.ensure_status_index()
    assert calls == []


class FakeReadiness:
    instances = []

    def __init__(self):
        self.events = []
        self.__class__.instances.append(self)

    def begin_indexing(self, value):
        self.events.append(("begin", str(value.id)))
        return True

    def finalize(self, document_id):
        self.events.append(("finalize", document_id))

    def mark_failed(self, document_id):
        self.events.append(("failed", document_id))

    def close(self):
        self.events.append(("close", None))


def _patch_indexing(monkeypatch, graph_failure=False):
    from app.services import document_indexing_service as module

    FakeReadiness.instances = []
    monkeypatch.setattr(module, "DocumentReadinessService", FakeReadiness)
    monkeypatch.setattr(module.DocumentCatalogService, "get_document", lambda self, value: None)
    monkeypatch.setattr(
        module,
        "HybridIndexer",
        lambda: SimpleNamespace(index=lambda **kwargs: len(kwargs["chunks"])),
    )

    def graph_index(**kwargs):
        if graph_failure:
            raise RuntimeError("injected graph failure")
        return SimpleNamespace(
            entity_count=1,
            semantic_relationship_count=1,
            rejected_relationship_count=0,
            cached_chunks=0,
            extracted_chunks=len(kwargs["chunks"]),
        )

    monkeypatch.setattr(
        module,
        "GraphIndexer",
        lambda **kwargs: SimpleNamespace(index=graph_index),
    )
    monkeypatch.setattr(module.DocumentIndexingService, "_persist_ontology_metadata", lambda *args, **kwargs: None)


def test_failure_injection_qdrant_then_graph_is_invisible(tmp_path, monkeypatch):
    _patch_indexing(monkeypatch, graph_failure=True)
    path = tmp_path / "failure.txt"
    path.write_text("A bounded ingestion failure test.", encoding="utf-8")
    service = DocumentIndexingService(ontology_profile=GENERAL_ONTOLOGY)
    with pytest.raises(RuntimeError, match="injected graph failure"):
        service.index_file(path)
    events = FakeReadiness.instances[0].events
    assert any(event[0] == "failed" for event in events)
    assert not any(event[0] == "finalize" for event in events)


def test_failure_injection_mid_neo4j_is_invisible(tmp_path, monkeypatch):
    _patch_indexing(monkeypatch, graph_failure=True)
    path = tmp_path / "partial.txt"
    path.write_text("First graph chunk writes, then Neo4j fails.", encoding="utf-8")
    with pytest.raises(RuntimeError):
        DocumentIndexingService(ontology_profile=GENERAL_ONTOLOGY).index_file(path)
    assert FakeReadiness.instances[0].events[-2][0] == "failed"


def test_failure_injection_full_success_finalizes_ready(tmp_path, monkeypatch):
    _patch_indexing(monkeypatch)
    path = tmp_path / "success.txt"
    path.write_text("A complete deterministic indexing test.", encoding="utf-8")
    result = DocumentIndexingService(ontology_profile=GENERAL_ONTOLOGY).index_file(path)
    assert result.status == READY
    assert any(event[0] == "finalize" for event in FakeReadiness.instances[0].events)


def test_existing_ready_duplicate_short_circuits_before_provider(tmp_path, monkeypatch):
    from app.services import document_indexing_service as module

    path = tmp_path / "duplicate.txt"
    path.write_text("Already indexed bytes.", encoding="utf-8")
    parsed = DocumentIndexingService().ingestion_service.ingest(path)
    summary = SimpleNamespace(
        document_id=str(parsed.document.id), filename=path.name, file_type="txt",
        title=None, ontology_profile="general", ontology_version="2.0",
        ontology_profiles=["general"], ontology_confidence=0.8,
        ontology_method="deterministic", ontology_reason="ready",
        ontology_scores={}, chunk_count=len(parsed.chunks), entity_count=1,
        graph_relationship_count=1,
    )
    monkeypatch.setattr(module.DocumentCatalogService, "get_document", lambda self, value: summary)
    monkeypatch.setattr(module, "HybridIndexer", lambda: pytest.fail("provider/indexer called"))
    result = DocumentIndexingService().index_file(path)
    assert result.document_id == str(parsed.document.id)
    assert result.graph_extracted_chunks == 0


def test_failed_attempt_then_success_reuses_stable_document(tmp_path, monkeypatch):
    _patch_indexing(monkeypatch, graph_failure=True)
    path = tmp_path / "retry.txt"
    path.write_text("Stable retry content.", encoding="utf-8")
    service = DocumentIndexingService(ontology_profile=GENERAL_ONTOLOGY)
    stable = service.ingestion_service.ingest(path)
    with pytest.raises(RuntimeError):
        service.index_file(path)
    _patch_indexing(monkeypatch, graph_failure=False)
    result = DocumentIndexingService(ontology_profile=GENERAL_ONTOLOGY).index_file(path)
    assert result.document_id == str(stable.document.id)
    assert result.status == READY
