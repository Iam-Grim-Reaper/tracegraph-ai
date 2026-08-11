from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from uuid import (
    NAMESPACE_URL,
    UUID,
    uuid4,
    uuid5,
)

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


# Stable namespaces for TraceGraph IDs.
#
# These values are deterministic because
# they are themselves derived from fixed
# TraceGraph namespace names.
DOCUMENT_ID_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "tracegraph-ai/document",
)

CHUNK_ID_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "tracegraph-ai/chunk",
)


def create_stable_document_id(
    content: bytes,
    file_type: FileType,
) -> UUID:
    """
    Generate a deterministic document UUID
    from the original file bytes.

    The same file content and file type will
    always produce the same document ID.
    """

    if not content:
        raise ValueError(
            "Cannot create document ID "
            "from empty content"
        )

    content_hash = sha256(
        content
    ).hexdigest()

    identity = (
        f"{file_type.value}:"
        f"{content_hash}"
    )

    return uuid5(
        DOCUMENT_ID_NAMESPACE,
        identity,
    )


def create_stable_chunk_id(
    document_id: UUID,
    chunk_index: int,
    text: str,
    page_number: int | None = None,
) -> UUID:
    """
    Generate a deterministic chunk UUID.

    The ID depends on:
    - parent document
    - chunk position
    - page
    - chunk content

    Therefore the same document processed
    with the same chunking result produces
    the same chunk IDs.
    """

    if chunk_index < 0:
        raise ValueError(
            "chunk_index cannot be negative"
        )

    if not text.strip():
        raise ValueError(
            "Cannot create chunk ID "
            "from empty text"
        )

    text_hash = sha256(
        text.encode("utf-8")
    ).hexdigest()

    page_value = (
        page_number
        if page_number is not None
        else 0
    )

    identity = (
        f"{document_id}:"
        f"{chunk_index}:"
        f"{page_value}:"
        f"{text_hash}"
    )

    return uuid5(
        CHUNK_ID_NAMESPACE,
        identity,
    )


class DocumentMetadata(BaseModel):
    title: str | None = None
    author: str | None = None
    page_count: int | None = None
    language: str | None = None


class Document(BaseModel):
    # Keep uuid4 as a fallback so existing
    # application/tests can still construct
    # temporary Documents without explicitly
    # supplying an ID.
    #
    # Production loaders will explicitly use
    # create_stable_document_id().
    id: UUID = Field(
        default_factory=uuid4
    )

    filename: str
    file_type: FileType

    status: DocumentStatus = (
        DocumentStatus.UPLOADED
    )

    storage_uri: str | None = None

    metadata: DocumentMetadata = Field(
        default_factory=DocumentMetadata
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class ParsedPage(BaseModel):
    page_number: int = Field(
        ge=1
    )

    text: str


class ChunkMetadata(BaseModel):
    page_number: int | None = None
    section: str | None = None
    heading: str | None = None


class DocumentChunk(BaseModel):
    # uuid4 remains available for callers
    # creating standalone chunks manually.
    #
    # TextChunker will explicitly supply
    # deterministic IDs.
    id: UUID = Field(
        default_factory=uuid4
    )

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
        default_factory=lambda: datetime.now(
            timezone.utc
        )
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