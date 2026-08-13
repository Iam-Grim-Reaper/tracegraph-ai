import re

from pydantic import BaseModel, Field, field_validator

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

    entity_type: EntityType | str
    original_entity_type: str | None = None

    @field_validator("entity_type", mode="before")
    @classmethod
    def validate_raw_entity_type(cls, value):
        if isinstance(value, EntityType):
            return value
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9 _-]{0,63}", value.strip()):
            raise ValueError("entity_type must be a safe non-empty type name")
        try:
            return EntityType(value.strip())
        except ValueError:
            return value.strip()

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

    source_type: EntityType | str

    target_name: str = Field(
        min_length=1,
        max_length=200,
    )

    target_type: EntityType | str

    @field_validator("source_type", "target_type", mode="before")
    @classmethod
    def validate_raw_endpoint_type(cls, value):
        return EntityCandidate.validate_raw_entity_type(value)

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
class ChunkGraphExtraction(BaseModel):
    """
    Graph information extracted from one chunk.
    """

    chunk_index: int = Field(
        ge=0
    )

    entities: list[EntityCandidate] = Field(
        default_factory=list
    )

    relationships: list[
        RelationshipCandidate
    ] = Field(
        default_factory=list
    )


class GraphExtractionBatch(BaseModel):
    """
    Structured response for multiple chunks.
    """

    chunks: list[
        ChunkGraphExtraction
    ] = Field(
        default_factory=list
    )


class RawEntityCandidate(BaseModel):
    """Provider-facing entity with transport-safe raw type strings."""

    name: str = Field(min_length=1, max_length=200)
    entity_type: str
    original_entity_type: str | None = None
    aliases: list[str] = Field(default_factory=list)


class RawRelationshipCandidate(BaseModel):
    """Provider-facing relationship before ontology normalization."""

    source_name: str = Field(min_length=1, max_length=200)
    source_type: str
    target_name: str = Field(min_length=1, max_length=200)
    target_type: str
    relationship_type: RelationshipType
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_text: str = Field(min_length=1)


class RawChunkGraphExtraction(BaseModel):
    """Provider-facing graph extraction for one source chunk."""

    chunk_index: int = Field(ge=0)
    entities: list[RawEntityCandidate] = Field(default_factory=list)
    relationships: list[RawRelationshipCandidate] = Field(default_factory=list)


class RawGraphExtractionBatch(BaseModel):
    """Gemini response contract, converted immediately to internal models."""

    chunks: list[RawChunkGraphExtraction] = Field(default_factory=list)

class GraphEntity(BaseModel):
    """
    Canonical entity ready for Neo4j.
    """

    entity_id: str

    name: str

    normalized_name: str

    entity_type: EntityType
    original_entity_type: str | None = None

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
