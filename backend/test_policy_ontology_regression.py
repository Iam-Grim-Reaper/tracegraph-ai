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


POLICY_PATH = Path(
    "../data/policy_fixture.txt"
)

RESEARCH_DOCUMENT_ID = (
    "1290eef8-11ec-5161-8f6f-"
    "ac5782b76b18"
)

CAREER_DOCUMENT_ID = (
    "04685d93-3225-52a4-a22d-"
    "b9adfc05a058"
)

POLICY_RELATIONSHIP_TYPES = {
    "REQUIRES",
    "PROHIBITS",
    "GOVERNED_BY",
    "HAS_EXCEPTION",
}


def main():
    print("=" * 70)
    print(
        "TRACEGRAPH POLICY ONTOLOGY "
        "REGRESSION"
    )
    print("=" * 70)

    if not POLICY_PATH.exists():
        raise FileNotFoundError(
            f"Policy fixture not found: "
            f"{POLICY_PATH.resolve()}"
        )

    # =================================================
    # 1. Ingest
    # =================================================

    print(
        "\n[1/6] Ingesting policy document..."
    )

    ingestion = (
        IngestionService(
            max_chars=1000
        )
        .ingest(
            POLICY_PATH
        )
    )

    document = ingestion.document
    chunks = ingestion.chunks

    if not chunks:
        raise RuntimeError(
            "Policy fixture produced no chunks."
        )

    policy_document_id = str(
        document.id
    )

    document_text = (
        "\n\n".join(
            chunk.text
            for chunk in chunks
            if chunk.text.strip()
        )
    )

    print(
        "Document ID:",
        policy_document_id,
    )

    print(
        "Filename:",
        document.filename,
    )

    print(
        "Chunks:",
        len(chunks),
    )

    # =================================================
    # 2. Automatic ontology classification
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
        != "policy"
    ):
        raise RuntimeError(
            "Expected policy fixture "
            "to classify as policy, "
            f"received "
            f"'{selected_ontology.name}'."
        )

    # =================================================
    # 3. Graph indexing
    # =================================================

    print(
        "\n[3/6] Building policy graph..."
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
        "\nPolicy graph statistics:"
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
    # 4. Verify policy graph
    # =================================================

    print(
        "\n[4/6] Verifying policy graph..."
    )

    store = Neo4jGraphStore()

    try:
        store.verify_connectivity()

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
                        policy_document_id
                    )
                },
            )
        )

        if not document_rows:
            raise RuntimeError(
                "Policy document missing "
                "from Neo4j."
            )

        stored = document_rows[0]

        print(
            "Stored ontology:",
            stored[
                "ontology_profile"
            ],
        )

        print(
            "Stored ontology version:",
            stored[
                "ontology_version"
            ],
        )

        if (
            stored[
                "ontology_profile"
            ]
            != "policy"
        ):
            raise RuntimeError(
                "Incorrect policy ontology "
                "metadata."
            )

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
                        policy_document_id
                    )
                },
            )
        )

        print(
            "\nStored policy relationships:"
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

        # -----------------------------------------
        # We require these two especially important
        # policy semantics for the first policy
        # regression.
        #
        # REQUIRES / PROHIBITS are inspected too,
        # but we don't make all four mandatory yet
        # because we want to diagnose extraction
        # versus validation if Gemini omits one.
        # -----------------------------------------

        required_for_regression = {
            "GOVERNED_BY",
            "HAS_EXCEPTION",
        }

        missing = (
            required_for_regression
            - relationship_types
        )

        if missing:
            raise RuntimeError(
                "Missing required policy "
                "relationships: "
                f"{sorted(missing)}"
            )

        invalid_provenance = [
            row
            for row
            in relationship_rows
            if (
                row[
                    "ontology_profile"
                ]
                != "policy"
                or
                row[
                    "ontology_version"
                ]
                != "2.0"
            )
        ]

        if invalid_provenance:
            raise RuntimeError(
                "Policy relationship "
                "provenance is invalid."
            )

        # =================================================
        # 5. Policy-scoped retrieval
        # =================================================

        print(
            "\n[5/6] Testing policy "
            "document-scoped retrieval..."
        )

        retriever = (
            GraphQueryRetriever(
                store=store
            )
        )

        policy_result = (
            retriever.retrieve(
                query=(
                    "What regulation governs "
                    "the ACME Data Protection "
                    "Policy and what exception "
                    "does it have?"
                ),

                max_seed_entities=5,
                max_facts=30,

                document_ids=[
                    policy_document_id
                ],
            )
        )

        policy_fact_types = {
            fact.relationship_type
            for fact
            in policy_result.facts
        }

        print(
            "Policy linked entities:",
            len(
                policy_result
                .linked_entities
            ),
        )

        print(
            "Policy retrieved facts:",
            len(
                policy_result.facts
            ),
        )

        print(
            "Retrieved policy fact types:",
            sorted(
                policy_fact_types
            ),
        )

        if (
            "GOVERNED_BY"
            not in policy_fact_types
        ):
            raise RuntimeError(
                "Policy-scoped retrieval "
                "failed to retrieve "
                "GOVERNED_BY."
            )

        if (
            "HAS_EXCEPTION"
            not in policy_fact_types
        ):
            raise RuntimeError(
                "Policy-scoped retrieval "
                "failed to retrieve "
                "HAS_EXCEPTION."
            )

        # =================================================
        # 6. Cross-domain isolation
        # =================================================

        print(
            "\n[6/6] Testing cross-domain "
            "scope isolation..."
        )

        policy_under_research = (
            retriever.retrieve(
                query=(
                    "What regulation governs "
                    "the ACME Data Protection "
                    "Policy?"
                ),

                max_seed_entities=5,
                max_facts=20,

                document_ids=[
                    RESEARCH_DOCUMENT_ID
                ],
            )
        )

        leaked_policy_to_research = [
            fact
            for fact
            in policy_under_research.facts
            if (
                fact.relationship_type
                in POLICY_RELATIONSHIP_TYPES
            )
        ]

        print(
            "Policy facts under "
            "research scope:",
            len(
                leaked_policy_to_research
            ),
        )

        if leaked_policy_to_research:
            raise RuntimeError(
                "Policy facts leaked into "
                "research scope."
            )

        policy_under_career = (
            retriever.retrieve(
                query=(
                    "What exception does the "
                    "ACME Data Protection "
                    "Policy have?"
                ),

                max_seed_entities=5,
                max_facts=20,

                document_ids=[
                    CAREER_DOCUMENT_ID
                ],
            )
        )

        leaked_policy_to_career = [
            fact
            for fact
            in policy_under_career.facts
            if (
                fact.relationship_type
                in POLICY_RELATIONSHIP_TYPES
            )
        ]

        print(
            "Policy facts under "
            "career scope:",
            len(
                leaked_policy_to_career
            ),
        )

        if leaked_policy_to_career:
            raise RuntimeError(
                "Policy facts leaked into "
                "career scope."
            )

        # -----------------------------------------
        # Existing research regression
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

        research_ok = any(
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
            "Research regression:",
            research_ok,
        )

        if not research_ok:
            raise RuntimeError(
                "Research regression failed "
                "after policy indexing."
            )

        # -----------------------------------------
        # Existing career regression
        # -----------------------------------------

        career_result = (
            retriever.retrieve(
                query=(
                    "Where did Alex Morgan work?"
                ),

                max_seed_entities=5,
                max_facts=20,

                document_ids=[
                    CAREER_DOCUMENT_ID
                ],
            )
        )

        career_ok = any(
            (
                fact.relationship_type
                == "WORKED_AT"
            )
            for fact
            in career_result.facts
        )

        print(
            "Career regression:",
            career_ok,
        )

        if not career_ok:
            raise RuntimeError(
                "Career regression failed "
                "after policy indexing."
            )

    finally:
        store.close()

    print(
        "\n" + "=" * 70
    )

    print(
        "POLICY ONTOLOGY "
        "REGRESSION VALID"
    )

    print("=" * 70)

    print(
        "Policy auto-classification: PASS"
    )

    print(
        "Policy ontology metadata:   PASS"
    )

    print(
        "Policy graph semantics:     PASS"
    )

    print(
        "Policy scoped retrieval:    PASS"
    )

    print(
        "Research isolation:         PASS"
    )

    print(
        "Career isolation:           PASS"
    )

    print(
        "Research regression:        PASS"
    )

    print(
        "Career regression:          PASS"
    )


if __name__ == "__main__":
    main()