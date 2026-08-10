import pytest

from app.ingestion.chunker import TextChunker
from app.models.document import Document, FileType


def create_document() -> Document:
    return Document(
        filename="example.txt",
        file_type=FileType.TXT,
    )


def test_chunker_creates_chunks():
    document = create_document()

    text = (
        "Python is commonly used for AI development.\n\n"
        "FastAPI is used for building APIs.\n\n"
        "Knowledge graphs represent entities and relationships."
    )

    chunker = TextChunker(max_chars=100)

    chunks = chunker.chunk(
        document=document,
        text=text,
    )

    assert len(chunks) >= 2

    for chunk in chunks:
        assert chunk.document_id == document.id
        assert len(chunk.text) <= 100


def test_chunk_indices_are_sequential():
    document = create_document()

    text = (
        "First paragraph contains some information.\n\n"
        "Second paragraph contains some information.\n\n"
        "Third paragraph contains some information."
    )

    chunker = TextChunker(max_chars=100)

    chunks = chunker.chunk(document, text)

    indices = [
        chunk.chunk_index
        for chunk in chunks
    ]

    assert indices == list(range(len(chunks)))


def test_chunk_relationships_are_correct():
    document = create_document()

    text = (
        "Paragraph one contains useful information about Python.\n\n"
        "Paragraph two contains useful information about retrieval.\n\n"
        "Paragraph three contains useful information about graphs."
    )

    chunker = TextChunker(max_chars=100)

    chunks = chunker.chunk(document, text)

    assert len(chunks) >= 2

    assert chunks[0].previous_chunk_id is None
    assert chunks[-1].next_chunk_id is None

    for index in range(len(chunks) - 1):
        current_chunk = chunks[index]
        next_chunk = chunks[index + 1]

        assert current_chunk.next_chunk_id == next_chunk.id
        assert next_chunk.previous_chunk_id == current_chunk.id


def test_chunker_rejects_empty_text():
    document = create_document()

    chunker = TextChunker()

    with pytest.raises(
        ValueError,
        match="Cannot chunk empty text",
    ):
        chunker.chunk(document, "")


def test_chunker_rejects_invalid_max_chars():
    with pytest.raises(
        ValueError,
        match="max_chars must be at least 100",
    ):
        TextChunker(max_chars=50)


def test_long_paragraph_is_split():
    document = create_document()

    text = " ".join(
        ["TraceGraph"] * 100
    )

    chunker = TextChunker(max_chars=100)

    chunks = chunker.chunk(document, text)

    assert len(chunks) > 1

    for chunk in chunks:
        assert len(chunk.text) <= 100