from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class FileType(str, Enum):
    PDF = "pdf"
    TXT = "txt"
    MARKDOWN = "md"


class DocumentMetadata(BaseModel):
    title: str | None = None
    author: str | None = None
    page_count: int | None = None
    language: str | None = None


class Document(BaseModel):
    id: UUID = Field(default_factory=uuid4)

    filename: str
    file_type: FileType

    status: DocumentStatus = DocumentStatus.UPLOADED

    storage_uri: str | None = None

    metadata: DocumentMetadata = Field(
        default_factory=DocumentMetadata
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

class ParsedPage(BaseModel):
    page_number: int = Field(ge=1)
    text: str


class ChunkMetadata(BaseModel):
    page_number: int | None = None
    section: str | None = None
    heading: str | None = None


class DocumentChunk(BaseModel):
    id: UUID = Field(default_factory=uuid4)

    document_id: UUID

    chunk_index: int

    text: str

    contextual_text: str | None = None

    metadata: ChunkMetadata = Field(
        default_factory=ChunkMetadata
    )

    previous_chunk_id: UUID | None = None
    next_chunk_id: UUID | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Citation(BaseModel):
    document_id: UUID
    chunk_id: UUID

    filename: str

    page_number: int | None = None
    section: str | None = None

    quoted_text: str | None = None
    
class IngestionResult(BaseModel):
    document: Document
    chunks: list[DocumentChunk]