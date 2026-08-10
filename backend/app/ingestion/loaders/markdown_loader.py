import re
from pathlib import Path

from app.models.document import (
    Document,
    DocumentMetadata,
    FileType,
)


class MarkdownLoader:
    def load(self, file_path: str | Path) -> tuple[Document, str]:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")

        if path.suffix.lower() not in {".md", ".markdown"}:
            raise ValueError(
                f"Unsupported file type: {path.suffix}. "
                "Expected .md or .markdown"
            )

        text = path.read_text(
            encoding="utf-8"
        ).strip()

        if not text:
            raise ValueError(
                f"File is empty: {path.name}"
            )

        title = self._extract_title(text)

        document = Document(
            filename=path.name,
            file_type=FileType.MARKDOWN,
            metadata=DocumentMetadata(
                title=title,
            ),
        )

        return document, text

    @staticmethod
    def _extract_title(text: str) -> str | None:
        match = re.search(
            r"^\s*#\s+(.+?)\s*$",
            text,
            flags=re.MULTILINE,
        )

        if match:
            return match.group(1).strip()

        return None