from pathlib import Path

from app.ingestion.chunker import (
    TextChunker,
)
from app.ingestion.loaders.pdf_loader import (
    PDFLoader,
)


def main():
    path = Path(
        "../data/sample.pdf"
    )

    loader = PDFLoader()

    first_document, first_pages = (
        loader.load(path)
    )

    second_document, second_pages = (
        loader.load(path)
    )

    print("=" * 70)
    print("DOCUMENT ID CHECK")
    print("=" * 70)

    print(
        "First document ID: ",
        first_document.id,
    )

    print(
        "Second document ID:",
        second_document.id,
    )

    print(
        "Document IDs match:",
        first_document.id
        == second_document.id,
    )

    chunker = TextChunker(
        max_chars=1000
    )

    first_chunks = (
        chunker.chunk_pages(
            document=first_document,
            pages=first_pages,
        )
    )

    second_chunks = (
        chunker.chunk_pages(
            document=second_document,
            pages=second_pages,
        )
    )

    print("\n" + "=" * 70)
    print("CHUNK ID CHECK")
    print("=" * 70)

    print(
        "First run chunks:",
        len(first_chunks),
    )

    print(
        "Second run chunks:",
        len(second_chunks),
    )

    first_ids = [
        chunk.id
        for chunk in first_chunks
    ]

    second_ids = [
        chunk.id
        for chunk in second_chunks
    ]

    print(
        "All chunk IDs match:",
        first_ids == second_ids,
    )

    print(
        "\nFirst 5 chunk IDs:"
    )

    for chunk in first_chunks[:5]:
        print(
            f"Chunk {chunk.chunk_index}: "
            f"{chunk.id}"
        )


if __name__ == "__main__":
    main()