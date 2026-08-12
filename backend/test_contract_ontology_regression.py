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


CONTRACT_PATH = Path(
    "../data/contract_fixture.txt"
)

RESEARCH_DOCUMENT_ID = (
    "1290eef8-11ec-5161-8f6f-"
    "ac5782b76b18"
)

CAREER_DOCUMENT_ID = (
    "04685d93-3225-52a4-a22d-"
    "b9adfc05a058"
)

POLICY_DOCUMENT_ID = (
    "fcf54ff5-72d9-5ef6-b5b2-"
    "1084c8ab7af3"
)


CONTRACT_RELATIONSHIP_TYPES = {
    "HAS_OBLIGATION",
    "GRANTS_RIGHT",
    "APPLIES_TO_PARTY",
    "TERMINATES_ON",
    "REQUIRES",
}


def main():
    print("=" * 70)

    print(
        "TRACEGRAPH CONTRACT ONTOLOGY "
        "REGRESSION"
    )

    print("=" * 70)

    if not CONTRACT_PATH.exists():
        raise FileNotFoundError(
            f"Contract fixture not found: "
            f"{CONTRACT_PATH.resolve()}"
        )

    # =================================================
    # 1. Ingest contract document
    # =================================================

    print(
        "\n[1/6] Ingesting contract document..."
    )

    ingestion = (
        IngestionService(
            max_chars=1000
        )
        .ingest(
            CONTRACT_PATH
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
            "Contract fixture produced "
            "no chunks."
        )

    contract_document_id = str(
        document.id
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
            "Contract fixture contained "
            "no usable text."
        )

    print(
        "Document ID:",
        contract_document_id,
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
        != "contract"
    ):
        raise RuntimeError(
            "Expected contract fixture "
            "to classify as contract, "
            f"received "
            f"'{selected_ontology.name}'."
        )

    # =================================================
    # 3. Contract graph indexing
    # =================================================

    print(
        "\n[3/6] Building contract graph..."
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
        "\nContract graph statistics:"
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
    # 4. Verify contract graph
    # =================================================

    print(
        "\n[4/6] Verifying contract graph..."
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
                        contract_document_id
                    )
                },
            )
        )

        if not document_rows:
            raise RuntimeError(
                "Contract document missing "
                "from Neo4j."
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
            != "contract"
        ):
            raise RuntimeError(
                "Contract document has "
                "incorrect ontology metadata."
            )

        if (
            stored_document[
                "ontology_version"
            ]
            != "2.0"
        ):
            raise RuntimeError(
                "Contract ontology version "
                "is incorrect."
            )

        # -----------------------------------------
        # Retrieve all semantic relationships
        # sourced from this contract.
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
                        contract_document_id
                    )
                },
            )
        )

        print(
            "\nStored contract relationships:"
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
        # These are the central contract semantics
        # we require for the first regression.
        #
        # TERMINATES_ON and REQUIRES are inspected
        # but are not initially mandatory because
        # we want to diagnose extraction behavior
        # independently if Gemini omits either.
        # -----------------------------------------

        required_contract_types = {
            "HAS_OBLIGATION",
            "GRANTS_RIGHT",
            "APPLIES_TO_PARTY",
        }

        missing_types = (
            required_contract_types
            - relationship_types
        )

        if missing_types:
            raise RuntimeError(
                "Missing required contract "
                "relationship types: "
                f"{sorted(missing_types)}"
            )

        # -----------------------------------------
        # Ontology provenance
        # -----------------------------------------

        invalid_provenance = [
            row
            for row in relationship_rows
            if (
                row[
                    "ontology_profile"
                ]
                != "contract"
                or
                row[
                    "ontology_version"
                ]
                != "2.0"
            )
        ]

        if invalid_provenance:
            raise RuntimeError(
                "Some contract relationships "
                "have incorrect ontology "
                "provenance."
            )

                # =================================================
        # 5. Contract document-scoped retrieval
        # =================================================

        print(
            "\n[5/6] Testing contract "
            "document-scoped retrieval..."
        )

        retriever = (
            GraphQueryRetriever(
                store=store
            )
        )

        # -----------------------------------------
        # Query A:
        # obligation facts around Northstar
        # -----------------------------------------

        obligation_result = (
            retriever.retrieve(
                query=(
                    "What obligation does "
                    "Northstar Analytics LLC "
                    "have?"
                ),

                max_seed_entities=5,
                max_facts=30,

                document_ids=[
                    contract_document_id
                ],
            )
        )

        obligation_fact_types = {
            fact.relationship_type
            for fact
            in obligation_result.facts
        }

        print(
            "Obligation linked entities:",
            len(
                obligation_result
                .linked_entities
            ),
        )

        print(
            "Obligation retrieved facts:",
            len(
                obligation_result.facts
            ),
        )

        print(
            "Obligation fact types:",
            sorted(
                obligation_fact_types
            ),
        )

        if (
            "HAS_OBLIGATION"
            not in obligation_fact_types
        ):
            raise RuntimeError(
                "Contract-scoped retrieval "
                "failed to retrieve "
                "HAS_OBLIGATION."
            )

        # -----------------------------------------
        # Query B:
        # rights around the clause that grants it
        #
        # GRANTS_RIGHT belongs to a different
        # connected component from Northstar in
        # the current extracted contract graph.
        # Therefore test it using its own
        # explicit graph anchor.
        # -----------------------------------------

        right_result = (
            retriever.retrieve(
                query=(
                    "What right does the "
                    "Service Terms Clause grant?"
                ),

                max_seed_entities=5,
                max_facts=30,

                document_ids=[
                    contract_document_id
                ],
            )
        )

        right_fact_types = {
            fact.relationship_type
            for fact
            in right_result.facts
        }

        print(
            "Right linked entities:",
            len(
                right_result
                .linked_entities
            ),
        )

        print(
            "Right retrieved facts:",
            len(
                right_result.facts
            ),
        )

        print(
            "Right fact types:",
            sorted(
                right_fact_types
            ),
        )

        if (
            "GRANTS_RIGHT"
            not in right_fact_types
        ):
            raise RuntimeError(
                "Contract-scoped retrieval "
                "failed to retrieve "
                "GRANTS_RIGHT."
            )

        # -----------------------------------------
        # Verify actual fact content as well,
        # not just relationship type.
        # -----------------------------------------

        obligation_fact_found = any(
            (
                fact.relationship_type
                == "HAS_OBLIGATION"

                and
                "northstar"
                in (
                    fact.source_name
                    or ""
                ).casefold()

                and
                "data protection obligation"
                in (
                    fact.target_name
                    or ""
                ).casefold()
            )

            for fact
            in obligation_result.facts
        )

        if not obligation_fact_found:
            raise RuntimeError(
                "Expected Northstar "
                "HAS_OBLIGATION "
                "Data Protection Obligation "
                "fact was not retrieved."
            )

        right_fact_found = any(
            (
                fact.relationship_type
                == "GRANTS_RIGHT"

                and
                "service terms clause"
                in (
                    fact.source_name
                    or ""
                ).casefold()

                and
                "audit right"
                in (
                    fact.target_name
                    or ""
                ).casefold()
            )

            for fact
            in right_result.facts
        )

        if not right_fact_found:
            raise RuntimeError(
                "Expected Service Terms Clause "
                "GRANTS_RIGHT Audit Right "
                "fact was not retrieved."
            )

        print(
            "Contract obligation retrieval:",
            obligation_fact_found,
        )

        print(
            "Contract right retrieval:",
            right_fact_found,
        )
        # =================================================
        # 6. Four-domain scope isolation
        # =================================================

        print(
            "\n[6/6] Testing four-domain "
            "scope isolation..."
        )

        # -----------------------------------------
        # Contract query inside research scope
        # -----------------------------------------

        research_scope = (
            retriever.retrieve(
                query=(
                    "What obligation does "
                    "Northstar Analytics LLC "
                    "have?"
                ),

                max_seed_entities=5,
                max_facts=20,

                document_ids=[
                    RESEARCH_DOCUMENT_ID
                ],
            )
        )

        research_leaks = [
            fact
            for fact
            in research_scope.facts
            if (
                fact.relationship_type
                in CONTRACT_RELATIONSHIP_TYPES
            )
        ]

        print(
            "Contract facts under "
            "research scope:",
            len(
                research_leaks
            ),
        )

        if research_leaks:
            raise RuntimeError(
                "Contract facts leaked into "
                "research scope."
            )

        # -----------------------------------------
        # Contract query inside career scope
        # -----------------------------------------

        career_scope = (
            retriever.retrieve(
                query=(
                    "What right is granted "
                    "under the contract?"
                ),

                max_seed_entities=5,
                max_facts=20,

                document_ids=[
                    CAREER_DOCUMENT_ID
                ],
            )
        )

        career_leaks = [
            fact
            for fact
            in career_scope.facts
            if (
                fact.relationship_type
                in CONTRACT_RELATIONSHIP_TYPES
            )
        ]

        print(
            "Contract facts under "
            "career scope:",
            len(
                career_leaks
            ),
        )

        if career_leaks:
            raise RuntimeError(
                "Contract facts leaked into "
                "career scope."
            )

        # -----------------------------------------
        # Contract query inside policy scope
        # -----------------------------------------

        policy_scope = (
            retriever.retrieve(
                query=(
                    "What obligation does "
                    "Northstar Analytics LLC "
                    "have?"
                ),

                max_seed_entities=5,
                max_facts=20,

                document_ids=[
                    POLICY_DOCUMENT_ID
                ],
            )
        )

        policy_leaks = [
            fact
            for fact
            in policy_scope.facts
            if (
                fact.relationship_type
                in CONTRACT_RELATIONSHIP_TYPES
            )
        ]

        print(
            "Contract facts under "
            "policy scope:",
            len(
                policy_leaks
            ),
        )

        if policy_leaks:
            raise RuntimeError(
                "Contract facts leaked into "
                "policy scope."
            )

        # -----------------------------------------
        # Research regression
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
                "after contract indexing."
            )

        # -----------------------------------------
        # Career regression
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
                "after contract indexing."
            )

        # -----------------------------------------
        # Policy regression
        # -----------------------------------------

        policy_result = (
            retriever.retrieve(
                query=(
                    "What regulation governs "
                    "the ACME Data Protection "
                    "Policy?"
                ),

                max_seed_entities=5,
                max_facts=20,

                document_ids=[
                    POLICY_DOCUMENT_ID
                ],
            )
        )

        policy_ok = any(
            (
                fact.relationship_type
                == "GOVERNED_BY"
            )
            for fact
            in policy_result.facts
        )

        print(
            "Policy regression:",
            policy_ok,
        )

        if not policy_ok:
            raise RuntimeError(
                "Policy regression failed "
                "after contract indexing."
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
        "CONTRACT ONTOLOGY "
        "REGRESSION VALID"
    )

    print("=" * 70)

    print(
        "Contract auto-classification: PASS"
    )

    print(
        "Contract ontology metadata:   PASS"
    )

    print(
        "Contract graph semantics:     PASS"
    )

    print(
        "Contract scoped retrieval:    PASS"
    )

    print(
        "Research isolation:           PASS"
    )

    print(
        "Career isolation:             PASS"
    )

    print(
        "Policy isolation:             PASS"
    )

    print(
        "Research regression:          PASS"
    )

    print(
        "Career regression:            PASS"
    )

    print(
        "Policy regression:            PASS"
    )


if __name__ == "__main__":
    main()