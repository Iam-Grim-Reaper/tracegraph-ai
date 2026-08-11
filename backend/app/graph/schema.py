from enum import StrEnum

from app.graph.store import Neo4jGraphStore


class EntityType(StrEnum):
    PERSON = "Person"
    ORGANIZATION = "Organization"
    TEAM = "Team"
    PROJECT = "Project"
    TECHNOLOGY = "Technology"
    PRODUCT = "Product"
    MODEL = "Model"
    METHOD = "Method"
    CONCEPT = "Concept"
    DATASET = "Dataset"
    LOCATION = "Location"
    EVENT = "Event"


class RelationshipType(StrEnum):
    CONTAINS = "CONTAINS"
    MENTIONS = "MENTIONS"
    USES = "USES"
    WORKS_ON = "WORKS_ON"
    OWNED_BY = "OWNED_BY"
    PART_OF = "PART_OF"
    DEPENDS_ON = "DEPENDS_ON"
    DEVELOPED_BY = "DEVELOPED_BY"
    RELATED_TO = "RELATED_TO"
    LOCATED_IN = "LOCATED_IN"
    GENERATED_BY = "GENERATED_BY"
    

    # Useful for research / technical documents.
    TRAINED_ON = "TRAINED_ON"
    EVALUATED_ON = "EVALUATED_ON"
    EXPLAINED_BY = "EXPLAINED_BY"
    APPLIES_TO = "APPLIES_TO"


ALLOWED_ENTITY_TYPES = {
    entity_type.value
    for entity_type in EntityType
}

ALLOWED_RELATIONSHIP_TYPES = {
    relationship_type.value
    for relationship_type in RelationshipType
}

EXTRACTABLE_RELATIONSHIP_TYPES = (
    ALLOWED_RELATIONSHIP_TYPES
    - {
        RelationshipType.CONTAINS.value,
        RelationshipType.MENTIONS.value,
    }
)


SCHEMA_QUERIES = [
    """
    CREATE CONSTRAINT document_id_unique
    IF NOT EXISTS
    FOR (d:Document)
    REQUIRE d.document_id IS UNIQUE
    """,

    """
    CREATE CONSTRAINT chunk_id_unique
    IF NOT EXISTS
    FOR (c:Chunk)
    REQUIRE c.chunk_id IS UNIQUE
    """,

    """
    CREATE CONSTRAINT entity_id_unique
    IF NOT EXISTS
    FOR (e:Entity)
    REQUIRE e.entity_id IS UNIQUE
    """,

    """
    CREATE INDEX entity_normalized_name
    IF NOT EXISTS
    FOR (e:Entity)
    ON (e.normalized_name)
    """,

    """
    CREATE INDEX entity_type
    IF NOT EXISTS
    FOR (e:Entity)
    ON (e.entity_type)
    """,

    """
    CREATE INDEX chunk_document_id
    IF NOT EXISTS
    FOR (c:Chunk)
    ON (c.document_id)
    """,
]

RELATIONSHIP_GUIDANCE = {
    "USES": (
        "The source explicitly uses the target "
        "method, technology, model, or resource."
    ),
    "WORKS_ON": (
        "A person or team explicitly works on "
        "the target project or product."
    ),
    "OWNED_BY": (
        "The source is explicitly owned by "
        "the target."
    ),
    "PART_OF": (
        "The source is structurally or "
        "organizationally part of the target. "
        "Do not use this merely because the "
        "target uses the source."
    ),
    "DEPENDS_ON": (
        "The source explicitly depends on "
        "the target."
    ),
    "DEVELOPED_BY": (
        "The source was developed or created "
        "by the target."
    ),
    "RELATED_TO": (
        "A meaningful relationship is explicit "
        "but no more specific allowed "
        "relationship applies."
    ),
    "LOCATED_IN": (
        "The source is explicitly located in "
        "the target location."
    ),
    "GENERATED_BY": (
        "The source was explicitly generated "
        "or produced by the target."
    ),
    "TRAINED_ON": (
        "A model was explicitly trained using "
        "the target dataset."
    ),
    "EVALUATED_ON": (
        "A model or system was explicitly "
        "evaluated or tested on the target "
        "dataset."
    ),
    "EXPLAINED_BY": (
        "A model or system has its predictions "
        "explained or interpreted using the "
        "target method."
    ),
    "APPLIES_TO": (
        "A method, technique, or concept is "
        "explicitly applied to the target."
    ),
}

def initialize_graph_schema(
    store: Neo4jGraphStore,
) -> None:
    print("Initializing TraceGraph schema...")

    for query in SCHEMA_QUERIES:
        store.query(query)

    print(
        f"Configured {len(SCHEMA_QUERIES)} "
        "constraints/indexes."
    )