from enum import StrEnum
import logging

from app.core.observability import log_event
from app.graph.store import Neo4jGraphStore


logger = logging.getLogger(__name__)


# =========================================================
# ENTITY TYPES
#
# This enum is the complete vocabulary TraceGraph
# understands.
#
# Ontology profiles decide which subset is allowed
# for a particular document.
# =========================================================


class EntityType(StrEnum):
    # -----------------------------------------------------
    # Universal Core
    # -----------------------------------------------------

    PERSON = "Person"
    ORGANIZATION = "Organization"
    TEAM = "Team"
    PROJECT = "Project"
    PRODUCT = "Product"
    CONCEPT = "Concept"
    LOCATION = "Location"
    EVENT = "Event"

    # -----------------------------------------------------
    # Research / Technical
    # -----------------------------------------------------

    TECHNOLOGY = "Technology"
    MODEL = "Model"
    METHOD = "Method"
    DATASET = "Dataset"
    METRIC = "Metric"

    # -----------------------------------------------------
    # Career / Resume
    # -----------------------------------------------------

    ROLE = "Role"
    SKILL = "Skill"
    DEGREE = "Degree"
    CERTIFICATION = "Certification"
    EXPERIENCE = "Experience"

    # -----------------------------------------------------
    # Policy / Compliance
    # -----------------------------------------------------

    POLICY = "Policy"
    REQUIREMENT = "Requirement"
    REGULATION = "Regulation"
    CONTROL = "Control"
    EXCEPTION = "Exception"
    PROCEDURE = "Procedure"

    # -----------------------------------------------------
    # Contract / Legal
    # -----------------------------------------------------

    PARTY = "Party"
    CLAUSE = "Clause"
    OBLIGATION = "Obligation"
    RIGHT = "Right"


# =========================================================
# RELATIONSHIP TYPES
# =========================================================


class RelationshipType(StrEnum):
    # -----------------------------------------------------
    # Structural — application generated only
    # -----------------------------------------------------

    CONTAINS = "CONTAINS"
    MENTIONS = "MENTIONS"

    # -----------------------------------------------------
    # Universal Core
    # -----------------------------------------------------

    USES = "USES"
    WORKS_ON = "WORKS_ON"
    OWNED_BY = "OWNED_BY"
    PART_OF = "PART_OF"
    DEPENDS_ON = "DEPENDS_ON"
    DEVELOPED_BY = "DEVELOPED_BY"
    RELATED_TO = "RELATED_TO"
    LOCATED_IN = "LOCATED_IN"
    GENERATED_BY = "GENERATED_BY"
    APPLIES_TO = "APPLIES_TO"

    # -----------------------------------------------------
    # Research / Technical
    # -----------------------------------------------------

    TRAINED_ON = "TRAINED_ON"
    EVALUATED_ON = "EVALUATED_ON"
    EXPLAINED_BY = "EXPLAINED_BY"

    # -----------------------------------------------------
    # Career / Resume
    # -----------------------------------------------------

    WORKED_AT = "WORKED_AT"
    HAS_ROLE = "HAS_ROLE"
    HAS_SKILL = "HAS_SKILL"
    EARNED_DEGREE = "EARNED_DEGREE"
    CERTIFIED_IN = "CERTIFIED_IN"

    # -----------------------------------------------------
    # Policy / Compliance
    # -----------------------------------------------------

    REQUIRES = "REQUIRES"
    PROHIBITS = "PROHIBITS"
    GOVERNED_BY = "GOVERNED_BY"
    HAS_EXCEPTION = "HAS_EXCEPTION"

    # -----------------------------------------------------
    # Contract / Legal
    # -----------------------------------------------------

    HAS_OBLIGATION = "HAS_OBLIGATION"
    GRANTS_RIGHT = "GRANTS_RIGHT"
    APPLIES_TO_PARTY = "APPLIES_TO_PARTY"
    TERMINATES_ON = "TERMINATES_ON"


# =========================================================
# Backward-compatible global sets
#
# Older code/tests may still import these.
#
# Ontology-aware extraction will stop using these
# directly in the next migration stage.
# =========================================================


ALLOWED_ENTITY_TYPES = {
    entity_type.value
    for entity_type in EntityType
}


ALLOWED_RELATIONSHIP_TYPES = {
    relationship_type.value
    for relationship_type
    in RelationshipType
}


EXTRACTABLE_RELATIONSHIP_TYPES = (
    ALLOWED_RELATIONSHIP_TYPES
    - {
        RelationshipType.CONTAINS.value,
        RelationshipType.MENTIONS.value,
    }
)


