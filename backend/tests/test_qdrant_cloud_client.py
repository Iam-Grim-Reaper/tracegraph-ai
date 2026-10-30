from types import SimpleNamespace

import pytest

from app.retrieval import hybrid_store as module


@pytest.mark.parametrize(
    ("url", "expected_cloud_inference"),
    [
        (
            "https://example.us-east-1.aws.cloud.qdrant.io",
            True,
        ),
        ("http://tracegraph-qdrant:6333", False),
        ("https://my-self-hosted-qdrant.example.com", False),
    ],
)
def test_bm25_inference_mode_matches_qdrant_host(
    monkeypatch,
    url,
    expected_cloud_inference,
):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(module, "QdrantClient", fake_client)
    monkeypatch.setattr(
        module,
        "settings",
        SimpleNamespace(
            qdrant_url=url,
            qdrant_api_key="test-key",
            qdrant_hybrid_collection="test-hybrid",
            embedding_dimensions=768,
        ),
    )

    store = module.HybridStore()

    assert store.collection_name == "test-hybrid"
    assert captured["cloud_inference"] is expected_cloud_inference
