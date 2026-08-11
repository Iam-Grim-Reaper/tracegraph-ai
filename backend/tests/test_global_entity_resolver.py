from app.graph.entity_resolver import (
    GlobalEntityResolver,
)
from app.graph.models import (
    GraphEntity,
    GraphRelationship,
)
from app.graph.postprocessor import (
    ProcessedChunkGraph,
)
from app.graph.schema import (
    EntityType,
    RelationshipType,
)


class FakeGraphStore:
    def __init__(
        self,
        rows=None,
    ):
        self.rows = rows or []

    def query(
        self,
        cypher,
        parameters=None,
    ):
        return self.rows


def test_reuses_existing_entity_by_alias():
    store = FakeGraphStore(
        rows=[
            {
                "entity_id": "existing-gradcam",
                "name": (
                    "Gradient-weighted Class "
                    "Activation Mapping"
                ),
                "normalized_name": (
                    "gradient weighted class "
                    "activation mapping"
                ),
                "entity_type": "Method",
                "aliases": [
                    "Grad-CAM",
                ],
                "normalized_aliases": [
                    "grad cam",
                ],
            }
        ]
    )

    resolver = GlobalEntityResolver(
        store=store
    )

    entity = GraphEntity(
        entity_id="local-gradcam",
        name="Grad-CAM",
        normalized_name="grad cam",
        entity_type=EntityType.METHOD,
        aliases=[],
    )

    graph = ProcessedChunkGraph(
        entities=[entity],
        relationships=[],
        rejected_relationships=[],
    )

    resolved = resolver.resolve(
        graph
    )

    assert len(resolved.entities) == 1

    assert (
        resolved.entities[0].entity_id
        == "existing-gradcam"
    )

    assert (
        resolved.entities[0].name
        ==
        "Gradient-weighted Class "
        "Activation Mapping"
    )

    assert (
        "Grad-CAM"
        in resolved.entities[0].aliases
    )


def test_keeps_new_entity_when_no_match():
    store = FakeGraphStore(
        rows=[]
    )

    resolver = GlobalEntityResolver(
        store=store
    )

    entity = GraphEntity(
        entity_id="new-entity",
        name="LC25000",
        normalized_name="lc25000",
        entity_type=EntityType.DATASET,
        aliases=[],
    )

    graph = ProcessedChunkGraph(
        entities=[entity],
        relationships=[],
        rejected_relationships=[],
    )

    resolved = resolver.resolve(
        graph
    )

    assert (
        resolved.entities[0].entity_id
        == "new-entity"
    )


def test_relationship_ids_are_remapped():
    class MappingStore:
        def query(
            self,
            cypher,
            parameters=None,
        ):
            if (
                parameters[
                    "normalized_name"
                ]
                == "grad cam"
            ):
                return [
                    {
                        "entity_id": (
                            "existing-gradcam"
                        ),
                        "name": (
                            "Gradient-weighted "
                            "Class Activation "
                            "Mapping"
                        ),
                        "normalized_name": (
                            "gradient weighted "
                            "class activation "
                            "mapping"
                        ),
                        "entity_type": (
                            "Method"
                        ),
                        "aliases": [
                            "Grad-CAM"
                        ],
                        "normalized_aliases": [
                            "grad cam"
                        ],
                    }
                ]

            return []

    resolver = GlobalEntityResolver(
        store=MappingStore()
    )

    gradcam = GraphEntity(
        entity_id="local-gradcam",
        name="Grad-CAM",
        normalized_name="grad cam",
        entity_type=EntityType.METHOD,
        aliases=[],
    )

    convnext = GraphEntity(
        entity_id="local-convnext",
        name="ConvNeXt-Small",
        normalized_name=(
            "convnext small"
        ),
        entity_type=EntityType.MODEL,
        aliases=[],
    )

    relationship = GraphRelationship(
        source_entity_id=(
            "local-gradcam"
        ),
        target_entity_id=(
            "local-convnext"
        ),
        relationship_type=(
            RelationshipType.APPLIES_TO
        ),
        confidence=0.95,
        evidence_text=(
            "Grad-CAM was applied to "
            "ConvNeXt-Small."
        ),
        source_document_id="doc-1",
        source_chunk_id="chunk-1",
        page_number=5,
    )

    graph = ProcessedChunkGraph(
        entities=[
            gradcam,
            convnext,
        ],
        relationships=[
            relationship
        ],
        rejected_relationships=[],
    )

    resolved = resolver.resolve(
        graph
    )

    assert (
        resolved.relationships[0]
        .source_entity_id
        ==
        "existing-gradcam"
    )

    assert (
        resolved.relationships[0]
        .target_entity_id
        ==
        "local-convnext"
    )