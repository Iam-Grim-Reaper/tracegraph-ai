from pydantic import BaseModel, Field

from app.graph.schema import (
    EntityType,
    RelationshipType,
)


class EntityCandidate(BaseModel):
    """
    Raw entity proposed by the extraction model.
    """

    name: str = Field(
        min_length=1,
        max_length=200,
    )

    entity_type: EntityType

    aliases: list[str] = Field(
        default_factory=list
    )


class RelationshipCandidate(BaseModel):
    """
    Raw relationship proposed by the
    extraction model.
    """

    source_name: str = Field(
        min_length=1,
        max_length=200,
    )

    source_type: EntityType

    target_name: str = Field(
        min_length=1,
        max_length=200,
    )

    target_type: EntityType

    relationship_type: RelationshipType

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    evidence_text: str = Field(
        min_length=1,
    )


class ExtractedGraph(BaseModel):
    """
    Structured output returned by the
    graph extraction stage.
    """

    entities: list[EntityCandidate] = Field(
        default_factory=list
    )

    relationships: list[
        RelationshipCandidate
    ] = Field(
        default_factory=list
    )


class GraphEntity(BaseModel):
    """
    Canonical entity ready for Neo4j.
    """

    entity_id: str

    name: str

    normalized_name: str

    entity_type: EntityType

    aliases: list[str] = Field(
        default_factory=list
    )


class GraphRelationship(BaseModel):
    """
    Validated relationship ready for Neo4j.
    Includes provenance back to source evidence.
    """

    source_entity_id: str

    target_entity_id: str

    relationship_type: RelationshipType

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    evidence_text: str

    source_document_id: str

    source_chunk_id: str

    page_number: int | None = Field(
        default=None,
        ge=1,
    )