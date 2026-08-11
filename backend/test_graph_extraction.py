from pathlib import Path

from app.graph.extractor import (
    GraphExtractor,
)
from app.ingestion.chunker import (
    TextChunker,
)
from app.ingestion.loaders.pdf_loader import (
    PDFLoader,
)


def main():
    pdf_path = Path(
        "../data/sample.pdf"
    )

    print("Loading PDF...")

    loader = PDFLoader()

    document, pages = loader.load(
        pdf_path
    )

    chunker = TextChunker(
        max_chars=1000
    )

    chunks = chunker.chunk_pages(
        document=document,
        pages=pages,
    )

    print(
        f"Created {len(chunks)} chunks."
    )

    # These chunks contain useful technical
    # entities and relationships in our sample.
    selected_indexes = {
        11,
        15,
        18,
        22,
        25,
    }

    selected_chunks = [
        chunk
        for chunk in chunks
        if chunk.chunk_index
        in selected_indexes
    ]

    print(
        "Testing graph extraction on "
        f"{len(selected_chunks)} chunks."
    )

    extractor = GraphExtractor()

    results = extractor.extract_chunks(
        document=document,
        chunks=selected_chunks,
        batch_size=5,
    )

    for chunk_index in sorted(results):
        graph = results[chunk_index]

        print("\n")
        print("=" * 80)
        print(
            f"CHUNK {chunk_index}"
        )
        print("=" * 80)

        print("\nENTITIES")

        for entity in graph.entities:
            print(
                f"- {entity.name} "
                f"[{entity.entity_type.value}]"
            )

            if entity.aliases:
                print(
                    f"  aliases: "
                    f"{entity.aliases}"
                )

        print("\nRELATIONSHIPS")

        if not graph.relationships:
            print(
                "- No supported relationships"
            )

        for relationship in (
            graph.relationships
        ):
            print(
                f"- "
                f"{relationship.source_name}"
                f" "
                f"{relationship.relationship_type.value}"
                f" "
                f"{relationship.target_name}"
            )

            print(
                f"  confidence: "
                f"{relationship.confidence:.2f}"
            )

            print(
                f"  evidence: "
                f"{relationship.evidence_text}"
            )


if __name__ == "__main__":
    main()