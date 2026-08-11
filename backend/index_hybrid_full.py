from pathlib import Path

from app.ingestion.chunker import (
    TextChunker,
)
from app.ingestion.loaders.pdf_loader import (
    PDFLoader,
)
from app.retrieval.hybrid_indexer import (
    HybridIndexer,
)


def main():
    pdf_path = Path(
        "../data/sample.pdf"
    )

    print("=" * 70)
    print(
        "TRACEGRAPH FULL HYBRID INDEX"
    )
    print("=" * 70)

    print("\nLoading PDF...")

    loader = PDFLoader()

    document, pages = loader.load(
        pdf_path
    )

    print(
        f"Document ID: "
        f"{document.id}"
    )

    document_text = "\n\n".join(
        page.text
        for page in pages
        if page.text.strip()
    )

    if not document_text.strip():
        raise RuntimeError(
            "PDF contains no usable text"
        )

    chunker = TextChunker(
        max_chars=1000
    )

    chunks = chunker.chunk_pages(
        document=document,
        pages=pages,
    )

    print(
        f"Chunks: {len(chunks)}"
    )

    print(
        "\nFirst 5 stable chunk IDs:"
    )

    for chunk in chunks[:5]:
        print(
            f"  {chunk.chunk_index}: "
            f"{chunk.id}"
        )

    indexer = HybridIndexer()

    print(
        "\nRebuilding hybrid "
        "collection..."
    )

    print(
        "NOTE: This removes only the "
        "current Qdrant hybrid collection."
    )

    indexed_count = (
        indexer.index(
            document=document,
            chunks=chunks,
            document_text=(
                document_text
            ),

            # We need True exactly once
            # because the existing hybrid
            # collection contains points
            # created before stable IDs.
            reset_collection=True,
        )
    )

    point_count = (
        indexer.hybrid_store
        .count_points()
    )

    print("\n" + "=" * 70)

    print(
        "HYBRID INDEX COMPLETE"
    )

    print("=" * 70)

    print(
        f"Indexed chunks: "
        f"{indexed_count}"
    )

    print(
        f"Qdrant points: "
        f"{point_count}"
    )

    if point_count != indexed_count:
        raise RuntimeError(
            "Unexpected Qdrant point "
            "count after indexing"
        )


if __name__ == "__main__":
    main()