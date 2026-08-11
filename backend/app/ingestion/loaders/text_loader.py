from pathlib import Path

from app.models.document import (
    Document,
    FileType,
    create_stable_document_id,
)


class TextLoader:
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

        if path.suffix.lower() != ".txt":
            raise ValueError(
                f"Unsupported file type: "
                f"{path.suffix}. Expected .txt"
            )

        # Read the original bytes first so the
        # document ID is based on the actual
        # source file content.
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
                f"Unable to decode text file "
                f"as UTF-8: {path.name}"
            ) from exc

        if not text:
            raise ValueError(
                f"File contains no usable "
                f"text: {path.name}"
            )

        # Same file bytes + same file type
        # always produce the same Document ID.
        document_id = (
            create_stable_document_id(
                content=file_bytes,
                file_type=FileType.TXT,
            )
        )

        document = Document(
            id=document_id,
            filename=path.name,
            file_type=FileType.TXT,
        )

        return document, text