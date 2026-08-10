from pathlib import Path

from app.ingestion.chunker import TextChunker
from app.ingestion.loaders.markdown_loader import MarkdownLoader
from app.ingestion.loaders.pdf_loader import PDFLoader
from app.ingestion.loaders.text_loader import TextLoader
from app.models.document import IngestionResult


class IngestionService:
    def __init__(self, max_chars: int = 1000):
        self.chunker = TextChunker(
            max_chars=max_chars
        )

        self.text_loader = TextLoader()
        self.markdown_loader = MarkdownLoader()
        self.pdf_loader = PDFLoader()

    def ingest(
        self,
        file_path: str | Path,
    ) -> IngestionResult:
        path = Path(file_path)

        suffix = path.suffix.lower()

        if suffix == ".txt":
            document, text = (
                self.text_loader.load(path)
            )

            chunks = self.chunker.chunk(
                document=document,
                text=text,
            )

        elif suffix in {".md", ".markdown"}:
            document, text = (
                self.markdown_loader.load(path)
            )

            chunks = self.chunker.chunk(
                document=document,
                text=text,
            )

        elif suffix == ".pdf":
            document, pages = (
                self.pdf_loader.load(path)
            )

            chunks = self.chunker.chunk_pages(
                document=document,
                pages=pages,
            )

        else:
            raise ValueError(
                f"Unsupported file type: "
                f"{suffix or 'no extension'}"
            )

        return IngestionResult(
            document=document,
            chunks=chunks,
        )