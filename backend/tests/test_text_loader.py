import pytest

from app.ingestion.loaders.text_loader import TextLoader
from app.models.document import DocumentStatus, FileType


def test_text_loader_loads_valid_file(tmp_path):
    file_path = tmp_path / "example.txt"

    file_path.write_text(
        "TraceGraph is an agentic GraphRAG platform.",
        encoding="utf-8",
    )

    loader = TextLoader()

    document, text = loader.load(file_path)

    assert document.filename == "example.txt"
    assert document.file_type == FileType.TXT
    assert document.status == DocumentStatus.UPLOADED

    assert text == "TraceGraph is an agentic GraphRAG platform."


def test_text_loader_rejects_missing_file(tmp_path):
    missing_file = tmp_path / "missing.txt"

    loader = TextLoader()

    with pytest.raises(FileNotFoundError):
        loader.load(missing_file)


def test_text_loader_rejects_wrong_file_type(tmp_path):
    file_path = tmp_path / "example.pdf"

    file_path.write_text(
        "This should not be accepted.",
        encoding="utf-8",
    )

    loader = TextLoader()

    with pytest.raises(ValueError, match="Unsupported file type"):
        loader.load(file_path)


def test_text_loader_rejects_empty_file(tmp_path):
    file_path = tmp_path / "empty.txt"

    file_path.write_text(
        "",
        encoding="utf-8",
    )

    loader = TextLoader()

    with pytest.raises(ValueError, match="File is empty"):
        loader.load(file_path)