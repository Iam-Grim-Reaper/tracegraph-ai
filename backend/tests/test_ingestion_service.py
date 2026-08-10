import pytest

from app.ingestion.service import IngestionService
from app.models.document import (
    Document,
    FileType,
    ParsedPage,
)


def test_ingests_txt_file(tmp_path):
    file_path = tmp_path / "example.txt"

    file_path.write_text(
        "TraceGraph combines retrieval, "
        "knowledge graphs, and verification.",
        encoding="utf-8",
    )

    service = IngestionService(
        max_chars=100
    )

    result = service.ingest(file_path)

    assert result.document.filename == "example.txt"
    assert result.document.file_type == FileType.TXT

    assert len(result.chunks) >= 1

    for chunk in result.chunks:
        assert (
            chunk.document_id
            == result.document.id
        )


def test_ingests_markdown_file(tmp_path):
    file_path = tmp_path / "example.md"

    file_path.write_text(
        "# TraceGraph AI\n\n"
        "TraceGraph is an agentic GraphRAG system.",
        encoding="utf-8",
    )

    service = IngestionService(
        max_chars=100
    )

    result = service.ingest(file_path)

    assert result.document.file_type == FileType.MARKDOWN

    assert (
        result.document.metadata.title
        == "TraceGraph AI"
    )

    assert len(result.chunks) >= 1


def test_pdf_ingestion_preserves_page_number(
    tmp_path,
    monkeypatch,
):
    file_path = tmp_path / "example.pdf"

    file_path.write_bytes(
        b"placeholder"
    )

    service = IngestionService(
        max_chars=100
    )

    def fake_pdf_load(_):
        document = Document(
            filename="example.pdf",
            file_type=FileType.PDF,
        )

        pages = [
            ParsedPage(
                page_number=1,
                text=(
                    "Page one contains information "
                    "about contextual retrieval."
                ),
            ),
            ParsedPage(
                page_number=2,
                text=(
                    "Page two contains information "
                    "about knowledge graphs."
                ),
            ),
        ]

        return document, pages

    monkeypatch.setattr(
        service.pdf_loader,
        "load",
        fake_pdf_load,
    )

    result = service.ingest(
        file_path
    )

    assert result.document.file_type == FileType.PDF

    assert len(result.chunks) == 2

    assert (
        result.chunks[0]
        .metadata.page_number
        == 1
    )

    assert (
        result.chunks[1]
        .metadata.page_number
        == 2
    )


def test_rejects_unsupported_file_type(
    tmp_path,
):
    file_path = tmp_path / "example.csv"

    file_path.write_text(
        "a,b,c",
        encoding="utf-8",
    )

    service = IngestionService()

    with pytest.raises(
        ValueError,
        match="Unsupported file type",
    ):
        service.ingest(file_path)