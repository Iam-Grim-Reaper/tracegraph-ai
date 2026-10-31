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
        assert len(created) == 1
        assert created[0].queries == 3
        assert not created[0].closed
    finally:
        module.close_catalog_store()

    assert created[0].closed
