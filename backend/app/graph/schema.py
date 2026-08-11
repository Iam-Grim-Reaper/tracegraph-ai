from enum import StrEnum

from app.graph.store import Neo4jGraphStore


class EntityType(StrEnum):
    PERSON = "Person"
    ORGANIZATION = "Organization"
    TEAM = "Team"
    PROJECT = "Project"
    TECHNOLOGY = "Technology"
    PRODUCT = "Product"
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