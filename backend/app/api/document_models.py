from typing import Literal

from pydantic import BaseModel


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    file_type: str
    title: str | None = None
    author: str | None = None

    chunk_count: int = 0
    entity_count: int = 0
    graph_relationship_count: int = 0

    status: Literal["ready"] = "ready"


class DocumentUploadResponse(
    DocumentSummary
):
    qdrant_indexed_chunks: int

    graph_rejected_relationship_count: int
    graph_cached_chunks: int
    graph_extracted_chunks: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]
    total: int