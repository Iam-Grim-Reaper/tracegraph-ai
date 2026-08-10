from uuid import UUID

from app.models.document import (
    Document,
    DocumentChunk,
    DocumentStatus,
    FileType,
)


def test_document_creation():
    document = Document(
        filename="example.txt",
        file_type=FileType.TXT,
    )

    assert isinstance(document.id, UUID)
    assert document.filename == "example.txt"
    assert document.file_type == FileType.TXT
    assert document.status == DocumentStatus.UPLOADED

    assert document.storage_uri is None

    assert document.metadata.title is None
    assert document.metadata.author is None
    assert document.metadata.page_count is None
    assert document.metadata.language is None


def test_document_chunk_creation():
    document = Document(
        filename="example.txt",
        file_type=FileType.TXT,
    )

    chunk = DocumentChunk(
        document_id=document.id,
        chunk_index=0,
        text="Example chunk text.",
    )

    assert isinstance(chunk.id, UUID)

    assert chunk.document_id == document.id
    assert chunk.chunk_index == 0

    assert chunk.text == "Example chunk text."
    assert chunk.contextual_text is None

    assert chunk.previous_chunk_id is None
    assert chunk.next_chunk_id is None