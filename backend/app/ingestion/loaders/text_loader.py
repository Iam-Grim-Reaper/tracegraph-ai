from pathlib import Path

from app.models.document import Document, FileType


class TextLoader:
    def load(self, file_path: str | Path) -> tuple[Document, str]:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")

        if path.suffix.lower() != ".txt":
            raise ValueError(
                f"Unsupported file type: {path.suffix}. Expected .txt"
            )

        text = path.read_text(
            encoding="utf-8"
        ).strip()

        if not text:
            raise ValueError(
                f"File is empty: {path.name}"
            )

        document = Document(
            filename=path.name,
            file_type=FileType.TXT,
        )

        return document, text