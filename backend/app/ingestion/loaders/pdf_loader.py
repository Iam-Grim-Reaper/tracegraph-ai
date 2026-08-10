from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.models.document import (
    Document,
    DocumentMetadata,
    FileType,
    ParsedPage,
)


class PDFLoader:
    def load(
        self,
        file_path: str | Path,
    ) -> tuple[Document, list[ParsedPage]]:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Path is not a file: {path}"
            )

        if path.suffix.lower() != ".pdf":
            raise ValueError(
                f"Unsupported file type: {path.suffix}. "
                "Expected .pdf"
            )

        try:
            reader = PdfReader(path)
        except PdfReadError as exc:
            raise ValueError(
                f"Unable to read PDF: {path.name}"
            ) from exc

        if reader.is_encrypted:
            raise ValueError(
                "Encrypted PDFs are not supported yet"
            )

        pdf_metadata = reader.metadata

        title = (
            pdf_metadata.title
            if pdf_metadata is not None
            else None
        )

        author = (
            pdf_metadata.author
            if pdf_metadata is not None
            else None
        )

        pages: list[ParsedPage] = []

        for page_number, page in enumerate(
            reader.pages,
            start=1,
        ):
            extracted_text = page.extract_text() or ""

            cleaned_text = extracted_text.strip()

            if not cleaned_text:
                continue

            pages.append(
                ParsedPage(
                    page_number=page_number,
                    text=cleaned_text,
                )
            )

        if not pages:
            raise ValueError(
                "PDF contains no extractable text"
            )

        document = Document(
            filename=path.name,
            file_type=FileType.PDF,
            metadata=DocumentMetadata(
                title=title,
                author=author,
                page_count=len(reader.pages),
            ),
        )

        return document, pages