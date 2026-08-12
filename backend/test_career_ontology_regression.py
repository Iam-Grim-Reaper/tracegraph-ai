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


CAREER_PATH = Path(
    "../data/career_fixture.txt"
)

RESEARCH_DOCUMENT_ID = (
    "1290eef8-11ec-5161-8f6f-"
    "ac5782b76b18"
)


EXPECTED_CAREER_RELATIONSHIPS = {
    "WORKED_AT",
    "HAS_ROLE",
    "HAS_SKILL",
    "EARNED_DEGREE",
    "CERTIFIED_IN",
}


def main():
    print("=" * 70)

    print(
        "TRACEGRAPH CAREER ONTOLOGY "
        "REGRESSION"
    )

    print("=" * 70)

    if not CAREER_PATH.exists():
        raise FileNotFoundError(
            f"Career fixture not found: "
            f"{CAREER_PATH.resolve()}"
        )

    # =================================================
    # 1. Ingest career document
    # =================================================

    print(
        "\n[1/6] Ingesting career document..."
    )

    ingestion = (
        IngestionService(
            max_chars=1000
        )
        .ingest(
            CAREER_PATH
        )
    )

    document = (
        ingestion.document
    )

    chunks = (
        ingestion.chunks
    )

    if not chunks:
        raise RuntimeError(
            "Career fixture produced "
            "no chunks."
        )

    career_document_id = str(
        document.id
    )

    print(
        "Document ID:",
        career_document_id,
    )

    print(
        "Filename:",
        document.filename,
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
            "Career fixture contains "
            "no usable text."
        )

    # =================================================
    # 2. Automatic ontology classification
    #
    # Disable LLM fallback intentionally.
    # The resume should be obvious enough for
    # deterministic classification.
    # =================================================

    print(
        "\n[2/6] Classifying ontology..."
    )

    classifier = (
        OntologyClassifier(
            enable_llm_fallback=False
        )
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

    print(
        "Scores:",
        classification.scores,
    )

    if (
        selected_ontology.name
        != "career"
    ):
        raise RuntimeError(
            "Expected career fixture "
            "to classify as career, "
            f"received "
            f"'{selected_ontology.name}'."
        )

    # =================================================
    # 3. Career graph indexing
    #
    # This performs real Gemini graph extraction.
    #
    # Because the cache is ontology-aware,
    # career-v2.2 data is completely separate
    # from research-v2.2 cache data.
    # =================================================

    print(
        "\n[3/6] Building career graph..."
    )

    graph_indexer = (
        GraphIndexer(
            batch_size=1,
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
        "\nCareer graph statistics:"
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
    # 4. Verify career-specific graph semantics
    # =================================================

    print(
        "\n[4/6] Verifying career graph..."
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
                    d.filename
                        AS filename,

                    d.ontology_profile
                        AS ontology_profile,

                    d.ontology_version
                        AS ontology_version
                """,
                {
                    "document_id": (
                        career_document_id
                    )
                },
            )
        )

        if not document_rows:
            raise RuntimeError(
                "Career document was not "
                "stored in Neo4j."
            )

        stored_document = (
            document_rows[0]
        )

        print(
            "Stored ontology:",
            stored_document[
                "ontology_profile"
            ],
        )

        print(
            "Stored ontology version:",
            stored_document[
                "ontology_version"
            ],
        )

        if (
            stored_document[
                "ontology_profile"
            ]
            != "career"
        ):
            raise RuntimeError(
                "Career document has incorrect "
                "Neo4j ontology metadata."
            )

        # -----------------------------------------
        # Career semantic relationships
        # -----------------------------------------

        relationship_rows = (
            store.query(
                """
                MATCH (
                    source:Entity
                )-[r]->(
                    target:Entity
                )

                WHERE
                    r.source_document_id
                        = $document_id

                    AND NOT type(r) IN [
                        'CONTAINS',
                        'MENTIONS'
                    ]

                RETURN
                    source.name
                        AS source,

                    source.entity_type
                        AS source_type,

                    type(r)
                        AS relationship,

                    target.name
                        AS target,

                    target.entity_type
                        AS target_type,

                    r.evidence_text
                        AS evidence,

                    r.ontology_profile
                        AS ontology_profile,

                    r.ontology_version
                        AS ontology_version

                ORDER BY
                    relationship,
                    source,
                    target
                """,
                {
                    "document_id": (
                        career_document_id
                    )
                },
            )
        )

        print(
            "\nStored career relationships:"
        )

        relationship_types = set()

        for row in relationship_rows:
            relationship_types.add(
                row["relationship"]
            )

            print(
                row["source"],
                f"({row['source_type']})",
                "-[",
                row["relationship"],
                "]->",
                row["target"],
                f"({row['target_type']})",
            )

        print(
            "\nRelationship types:",
            sorted(
                relationship_types
            ),
        )

        missing_types = (
            EXPECTED_CAREER_RELATIONSHIPS
            - relationship_types
        )

        if missing_types:
            raise RuntimeError(
                "Missing expected career "
                "relationship types: "
                f"{sorted(missing_types)}"
            )

        # -----------------------------------------
        # All career facts must carry career
        # ontology provenance.
        # -----------------------------------------

        invalid_ontology_rows = [
            row
            for row in relationship_rows
            if (
                row[
                    "ontology_profile"
                ]
                != "career"
                or
                row[
                    "ontology_version"
                ]
                != "2.0"
            )
        ]

        if invalid_ontology_rows:
            raise RuntimeError(
                "Some career relationships "
                "have incorrect ontology "
                "provenance."
            )

        # =================================================
        # 5. Career document-scoped retrieval
        # =================================================

        print(
            "\n[5/6] Testing career "
            "document-scoped retrieval..."
        )

        retriever = (
            GraphQueryRetriever(
                store=store
            )
        )

        career_result = (
            retriever.retrieve(
                query=(
                    "Where did Alex Morgan work "
                    "and what skills does "
                    "Alex Morgan have?"
                ),

                max_seed_entities=5,
                max_facts=30,

                document_ids=[
                    career_document_id
                ],
            )
        )

        print(
            "Career linked entities:",
            len(
                career_result
                .linked_entities
            ),
        )

        print(
            "Career retrieved facts:",
            len(
                career_result.facts
            ),
        )

        career_fact_types = {
            fact.relationship_type
            for fact
            in career_result.facts
        }

        print(
            "Retrieved career fact types:",
            sorted(
                career_fact_types
            ),
        )

        if (
            "WORKED_AT"
            not in career_fact_types
        ):
            raise RuntimeError(
                "Career-scoped GraphRAG "
                "failed to retrieve WORKED_AT."
            )

        if (
            "HAS_SKILL"
            not in career_fact_types
        ):
            raise RuntimeError(
                "Career-scoped GraphRAG "
                "failed to retrieve HAS_SKILL."
            )

        # =================================================
        # 6. Cross-document isolation
        # =================================================

        print(
            "\n[6/6] Testing research/career "
            "scope isolation..."
        )

        # -----------------------------------------
        # Career question under RESEARCH scope.
        # -----------------------------------------

        research_scope_career_query = (
            retriever.retrieve(
                query=(
                    "Where did Alex Morgan work?"
                ),

                max_seed_entities=5,
                max_facts=20,

                document_ids=[
                    RESEARCH_DOCUMENT_ID
                ],
            )
        )

        leaked_career_facts = [
            fact
            for fact
            in (
                research_scope_career_query
                .facts
            )
            if (
                fact.relationship_type
                in EXPECTED_CAREER_RELATIONSHIPS
            )
        ]

        print(
            "Career facts found under "
            "research scope:",
            len(
                leaked_career_facts
            ),
        )

        if leaked_career_facts:
            raise RuntimeError(
                "Career graph facts leaked "
                "into research document scope."
            )

        # -----------------------------------------
        # Research question under CAREER scope.
        # -----------------------------------------

        career_scope_research_query = (
            retriever.retrieve(
                query=(
                    "Who developed Grad-CAM?"
                ),

                max_seed_entities=5,
                max_facts=20,

                document_ids=[
                    career_document_id
                ],
            )
        )

        leaked_research_facts = [
            fact
            for fact
            in (
                career_scope_research_query
                .facts
            )
            if (
                fact.relationship_type
                == "DEVELOPED_BY"
                and
                "selvaraju"
                in (
                    fact.target_name
                    or ""
                ).casefold()
            )
        ]

        print(
            "Grad-CAM facts found under "
            "career scope:",
            len(
                leaked_research_facts
            ),
        )

        if leaked_research_facts:
            raise RuntimeError(
                "Research graph facts leaked "
                "into career document scope."
            )

        # -----------------------------------------
        # Make sure research retrieval STILL works
        # after adding the career document.
        # -----------------------------------------

        research_result = (
            retriever.retrieve(
                query=(
                    "Who developed Grad-CAM?"
                ),

                max_seed_entities=5,
                max_facts=20,

                document_ids=[
                    RESEARCH_DOCUMENT_ID
                ],
            )
        )

        research_fact_found = any(
            (
                fact.relationship_type
                == "DEVELOPED_BY"
                and
                "selvaraju"
                in (
                    fact.target_name
                    or ""
                ).casefold()
            )
            for fact
            in research_result.facts
        )

        print(
            "Grad-CAM still works under "
            "research scope:",
            research_fact_found,
        )

        if not research_fact_found:
            raise RuntimeError(
                "Existing research GraphRAG "
                "regression failed after adding "
                "career document."
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
        "CAREER ONTOLOGY "
        "REGRESSION VALID"
    )

    print("=" * 70)

    print(
        "Career auto-classification: PASS"
    )

    print(
        "Career ontology metadata:   PASS"
    )

    print(
        "Career relationships:       PASS"
    )

    print(
        "Career scoped retrieval:    PASS"
    )

    print(
        "Research scope isolation:   PASS"
    )

    print(
        "Career scope isolation:     PASS"
    )

    print(
        "Research regression:        PASS"
    )


if __name__ == "__main__":
    main()