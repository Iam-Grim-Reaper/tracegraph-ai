from app.ingestion.chunker import (
    TextChunker,
)
from app.models.document import (
    Document,
    FileType,
    create_stable_document_id,
)


def test_same_file_gets_same_document_id():
    content = (
        b"TraceGraph deterministic "
        b"document content."
    )

    first = create_stable_document_id(
        content=content,
        file_type=FileType.PDF,
    )

    second = create_stable_document_id(
        content=content,
        file_type=FileType.PDF,
    )

    assert first == second


def test_different_content_gets_different_document_id():
    first = create_stable_document_id(
        content=b"Document A",
        file_type=FileType.PDF,
    )

    second = create_stable_document_id(
        content=b"Document B",
        file_type=FileType.PDF,
    )

    assert first != second


def test_file_type_affects_document_id():
    content = b"Same bytes"

    pdf_id = create_stable_document_id(
        content=content,
        file_type=FileType.PDF,
    )

    text_id = create_stable_document_id(
        content=content,
        file_type=FileType.TXT,
    )

    assert pdf_id != text_id


def test_repeated_chunking_produces_same_ids():
    content = (
        b"TraceGraph stable source file."
    )

    document_id = (
        create_stable_document_id(
            content=content,
            file_type=FileType.TXT,
        )
    )

    first_document = Document(
        id=document_id,
        filename="sample.txt",
        file_type=FileType.TXT,
    )

    second_document = Document(
        id=document_id,
        filename="sample.txt",
        file_type=FileType.TXT,
    )

    text = (
        "TraceGraph performs graph retrieval. "
        * 40
    )

    chunker = TextChunker(
        max_chars=200
    )

    first_chunks = chunker.chunk(
        document=first_document,
        text=text,
    )

    second_chunks = chunker.chunk(
        document=second_document,
        text=text,
    )

    assert len(first_chunks) == len(
        second_chunks
    )

    assert [
        chunk.id
        for chunk in first_chunks
    ] == [
        chunk.id
        for chunk in second_chunks
    ]


def test_previous_and_next_ids_are_stable():
    document_id = (
        create_stable_document_id(
            content=b"linked chunks",
            file_type=FileType.TXT,
        )
    )

    document = Document(
        id=document_id,
        filename="linked.txt",
        file_type=FileType.TXT,
    )

    chunker = TextChunker(
        max_chars=100
    )

    text = (
        "first paragraph " * 20
        + "\n\n"
        + "second paragraph " * 20
        + "\n\n"
        + "third paragraph " * 20
    )

    first_run = chunker.chunk(
        document=document,
        text=text,
    )

    second_run = chunker.chunk(
        document=document,
        text=text,
    )

    assert len(first_run) > 1

    for first, second in zip(
        first_run,
        second_run,
        strict=True,
    ):
        assert (
            first.id
            == second.id
        )

        assert (
            first.previous_chunk_id
            == second.previous_chunk_id
        )

        assert (
            first.next_chunk_id
            == second.next_chunk_id
        )