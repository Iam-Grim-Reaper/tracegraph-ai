import re
from pathlib import Path

from app.models.document import (
    Document,
    DocumentMetadata,
    FileType,
    create_stable_document_id,
)


class MarkdownLoader:
    def load(
        self,
        file_path: str | Path,
    ) -> tuple[Document, str]:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Path is not a file: {path}"
            )

        if path.suffix.lower() not in {
            ".md",
            ".markdown",
        }:
            raise ValueError(
                f"Unsupported file type: "
                f"{path.suffix}. "
                "Expected .md or .markdown"
            )

        # Read original bytes so that the
        # document identity is based on the
        # actual source file content.
        file_bytes = path.read_bytes()

        if not file_bytes:
            raise ValueError(
                f"File is empty: {path.name}"
            )

        try:
            text = file_bytes.decode(
                "utf-8"
            ).strip()

        except UnicodeDecodeError as exc:
            raise ValueError(
                f"Unable to decode Markdown "
                f"file as UTF-8: {path.name}"
            ) from exc

        if not text:
            raise ValueError(
                f"File contains no usable "
                f"text: {path.name}"
            )

        title = self._extract_title(
            text
        )

        # Same Markdown bytes + same file type
        # always produce the same document ID.
        document_id = (
            create_stable_document_id(
                content=file_bytes,
                file_type=FileType.MARKDOWN,
            )
        )

        document = Document(
            id=document_id,
            filename=path.name,
            file_type=FileType.MARKDOWN,
            metadata=DocumentMetadata(
                title=title,
            ),
        )

        return document, text

    @staticmethod
    def _extract_title(
        text: str,
    ) -> str | None:
        match = re.search(
            r"^\s*#\s+(.+?)\s*$",
            text,
            flags=re.MULTILINE,
        )

        if match:
            return match.group(1).strip()

        return None