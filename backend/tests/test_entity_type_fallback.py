import pytest

from app.graph.extractor import GraphExtractor
from app.graph.models import (
    EntityCandidate,
    GraphExtractionBatch,
    RawGraphExtractionBatch,
    RelationshipCandidate,
)
from app.graph.ontology import GENERAL_ONTOLOGY, RESEARCH_ONTOLOGY
from app.graph.schema import EntityType, RelationshipType
from app.graph.normalizer import EntityNormalizer
from app.graph.writer import Neo4jGraphWriter


def extractor(profile=GENERAL_ONTOLOGY):
    instance = GraphExtractor.__new__(GraphExtractor)
    instance.ontology_profile = profile
    return instance


def relationship(source_type, target_type):
    return RelationshipCandidate(
        source_name="Orion",
        source_type=source_type,
        target_name="Apache Spark",
        target_type=target_type,
        relationship_type=RelationshipType.USES,
        confidence=0.9,
        evidence_text="Orion uses Apache Spark.",
    )


def test_valid_general_type_remains_unchanged():
    entity = EntityCandidate(name="Orion", entity_type=EntityType.PROJECT)
    entities, _ = extractor()._normalize_profile_entity_types([entity], [], "doc-1")
    assert entities[0].entity_type == EntityType.PROJECT
    assert entities[0].original_entity_type is None


def test_valid_specialized_type_remains_unchanged():
    entity = EntityCandidate(name="Apache Spark", entity_type=EntityType.TECHNOLOGY)
    entities, _ = extractor(RESEARCH_ONTOLOGY)._normalize_profile_entity_types([entity], [], "doc-1")
    assert entities[0].entity_type == EntityType.TECHNOLOGY
    assert entities[0].original_entity_type is None


@pytest.mark.parametrize("raw_type", ["Technology", "Framework"])
def test_unknown_or_inactive_type_uses_concept_fallback(raw_type):
    entity = EntityCandidate(name="Apache Spark", entity_type=raw_type)
    entities, _ = extractor()._normalize_profile_entity_types([entity], [], "doc-1")
    assert entities[0].entity_type == EntityType.CONCEPT
    assert entities[0].original_entity_type == raw_type


def test_relationship_endpoint_types_follow_normalized_entities():
    entities = [
        EntityCandidate(name="Orion", entity_type=EntityType.PROJECT),
        EntityCandidate(name="Apache Spark", entity_type="Framework"),
    ]
    normalized, relationships = extractor()._normalize_profile_entity_types(
        entities, [relationship(EntityType.PROJECT, "Framework")], "doc-1"
    )
    assert normalized[1].entity_type == EntityType.CONCEPT
    assert relationships[0].source_type == EntityType.PROJECT
    assert relationships[0].target_type == EntityType.CONCEPT
    extractor()._validate_profile_output(normalized, relationships)


@pytest.mark.parametrize("raw_type", ["", "../Technology", "A" * 65, 42])
def test_malformed_type_is_rejected(raw_type):
    with pytest.raises(ValueError):
        EntityCandidate(name="unsafe", entity_type=raw_type)


def test_writer_persists_normalized_and_original_type():
    class Store:
        def __init__(self):
            self.parameters = None

        def query(self, _query, parameters):
            self.parameters = parameters

    store = Store()
    writer = Neo4jGraphWriter.__new__(Neo4jGraphWriter)
    writer.store = store
    writer.normalizer = EntityNormalizer()
    entity = EntityNormalizer().normalize_entity(EntityCandidate(
        name="Apache Spark",
        entity_type=EntityType.CONCEPT,
        original_entity_type="Technology",
    ))
    writer._write_entities([entity])
    assert store.parameters["entity_type"] == "Concept"
    assert store.parameters["original_entity_type"] == "Technology"
    assert store.parameters["name"] == "Apache Spark"


def test_provider_schema_uses_raw_endpoint_type_strings():
    schema = RawGraphExtractionBatch.model_json_schema()
    definitions = schema["$defs"]
    entity_properties = definitions["RawEntityCandidate"]["properties"]
    relationship_properties = definitions["RawRelationshipCandidate"]["properties"]

    assert entity_properties["entity_type"]["type"] == "string"
    assert "anyOf" not in entity_properties["entity_type"]
    for field in ("source_type", "target_type"):
        assert relationship_properties[field]["type"] == "string"
        assert "anyOf" not in relationship_properties[field]

    assert "anyOf" in entity_properties["original_entity_type"]
    assert relationship_properties["relationship_type"]["$ref"].endswith(
        "/RelationshipType"
    )


@pytest.mark.parametrize(
    ("raw_type", "expected_type", "expected_original"),
    [
        ("Technology", EntityType.CONCEPT, "Technology"),
        ("Framework", EntityType.CONCEPT, "Framework"),
        ("Project", EntityType.PROJECT, None),
    ],
)
def test_raw_provider_response_converts_then_normalizes(
    raw_type,
    expected_type,
    expected_original,
):
    raw = RawGraphExtractionBatch.model_validate({
        "chunks": [{
            "chunk_index": 0,
            "entities": [{"name": "Apache Spark", "entity_type": raw_type}],
            "relationships": [],
        }],
    })
    internal = GraphExtractionBatch.model_validate(raw.model_dump())
    entities, _ = extractor()._normalize_profile_entity_types(
        internal.chunks[0].entities,
        internal.chunks[0].relationships,
        "doc-1",
    )
    assert entities[0].entity_type == expected_type
    assert entities[0].original_entity_type == expected_original


def test_raw_relationship_endpoints_convert_and_normalize():
    raw = RawGraphExtractionBatch.model_validate({
        "chunks": [{
            "chunk_index": 0,
            "entities": [
                {"name": "Orion", "entity_type": "Project"},
                {"name": "Apache Spark", "entity_type": "Technology"},
            ],
            "relationships": [{
                "source_name": "Orion",
                "source_type": "Project",
                "target_name": "Apache Spark",
                "target_type": "Technology",
                "relationship_type": "USES",
                "confidence": 0.9,
                "evidence_text": "Orion uses Apache Spark.",
            }],
        }],
    })
    internal = GraphExtractionBatch.model_validate(raw.model_dump())
    entities, relationships = extractor()._normalize_profile_entity_types(
        internal.chunks[0].entities,
        internal.chunks[0].relationships,
        "doc-1",
    )
    assert relationships[0].source_type == EntityType.PROJECT
    assert relationships[0].target_type == EntityType.CONCEPT
    extractor()._validate_profile_output(entities, relationships)
