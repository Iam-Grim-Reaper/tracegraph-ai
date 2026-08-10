import pytest

from app.ingestion.loaders.markdown_loader import MarkdownLoader
from app.models.document import DocumentStatus, FileType


def test_markdown_loader_loads_valid_file(tmp_path):
    file_path = tmp_path / "example.md"

    file_path.write_text(
        "# TraceGraph AI\n\n"
        "TraceGraph combines retrieval and knowledge graphs.",
        encoding="utf-8",
    )

    loader = MarkdownLoader()

    document, text = loader.load(file_path)

    assert document.filename == "example.md"
    assert document.file_type == FileType.MARKDOWN
    assert document.status == DocumentStatus.UPLOADED
    assert document.metadata.title == "TraceGraph AI"

    assert "# TraceGraph AI" in text


def test_markdown_loader_supports_markdown_extension(tmp_path):
    file_path = tmp_path / "example.markdown"

    file_path.write_text(
        "# GraphRAG\n\nExample content.",
        encoding="utf-8",
    )

    loader = MarkdownLoader()

    document, _ = loader.load(file_path)

    assert document.file_type == FileType.MARKDOWN
    assert document.metadata.title == "GraphRAG"


def test_markdown_loader_without_title(tmp_path):
    file_path = tmp_path / "example.md"

    file_path.write_text(
        "This document has no heading.",
        encoding="utf-8",
    )

    loader = MarkdownLoader()

    document, _ = loader.load(file_path)

    assert document.metadata.title is None


def test_markdown_loader_rejects_missing_file(tmp_path):
    loader = MarkdownLoader()

    with pytest.raises(FileNotFoundError):
        loader.load(tmp_path / "missing.md")


def test_markdown_loader_rejects_wrong_type(tmp_path):
    file_path = tmp_path / "example.txt"

    file_path.write_text(
        "Not Markdown",
        encoding="utf-8",
    )

    loader = MarkdownLoader()

    with pytest.raises(
        ValueError,
        match="Unsupported file type",
    ):
        loader.load(file_path)


def test_markdown_loader_rejects_empty_file(tmp_path):
    file_path = tmp_path / "empty.md"

    file_path.write_text(
        "",
        encoding="utf-8",
    )

    loader = MarkdownLoader()

    with pytest.raises(
        ValueError,
        match="File is empty",
    ):
        loader.load(file_path)