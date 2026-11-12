from app.services import document_catalog_service as module


def test_catalog_uses_one_process_shared_store_and_closes_at_shutdown(monkeypatch):
    created = []
    class FakeStore:
        def __init__(self):
            self.queries = 0
            self.closed = False
            created.append(self)

        def query(self, cypher, parameters=None):
            self.queries += 1
            return []

        def close(self):
            self.closed = True

    module.close_catalog_store()
    monkeypatch.setattr(module, "Neo4jGraphStore", FakeStore)
    try:
        first = module.DocumentCatalogService()
        second = module.DocumentCatalogService()

        assert first.list_documents() == []
        assert second.list_documents() == []
        assert second.get_document("missing") is None
        assert first.get_ready_filenames(["missing"]) == {}
        assert first.get_ready_filenames([]) == {}
        assert len(created) == 1
        assert created[0].queries == 4
        assert not created[0].closed
    finally:
        module.close_catalog_store()

    assert created[0].closed

def test_ready_filename_lookup_is_scoped_to_requested_document_ids(monkeypatch):
    queries = []

    class FakeStore:
        def query(self, query, parameters):
            queries.append((query, parameters))
            return [{"document_id": "doc-a", "filename": "a.pdf"}]

    monkeypatch.setattr(module, "_get_catalog_store", lambda: FakeStore())
    filenames = module.DocumentCatalogService().get_ready_filenames(
        ["doc-b", "doc-a", "doc-a"]
    )
    assert filenames == {"doc-a": "a.pdf"}
    assert len(queries) == 1
    query, params = queries[0]
    assert params == {"document_ids": ["doc-a", "doc-b"]}
    assert "d.document_id IN $document_ids" in query
    assert "d.indexing_status = 'ready'" in query
    assert "count(" not in query.lower()