# =========================================================
# Neo4j schema
# =========================================================


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

    """
    CREATE INDEX document_indexing_status
    IF NOT EXISTS
    FOR (d:Document)
    ON (d.indexing_status)
    """,
]


# =========================================================
# Relationship guidance
#
# The extractor will later select only the guidance
# belonging to the active ontology profile.
# =========================================================


RELATIONSHIP_GUIDANCE = {
    # -----------------------------------------------------
    # Universal
    # -----------------------------------------------------

    RelationshipType.USES.value: (
        "The source explicitly uses the target "
        "method, technology, product, model, "
        "resource, or concept."
    ),

    RelationshipType.WORKS_ON.value: (
        "A person or team explicitly works on "
        "the target project or product."
    ),

    RelationshipType.OWNED_BY.value: (
        "The source is explicitly owned by "
        "the target."
    ),

    RelationshipType.PART_OF.value: (
        "The source is structurally or "
        "organizationally part of the target. "
        "Do not use this merely because the "
        "target uses the source."
    ),

    RelationshipType.DEPENDS_ON.value: (
        "The source explicitly depends on "
        "the target."
    ),

    RelationshipType.DEVELOPED_BY.value: (
        "The source was developed or created "
        "by the target."
    ),

    RelationshipType.RELATED_TO.value: (
        "A meaningful relationship is explicit "
        "but no more specific allowed "
        "relationship applies."
    ),

    RelationshipType.LOCATED_IN.value: (
        "The source is explicitly located in "
        "the target location."
    ),

    RelationshipType.GENERATED_BY.value: (
        "The source was explicitly generated "
        "or produced by the target."
    ),

    RelationshipType.APPLIES_TO.value: (
        "A method, technique, policy, rule, "
        "procedure, or concept is explicitly "
        "applied to the target."
    ),

    # -----------------------------------------------------
    # Research
    # -----------------------------------------------------

    RelationshipType.TRAINED_ON.value: (
        "A model was explicitly trained using "
        "the target dataset."
    ),

    RelationshipType.EVALUATED_ON.value: (
        "A model or system was explicitly "
        "evaluated or tested on the target "
        "dataset."
    ),

    RelationshipType.EXPLAINED_BY.value: (
        "A model or system has its predictions "
        "explained or interpreted using the "
        "target method."
    ),

    # -----------------------------------------------------
    # Career
    # -----------------------------------------------------

    RelationshipType.WORKED_AT.value: (
        "A person explicitly worked at or was "
        "employed by the target organization."
    ),

    RelationshipType.HAS_ROLE.value: (
        "A person explicitly holds or held the "
        "target professional role."
    ),

    RelationshipType.HAS_SKILL.value: (
        "A person explicitly possesses or "
        "demonstrates the target skill."
    ),

    RelationshipType.EARNED_DEGREE.value: (
        "A person explicitly earned or completed "
        "the target academic degree."
    ),

    RelationshipType.CERTIFIED_IN.value: (
        "A person explicitly holds the target "
        "certification."
    ),

    # -----------------------------------------------------
    # Policy
    # -----------------------------------------------------

    RelationshipType.REQUIRES.value: (
        "The source explicitly requires the "
        "target condition, action, control, "
        "procedure, or requirement."
    ),

    RelationshipType.PROHIBITS.value: (
        "The source explicitly prohibits the "
        "target action or condition."
    ),

    RelationshipType.GOVERNED_BY.value: (
        "The source is explicitly governed by "
        "the target policy or regulation."
    ),

    RelationshipType.HAS_EXCEPTION.value: (
        "The source explicitly provides or "
        "contains the target exception."
    ),

    # -----------------------------------------------------
    # Contract
    # -----------------------------------------------------

    RelationshipType.HAS_OBLIGATION.value: (
        "A party explicitly has the target "
        "contractual obligation."
    ),

    RelationshipType.GRANTS_RIGHT.value: (
        "The source explicitly grants the target "
        "right to a party."
    ),

    RelationshipType.APPLIES_TO_PARTY.value: (
        "A clause, obligation, or right explicitly "
        "applies to the target contractual party."
    ),

    RelationshipType.TERMINATES_ON.value: (
        "A contractual clause or obligation "
        "explicitly terminates upon the target "
        "event or condition."
    ),
}


def initialize_graph_schema(
    store: Neo4jGraphStore,
) -> None:
    log_event(logger, logging.INFO, "graph_schema_initializing", operation="graph_schema", status="started")

    for query in SCHEMA_QUERIES:
        store.query(
            query
        )

    log_event(logger, logging.INFO, "graph_schema_initialized", operation="graph_schema", status="complete")
