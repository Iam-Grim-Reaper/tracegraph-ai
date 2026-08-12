from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)


OntologyMethod = Literal[
    "deterministic",
    "llm",
    "fallback",
    "explicit",
]


class DocumentSummary(
    BaseModel
):
    document_id: str
    filename: str
    file_type: str

    title: str | None = None
    author: str | None = None

    # =========================================
    # Ontology metadata
    # =========================================

    ontology_profile: (
        str | None
    ) = None

    ontology_version: (
        str | None
    ) = None

    ontology_profiles: list[
        str
    ] = Field(
        default_factory=list
    )

    ontology_confidence: (
        float | None
    ) = None

    ontology_method: (
        OntologyMethod | None
    ) = None

    ontology_reason: (
        str | None
    ) = None

    ontology_scores: dict[
        str,
        float,
    ] = Field(
        default_factory=dict
    )

    # =========================================
    # Graph / document statistics
    # =========================================

    chunk_count: int = 0
    entity_count: int = 0

    graph_relationship_count: (
        int
    ) = 0

    status: Literal[
        "ready"
    ] = "ready"


class DocumentUploadResponse(
    DocumentSummary
):
    qdrant_indexed_chunks: int

    graph_rejected_relationship_count: (
        int
    )

    graph_cached_chunks: int
    graph_extracted_chunks: int


class DocumentListResponse(
    BaseModel
):
    documents: list[
        DocumentSummary
    ]

    total: int