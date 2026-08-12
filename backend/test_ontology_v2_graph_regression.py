from pathlib import Path

from app.graph.graph_query import (
    GraphQueryRetriever,
)
from app.graph.indexer import (
    GraphIndexer,
)
from app.graph.ontology_classifier import (
    OntologyClassifier,
)
from app.graph.store import (
    Neo4jGraphStore,
)
from app.ingestion.service import (
    IngestionService,
)


SAMPLE_PATH = Path(
    "../data/sample.pdf"
)

EXPECTED_DOCUMENT_ID = (
    "1290eef8-11ec-5161-8f6f-"
    "ac5782b76b18"
)


def main():
    print("=" * 70)

    print(
        "TRACEGRAPH ONTOLOGY V2 "
        "GRAPH REGRESSION"
    )

    print("=" * 70)

    if not SAMPLE_PATH.exists():
        raise FileNotFoundError(
            f"Sample PDF not found: "
            f"{SAMPLE_PATH.resolve()}"
        )

    # =================================================
    # 1. Ingestion
    # =================================================

    print(
        "\n[1/5] Ingesting sample.pdf..."
    )

    ingestion_service = (
        IngestionService(
            max_chars=1000
        )
    )

    ingestion = (
        ingestion_service.ingest(
            SAMPLE_PATH
        )
    )

    document = (
        ingestion.document
    )

    chunks = (
        ingestion.chunks
    )

    if str(document.id) != EXPECTED_DOCUMENT_ID:
        raise RuntimeError(
            "Stable document ID changed. "
            f"Expected {EXPECTED_DOCUMENT_ID}, "
            f"received {document.id}"
        )

    if len(chunks) != 30:
        raise RuntimeError(
            "Expected 30 chunks, "
            f"received {len(chunks)}"
        )

    print(
        "Document ID:",
        document.id,
    )

    print(
        "Chunks:",
        len(chunks),
    )

    document_text = (
        "\n\n".join(
            chunk.text
            for chunk in chunks
            if chunk.text.strip()
        )
    )

    if not document_text.strip():
        raise RuntimeError(
            "Document contains no "
            "usable text"
        )

    # =================================================
    # 2. Automatic ontology classification
    # =================================================

    print(
        "\n[2/5] Classifying ontology..."
    )

    classifier = (
        OntologyClassifier()
    )

    classification = (
        classifier.classify(
            document=document,
            document_text=document_text,
        )
    )

    selected_ontology = (
        classification.profile
    )

    print(
        "Selected ontology:",
        selected_ontology.name,
    )

    print(
        "Ontology version:",
        selected_ontology.version,
    )

    print(
        "Confidence:",
        f"{classification.confidence:.2f}",
    )

    print(
        "Method:",
        classification.method,
    )

    if (
        selected_ontology.name
        != "research"
    ):
        raise RuntimeError(
            "sample.pdf must classify "
            "as research."
        )

    if (
        selected_ontology.version
        != "2.0"
    ):
        raise RuntimeError(
            "Expected ontology version 2.0."
        )

    # =================================================
    # 3. Real Ontology-v2 graph indexing
    #
    # IMPORTANT:
    #
    # This WILL perform Gemini graph extraction
    # because the v2 ontology-aware cache is
    # intentionally separate from v1.
    # =================================================

    print(
        "\n[3/5] Building Ontology-v2 graph..."
    )

    graph_indexer = (
        GraphIndexer(
            batch_size=5,
            ontology_profile=(
                selected_ontology
            ),
        )
    )

    graph_stats = (
        graph_indexer.index(
            document=document,
            chunks=chunks,
        )
    )

    print(
        "\nGraph indexing statistics:"
    )

    print(
        "Chunks:",
        graph_stats.chunk_count,
    )

    print(
        "Cache hits:",
        graph_stats.cached_chunks,
    )

    print(
        "Newly extracted:",
        graph_stats.extracted_chunks,
    )

    print(
        "Entities:",
        graph_stats.entity_count,
    )

    print(
        "Semantic relationships:",
        graph_stats
        .semantic_relationship_count,
    )

    print(
        "Rejected relationships:",
        graph_stats
        .rejected_relationship_count,
    )

    # =================================================
    # 4. Neo4j integrity checks
    # =================================================

    print(
        "\n[4/5] Verifying Neo4j "
        "Ontology-v2 state..."
    )

    store = (
        Neo4jGraphStore()
    )

    try:
        store.verify_connectivity()

        # -----------------------------------------
        # Document ontology metadata
        # -----------------------------------------

        document_rows = (
            store.query(
                """
                MATCH (
                    d:Document {
                        document_id:
                            $document_id
                    }
                )

                RETURN
                    d.ontology_profile
                        AS ontology_profile,

                    d.ontology_version
                        AS ontology_version
                """,
                {
                    "document_id": (
                        EXPECTED_DOCUMENT_ID
                    )
                },
            )
        )

        if not document_rows:
            raise RuntimeError(
                "Document missing from Neo4j."
            )

        document_row = (
            document_rows[0]
        )

        print(
            "Stored document ontology:",
            document_row.get(
                "ontology_profile"
            ),
        )

        print(
            "Stored ontology version:",
            document_row.get(
                "ontology_version"
            ),
        )

        if (
            document_row.get(
                "ontology_profile"
            )
            != "research"
        ):
            raise RuntimeError(
                "Neo4j document ontology "
                "is not research."
            )

        if (
            document_row.get(
                "ontology_version"
            )
            != "2.0"
        ):
            raise RuntimeError(
                "Neo4j document ontology "
                "version is not 2.0."
            )

        # -----------------------------------------
        # Chunk ontology metadata
        # -----------------------------------------

        chunk_rows = (
            store.query(
                """
                MATCH (
                    d:Document {
                        document_id:
                            $document_id
                    }
                )-[:CONTAINS]->(
                    c:Chunk
                )

                RETURN
                    count(
                        DISTINCT c
                    ) AS chunk_count,

                    count(
                        CASE
                            WHEN
                                c.ontology_profile
                                    = 'research'

                                AND
                                c.ontology_version
                                    = '2.0'

                            THEN 1
                        END
                    ) AS v2_chunk_count
                """,
                {
                    "document_id": (
                        EXPECTED_DOCUMENT_ID
                    )
                },
            )
        )

        chunk_row = (
            chunk_rows[0]
        )

        print(
            "Stored chunks:",
            chunk_row[
                "chunk_count"
            ],
        )

        print(
            "Ontology-v2 chunks:",
            chunk_row[
                "v2_chunk_count"
            ],
        )

        if (
            chunk_row[
                "chunk_count"
            ]
            != 30
        ):
            raise RuntimeError(
                "Neo4j does not contain "
                "exactly 30 document chunks."
            )

        if (
            chunk_row[
                "v2_chunk_count"
            ]
            != 30
        ):
            raise RuntimeError(
                "Not every chunk was migrated "
                "to research ontology 2.0."
            )

        # -----------------------------------------
        # Relationship migration integrity
        #
        # There must be no old semantic
        # relationship provenance remaining for
        # this document.
        # -----------------------------------------

        relationship_rows = (
            store.query(
                """
                MATCH ()-[r]->()

                WHERE
                    r.source_document_id
                        = $document_id

                    AND NOT type(r) IN [
                        'CONTAINS',
                        'MENTIONS'
                    ]

                RETURN
                    count(r)
                        AS relationship_count,

                    count(
                        CASE
                            WHEN
                                r.ontology_profile
                                    = 'research'

                                AND
                                r.ontology_version
                                    = '2.0'

                            THEN 1
                        END
                    ) AS v2_relationship_count,

                    count(
                        CASE
                            WHEN
                                r.ontology_version
                                    IS NULL

                                OR
                                r.ontology_version
                                    <> '2.0'

                            THEN 1
                        END
                    ) AS stale_relationship_count
                """,
                {
                    "document_id": (
                        EXPECTED_DOCUMENT_ID
                    )
                },
            )
        )

        relationship_row = (
            relationship_rows[0]
        )

        print(
            "Semantic relationships:",
            relationship_row[
                "relationship_count"
            ],
        )

        print(
            "Ontology-v2 relationships:",
            relationship_row[
                "v2_relationship_count"
            ],
        )

        print(
            "Stale v1 relationships:",
            relationship_row[
                "stale_relationship_count"
            ],
        )

        if (
            relationship_row[
                "stale_relationship_count"
            ]
            != 0
        ):
            raise RuntimeError(
                "Stale Ontology-v1 semantic "
                "relationships remain."
            )

        if (
            relationship_row[
                "relationship_count"
            ]
            != relationship_row[
                "v2_relationship_count"
            ]
        ):
            raise RuntimeError(
                "Not every semantic relationship "
                "belongs to Ontology v2."
            )

        # -----------------------------------------
        # Known regression fact:
        #
        # Grad-CAM DEVELOPED_BY
        # R. R. Selvaraju et al.
        # -----------------------------------------

        gradcam_rows = (
            store.query(
                """
                MATCH (
                    source:Entity
                )-[
                    r:DEVELOPED_BY
                ]->(
                    target:Entity
                )

                WHERE
                    r.source_document_id
                        = $document_id

                    AND (
                        toLower(
                            source.name
                        ) CONTAINS 'grad-cam'

                        OR (
                            toLower(
                                source.name
                            ) CONTAINS 'grad'

                            AND
                            toLower(
                                source.name
                            ) CONTAINS 'cam'
                        )

                        OR any(
                            alias
                            IN coalesce(
                                source.aliases,
                                []
                            )

                            WHERE
                                toLower(
                                    alias
                                )
                                CONTAINS
                                'grad-cam'
                        )
                    )

                RETURN
                    source.name
                        AS source,

                    type(r)
                        AS relationship,

                    target.name
                        AS target,

                    r.source_chunk_id
                        AS source_chunk_id,

                    r.ontology_profile
                        AS ontology_profile,

                    r.ontology_version
                        AS ontology_version
                """,
                {
                    "document_id": (
                        EXPECTED_DOCUMENT_ID
                    )
                },
            )
        )

        print(
            "Grad-CAM DEVELOPED_BY facts:",
            len(
                gradcam_rows
            ),
        )

        for row in gradcam_rows:
            print(
                row["source"],
                "-[",
                row["relationship"],
                "]->",
                row["target"],
            )

        if not gradcam_rows:
            raise RuntimeError(
                "Ontology-v2 regression: "
                "Grad-CAM DEVELOPED_BY fact "
                "was not found."
            )

        has_selvaraju = any(
            "selvaraju"
            in (
                row["target"]
                or ""
            ).casefold()

            for row
            in gradcam_rows
        )

        if not has_selvaraju:
            raise RuntimeError(
                "Grad-CAM DEVELOPED_BY "
                "Selvaraju regression failed."
            )

        # =================================================
        # 5. Scoped graph retrieval regression
        # =================================================

        print(
            "\n[5/5] Testing scoped "
            "GraphRAG retrieval..."
        )

        graph_retriever = (
            GraphQueryRetriever(
                store=store
            )
        )

        retrieval = (
            graph_retriever.retrieve(
                query=(
                    "Who developed Grad-CAM?"
                ),

                max_seed_entities=5,

                max_facts=20,

                document_ids=[
                    EXPECTED_DOCUMENT_ID
                ],
            )
        )

        print(
            "Linked entities:",
            len(
                retrieval
                .linked_entities
            ),
        )

        print(
            "Retrieved graph facts:",
            len(
                retrieval.facts
            ),
        )

        developed_by_facts = [
            fact

            for fact
            in retrieval.facts

            if (
                fact.relationship_type
                == "DEVELOPED_BY"

                and
                "selvaraju"
                in fact.target_name.casefold()
            )
        ]

        if not developed_by_facts:
            raise RuntimeError(
                "Scoped GraphRAG retrieval "
                "could not recover the "
                "Grad-CAM developer fact."
            )

    finally:
        store.close()

    # =================================================
    # Success
    # =================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "ONTOLOGY V2 GRAPH "
        "REGRESSION VALID"
    )

    print("=" * 70)

    print(
        "Stable document ID:      PASS"
    )

    print(
        "Automatic ontology:      PASS"
    )

    print(
        "Ontology-v2 migration:   PASS"
    )

    print(
        "No stale v1 facts:       PASS"
    )

    print(
        "Grad-CAM fact:           PASS"
    )

    print(
        "Scoped graph retrieval:  PASS"
    )


if __name__ == "__main__":
    main()