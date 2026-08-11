from pathlib import Path

from app.services.document_indexing_service import (
    DocumentIndexingService,
)


def main():
    pdf_path = Path(
        "../data/sample.pdf"
    )

    service = (
        DocumentIndexingService()
    )

    result = service.index_file(
        pdf_path
    )

    print("\n")
    print("=" * 70)
    print("INDEXING RESULT")
    print("=" * 70)

    print(
        "Status:",
        result.status,
    )

    print(
        "Document ID:",
        result.document_id,
    )

    print(
        "Filename:",
        result.filename,
    )

    print(
        "File type:",
        result.file_type,
    )

    print(
        "Chunks:",
        result.chunk_count,
    )

    print(
        "Qdrant indexed:",
        result.qdrant_indexed_chunks,
    )

    print(
        "Graph entities:",
        result.graph_entity_count,
    )

    print(
        "Graph relationships:",
        result.graph_relationship_count,
    )

    print(
        "Graph cache hits:",
        result.graph_cached_chunks,
    )

    print(
        "Graph newly extracted:",
        result.graph_extracted_chunks,
    )


if __name__ == "__main__":
    main()