from uuid import uuid4

from app.graph.extraction_cache import (
    GraphExtractionCache,
)
from app.graph.models import (
    EntityCandidate,
    ExtractedGraph,
)
from app.graph.schema import EntityType
from app.models.document import (
    DocumentChunk,
)


def test_cache_returns_none_when_missing(
    tmp_path,
):
    cache = GraphExtractionCache(
        cache_dir=tmp_path
    )

    chunk = DocumentChunk(
        document_id=uuid4(),
        chunk_index=0,
        text="Example chunk text.",
    )

    assert cache.get(chunk) is None


def test_cache_round_trip(
    tmp_path,
):
    cache = GraphExtractionCache(
        cache_dir=tmp_path
    )

    chunk = DocumentChunk(
        document_id=uuid4(),
        chunk_index=0,
        text="Grad-CAM explains the model.",
    )

    graph = ExtractedGraph(
        entities=[
            EntityCandidate(
                name="Grad-CAM",
                entity_type=(
                    EntityType.METHOD
                ),
                aliases=[],
            )
        ],
        relationships=[],
    )

    cache.set(
        chunk=chunk,
        graph=graph,
    )

    restored = cache.get(
        chunk
    )

    assert restored is not None
    assert len(restored.entities) == 1
    assert (
        restored.entities[0].name
        == "Grad-CAM"
    )


def test_cache_is_chunk_specific(
    tmp_path,
):
    cache = GraphExtractionCache(
        cache_dir=tmp_path
    )

    document_id = uuid4()

    first = DocumentChunk(
        document_id=document_id,
        chunk_index=0,
        text="First chunk.",
    )

    second = DocumentChunk(
        document_id=document_id,
        chunk_index=1,
        text="Second chunk.",
    )

    graph = ExtractedGraph(
        entities=[],
        relationships=[],
    )

    cache.set(
        chunk=first,
        graph=graph,
    )

    assert cache.get(first) is not None
    assert cache.get(second) is None