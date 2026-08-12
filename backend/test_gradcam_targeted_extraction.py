from pathlib import Path

from app.graph.extractor import (
    GraphExtractor,
)
from app.graph.ontology import (
    RESEARCH_ONTOLOGY,
)
from app.ingestion.service import (
    IngestionService,
)


SAMPLE_PATH = Path(
    "../data/sample.pdf"
)

TARGET_CHUNK_INDEX = 29


def main():
    print("=" * 70)
    print(
        "TRACEGRAPH TARGETED "
        "GRAD-CAM EXTRACTION TEST"
    )
    print("=" * 70)

    ingestion = (
        IngestionService(
            max_chars=1000
        )
        .ingest(
            SAMPLE_PATH
        )
    )

    document = (
        ingestion.document
    )

    target_chunks = [
        chunk
        for chunk in ingestion.chunks
        if (
            chunk.chunk_index
            == TARGET_CHUNK_INDEX
        )
    ]

    if len(target_chunks) != 1:
        raise RuntimeError(
            "Could not locate exactly one "
            "chunk with index 29."
        )

    chunk = (
        target_chunks[0]
    )

    print(
        "Chunk ID:",
        chunk.id,
    )

    print(
        "Page:",
        chunk.metadata.page_number,
    )

    print(
        "\nSource text:"
    )

    print(
        chunk.text
    )

    print(
        "\nExtracting with research "
        "ontology 2.0..."
    )

    extractor = (
        GraphExtractor(
            ontology_profile=(
                RESEARCH_ONTOLOGY
            )
        )
    )

    results = (
        extractor.extract_chunks(
            document=document,
            chunks=[
                chunk
            ],
            batch_size=1,
        )
    )

    graph = (
        results[
            TARGET_CHUNK_INDEX
        ]
    )

    print(
        "\n----- ENTITIES -----"
    )

    for entity in graph.entities:
        print(
            entity.name,
            "|",
            entity.entity_type.value,
            "| aliases:",
            entity.aliases,
        )

    print(
        "\n----- RELATIONSHIPS -----"
    )

    for relationship in (
        graph.relationships
    ):
        print(
            relationship.source_name,
            "->",
            relationship
            .relationship_type
            .value,
            "->",
            relationship.target_name,
        )

        print(
            "Evidence:",
            relationship.evidence_text,
        )

    has_selvaraju = any(
        (
            "selvaraju"
            in entity.name.casefold()
            and
            entity.entity_type.value
            == "Person"
        )
        for entity
        in graph.entities
    )

    has_developed_by = any(
        (
            relationship
            .relationship_type
            .value
            == "DEVELOPED_BY"
            and
            "grad"
            in relationship
            .source_name
            .casefold()
            and
            "cam"
            in relationship
            .source_name
            .casefold()
            and
            "selvaraju"
            in relationship
            .target_name
            .casefold()
        )
        for relationship
        in graph.relationships
    )

    print(
        "\nSelvaraju entity:",
        has_selvaraju,
    )

    print(
        "Grad-CAM DEVELOPED_BY:",
        has_developed_by,
    )

    if not has_selvaraju:
        raise RuntimeError(
            "Research extractor still failed "
            "to extract Selvaraju."
        )

    if not has_developed_by:
        raise RuntimeError(
            "Research extractor still failed "
            "to extract Grad-CAM "
            "DEVELOPED_BY Selvaraju."
        )

    print(
        "\n" + "=" * 70
    )

    print(
        "TARGETED GRAD-CAM "
        "EXTRACTION VALID"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()