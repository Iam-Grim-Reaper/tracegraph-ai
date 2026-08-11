from app.ingestion.chunker import TextChunker
from app.ingestion.loaders.pdf_loader import PDFLoader
from app.retrieval.contextual_indexer import (
    ContextualVectorIndexer,
)


def main():
    print("Loading PDF...")

    document, pages = PDFLoader().load(
        "../data/sample.pdf"
    )

    print(
        f"Loaded {len(pages)} pages "
        f"from {document.filename}"
    )

    chunker = TextChunker(
        max_chars=1000
    )

    chunks = chunker.chunk_pages(
        document=document,
        pages=pages,
    )

    print(
        f"Created {len(chunks)} chunks"
    )

    document_text = "\n\n".join(
        page.text
        for page in pages
    )

    print(
        "\nGenerating contextual representations..."
    )

    indexer = ContextualVectorIndexer()

    indexed = indexer.index(
        document=document,
        chunks=chunks,
        document_text=document_text,
    )

    print(
        f"\nContextual chunks indexed: {indexed}"
    )


if __name__ == "__main__":
    main()