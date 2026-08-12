from pathlib import Path

from app.graph.extraction_cache import (
    GraphExtractionCache,
)
from app.graph.ontology import (
    RESEARCH_ONTOLOGY,
)
from app.graph.postprocessor import (
    GraphPostProcessor,
)
from app.ingestion.service import (
    IngestionService,
)


SAMPLE_PATH = Path(
    "../data/sample.pdf"
)


SEARCH_TERMS = [
    "grad-cam",
    "grad cam",
    "selvaraju",
]


def contains_target_text(
    text: str,
) -> bool:
    normalized = (
        text.casefold()
    )

    return any(
        term in normalized
        for term in SEARCH_TERMS
    )


def main():
    print("=" * 70)

    print(
        "TRACEGRAPH GRAD-CAM "
        "ONTOLOGY-V2 DIAGNOSTIC"
    )

    print("=" * 70)

    if not SAMPLE_PATH.exists():
        raise FileNotFoundError(
            f"Sample PDF not found: "
            f"{SAMPLE_PATH.resolve()}"
        )

    # =================================================
    # 1. Recreate the stable chunks.
    #
    # No embedding.
    # No Qdrant.
    # No Neo4j write.
    # No Gemini call.
    # =================================================

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

    chunks = (
        ingestion.chunks
    )

    print(
        "Document:",
        document.id,
    )

    print(
        "Chunks:",
        len(chunks),
    )

    # =================================================
    # 2. Open the Ontology-v2 research cache.
    # =================================================

    cache = (
        GraphExtractionCache(
            ontology_profile=(
                RESEARCH_ONTOLOGY
            )
        )
    )

    processor = (
        GraphPostProcessor(
            ontology_profile=(
                RESEARCH_ONTOLOGY
            )
        )
    )

    matching_chunks = [
        chunk
        for chunk in chunks
        if contains_target_text(
            chunk.text
        )
    ]

    print(
        "\nChunks containing "
        "Grad-CAM / Selvaraju:",
        len(matching_chunks),
    )

    if not matching_chunks:
        raise RuntimeError(
            "No source chunks contain "
            "Grad-CAM or Selvaraju."
        )

    # =================================================
    # 3. Inspect raw cached extraction and
    #    deterministic post-processing.
    # =================================================

    for chunk in matching_chunks:
        print(
            "\n" + "=" * 70
        )

        print(
            "CHUNK INDEX:",
            chunk.chunk_index,
        )

        print(
            "CHUNK ID:",
            chunk.id,
        )

        print(
            "PAGE:",
            chunk.metadata.page_number,
        )

        print(
            "\n----- SOURCE TEXT -----"
        )

        print(
            chunk.text
        )

        raw_graph = (
            cache.get(
                chunk
            )
        )

        if raw_graph is None:
            print(
                "\nCACHE RESULT: MISS"
            )

            continue

        print(
            "\nCACHE RESULT: HIT"
        )

        # -----------------------------------------
        # Raw entities
        # -----------------------------------------

        print(
            "\n----- RAW ENTITIES -----"
        )

        if not raw_graph.entities:
            print(
                "No raw entities."
            )

        for entity in (
            raw_graph.entities
        ):
            print(
                "ENTITY:",
                entity.name,
                "| TYPE:",
                entity.entity_type.value,
                "| ALIASES:",
                entity.aliases,
            )

        # -----------------------------------------
        # Raw relationships
        # -----------------------------------------

        print(
            "\n----- RAW RELATIONSHIPS -----"
        )

        if not raw_graph.relationships:
            print(
                "No raw relationships."
            )

        for relationship in (
            raw_graph.relationships
        ):
            print(
                "REL:",
                relationship.source_name,
                f"({relationship.source_type.value})",
                "->",
                relationship
                .relationship_type
                .value,
                "->",
                relationship.target_name,
                f"({relationship.target_type.value})",
            )

            print(
                "CONFIDENCE:",
                relationship.confidence,
            )

            print(
                "EVIDENCE:",
                relationship.evidence_text,
            )

        # -----------------------------------------
        # Post-processing
        # -----------------------------------------

        print(
            "\n----- POST-PROCESSED -----"
        )

        processed = (
            processor.process(
                document=document,
                chunk=chunk,
                extracted_graph=(
                    raw_graph
                ),
            )
        )

        print(
            "Accepted entities:",
            len(
                processed.entities
            ),
        )

        print(
            "Accepted relationships:",
            len(
                processed.relationships
            ),
        )

        print(
            "Rejected relationships:",
            len(
                processed
                .rejected_relationships
            ),
        )

        print(
            "\n----- ACCEPTED RELATIONSHIPS -----"
        )

        if not processed.relationships:
            print(
                "No accepted relationships."
            )

        for relationship in (
            processed.relationships
        ):
            print(
                "ACCEPTED:",
                relationship
                .source_entity_id,
                "->",
                relationship
                .relationship_type
                .value,
                "->",
                relationship
                .target_entity_id,
            )

            print(
                "EVIDENCE:",
                relationship
                .evidence_text,
            )

        print(
            "\n----- REJECTED RELATIONSHIPS -----"
        )

        if not (
            processed
            .rejected_relationships
        ):
            print(
                "No rejected relationships."
            )

        for rejected in (
            processed
            .rejected_relationships
        ):
            # Printing repr deliberately because
            # it lets us inspect the exact rejected
            # model without assuming its internal
            # field structure.
            print(
                repr(
                    rejected
                )
            )

    print(
        "\n" + "=" * 70
    )

    print(
        "GRAD-CAM DIAGNOSTIC COMPLETE"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()