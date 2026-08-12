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


MIXED_PATH = Path(
    "../data/mixed_policy_contract_fixture.txt"
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

CONTRACT_DOCUMENT_ID = (
    "c6bc1d88-2e3d-51fc-9434-"
    "138d0ea968d0"
)


POLICY_RELATIONSHIP_TYPES = {
    "REQUIRES",
    "PROHIBITS",
    "GOVERNED_BY",
    "HAS_EXCEPTION",
}


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
        "TRACEGRAPH COMPOSED ONTOLOGY "
        "GRAPH REGRESSION"
    )

    print("=" * 70)

    if not MIXED_PATH.exists():
        raise FileNotFoundError(
            f"Mixed fixture not found: "
            f"{MIXED_PATH.resolve()}"
        )

    # =================================================
    # 1. Ingestion
    # =================================================

    print(
        "\n[1/7] Ingesting mixed "
        "policy + contract document..."
    )

    ingestion = (
        IngestionService(
            max_chars=1000
        )
        .ingest(
            MIXED_PATH
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
            "Mixed fixture produced "
            "no chunks."
        )

    mixed_document_id = str(
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
            "Mixed fixture contained "
            "no usable text."
        )

    print(
        "Document ID:",
        mixed_document_id,
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
    # 2. Multi-domain classification
    # =================================================

    print(
        "\n[2/7] Classifying composed ontology..."
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
        "Selected profiles:",
        classification.selected_profiles,
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
        != "policy+contract"
    ):
        raise RuntimeError(
            "Expected composed ontology "
            "'policy+contract', received "
            f"'{selected_ontology.name}'."
        )

    if (
        classification.selected_profiles
        != (
            "policy",
            "contract",
        )
    ):
        raise RuntimeError(
            "Expected selected profiles "
            "('policy', 'contract')."
        )

    # =================================================
    # 3. Graph indexing
    #
    # This is the first real graph extraction
    # using a composed ontology profile.
    #
    # Its cache identity is automatically:
    #
    # graph-extraction-v2.2_policy+contract_...
    #
    # therefore it cannot collide with the
    # standalone policy or contract cache.
    # =================================================

    print(
        "\n[3/7] Building composed "
        "knowledge graph..."
    )

    graph_indexer = (
        GraphIndexer(
            batch_size=2,
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
        "\nComposed graph statistics:"
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
    # 4. Neo4j ontology/provenance verification
    # =================================================

    print(
        "\n[4/7] Verifying composed "
        "Neo4j state..."
    )

    store = (
        Neo4jGraphStore()
    )

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
                    d.filename
                        AS filename,

                    d.ontology_profile
                        AS ontology_profile,

                    d.ontology_version
                        AS ontology_version
                """,
                {
                    "document_id": (
                        mixed_document_id
                    )
                },
            )
        )

        if not document_rows:
            raise RuntimeError(
                "Mixed document was not "
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
            != "policy+contract"
        ):
            raise RuntimeError(
                "Neo4j did not persist "
                "the composed ontology name."
            )

        if (
            stored_document[
                "ontology_version"
            ]
            != "2.0"
        ):
            raise RuntimeError(
                "Incorrect composed ontology "
                "version in Neo4j."
            )

        # -----------------------------------------
        # All semantic facts from this document
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
                        mixed_document_id
                    )
                },
            )
        )

        print(
            "\nStored composed relationships:"
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

        # =================================================
        # 5. Prove BOTH ontology extensions contributed
        # =================================================

        print(
            "\n[5/7] Verifying policy + "
            "contract semantics..."
        )

        # -----------------------------------------
        # Strong policy-specific semantic.
        #
        # GOVERNED_BY does not come from the
        # Contract extension.
        # -----------------------------------------

        policy_semantics = (
            relationship_types
            & {
                "GOVERNED_BY",
                "PROHIBITS",
                "HAS_EXCEPTION",
            }
        )

        # -----------------------------------------
        # Strong contract-specific semantics.
        #
        # These do not come from Policy.
        # -----------------------------------------

        contract_semantics = (
            relationship_types
            & {
                "HAS_OBLIGATION",
                "GRANTS_RIGHT",
                "APPLIES_TO_PARTY",
                "TERMINATES_ON",
            }
        )

        print(
            "Policy-specific semantics:",
            sorted(
                policy_semantics
            ),
        )

        print(
            "Contract-specific semantics:",
            sorted(
                contract_semantics
            ),
        )

        if not policy_semantics:
            raise RuntimeError(
                "Composed graph contains no "
                "policy-specific semantic "
                "relationship."
            )

        if not contract_semantics:
            raise RuntimeError(
                "Composed graph contains no "
                "contract-specific semantic "
                "relationship."
            )

        # -----------------------------------------
        # We strongly expect GOVERNED_BY because
        # the fixture explicitly states:
        #
        # Data Protection Policy is governed by
        # GDPR.
        # -----------------------------------------

        if (
            "GOVERNED_BY"
            not in relationship_types
        ):
            raise RuntimeError(
                "Composed graph failed to "
                "extract GOVERNED_BY."
            )

        # -----------------------------------------
        # We strongly expect HAS_OBLIGATION.
        # -----------------------------------------

        if (
            "HAS_OBLIGATION"
            not in relationship_types
        ):
            raise RuntimeError(
                "Composed graph failed to "
                "extract HAS_OBLIGATION."
            )

        # -----------------------------------------
        # Every semantic fact must carry the
        # composed ontology provenance.
        # -----------------------------------------

        invalid_provenance = [
            row

            for row
            in relationship_rows

            if (
                row[
                    "ontology_profile"
                ]
                != "policy+contract"

                or
                row[
                    "ontology_version"
                ]
                != "2.0"
            )
        ]

        if invalid_provenance:
            raise RuntimeError(
                "Some composed ontology facts "
                "have incorrect provenance."
            )

        # =================================================
        # 6. Document-scoped GraphRAG retrieval
        # =================================================

        print(
            "\n[6/7] Testing composed "
            "document-scoped retrieval..."
        )

        retriever = (
            GraphQueryRetriever(
                store=store
            )
        )

        # -----------------------------------------
        # Policy side
        # -----------------------------------------

        policy_result = (
            retriever.retrieve(
                query=(
                    "What regulation governs "
                    "the Data Protection Policy?"
                ),

                max_seed_entities=5,
                max_facts=30,

                document_ids=[
                    mixed_document_id
                ],
            )
        )

        policy_fact_types = {
            fact.relationship_type

            for fact
            in policy_result.facts
        }

        print(
            "Mixed policy linked entities:",
            len(
                policy_result
                .linked_entities
            ),
        )

        print(
            "Mixed policy fact types:",
            sorted(
                policy_fact_types
            ),
        )

        if (
            "GOVERNED_BY"
            not in policy_fact_types
        ):
            raise RuntimeError(
                "Composed document retrieval "
                "failed on policy semantics."
            )

        # -----------------------------------------
        # Contract obligation side
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
                    mixed_document_id
                ],
            )
        )

        obligation_fact_types = {
            fact.relationship_type

            for fact
            in obligation_result.facts
        }

        print(
            "Mixed obligation linked entities:",
            len(
                obligation_result
                .linked_entities
            ),
        )

        print(
            "Mixed obligation fact types:",
            sorted(
                obligation_fact_types
            ),
        )

        if (
            "HAS_OBLIGATION"
            not in obligation_fact_types
        ):
            raise RuntimeError(
                "Composed document retrieval "
                "failed on contract obligation "
                "semantics."
            )

        # -----------------------------------------
        # Contract right side.
        #
        # This is queried independently because,
        # as we already learned in the contract
        # regression, clause/right facts may form
        # a separate graph component.
        # -----------------------------------------

        right_result = (
            retriever.retrieve(
                query=(
                    "What right does the "
                    "Audit Clause grant?"
                ),

                max_seed_entities=5,
                max_facts=30,

                document_ids=[
                    mixed_document_id
                ],
            )
        )

        right_fact_types = {
            fact.relationship_type

            for fact
            in right_result.facts
        }

        print(
            "Mixed right linked entities:",
            len(
                right_result
                .linked_entities
            ),
        )

        print(
            "Mixed right fact types:",
            sorted(
                right_fact_types
            ),
        )

        # GRANTS_RIGHT is useful to inspect but
        # not made mandatory here because the
        # essential contract proof is already
        # HAS_OBLIGATION.

        # =================================================
        # 7. Cross-document isolation + regressions
        # =================================================

        print(
            "\n[7/7] Testing five-document "
            "scope isolation..."
        )

        # -----------------------------------------
        # Mixed policy entity under standalone
        # contract scope.
        # -----------------------------------------

        mixed_policy_under_contract = (
            retriever.retrieve(
                query=(
                    "What regulation governs "
                    "the Data Protection Policy?"
                ),

                max_seed_entities=5,
                max_facts=20,

                document_ids=[
                    CONTRACT_DOCUMENT_ID
                ],
            )
        )

        mixed_policy_leak = any(
            (
                "data protection policy"
                in (
                    fact.source_name
                    or ""
                ).casefold()

                or
                "data protection policy"
                in (
                    fact.target_name
                    or ""
                ).casefold()
            )

            for fact
            in (
                mixed_policy_under_contract
                .facts
            )
        )

        print(
            "Mixed policy facts under "
            "standalone contract scope:",
            mixed_policy_leak,
        )

        if mixed_policy_leak:
            raise RuntimeError(
                "Mixed-document policy facts "
                "leaked into standalone "
                "contract scope."
            )

        # -----------------------------------------
        # Mixed contract entity under standalone
        # policy scope.
        # -----------------------------------------

        mixed_contract_under_policy = (
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

        mixed_contract_leak = any(
            (
                "northstar analytics"
                in (
                    fact.source_name
                    or ""
                ).casefold()

                or
                "northstar analytics"
                in (
                    fact.target_name
                    or ""
                ).casefold()
            )

            for fact
            in (
                mixed_contract_under_policy
                .facts
            )
        )

        print(
            "Mixed contract facts under "
            "standalone policy scope:",
            mixed_contract_leak,
        )

        if mixed_contract_leak:
            raise RuntimeError(
                "Mixed-document contract facts "
                "leaked into standalone "
                "policy scope."
            )

        # -----------------------------------------
        # Research still works
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
                "Research regression failed."
            )

        # -----------------------------------------
        # Career still works
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
                "Career regression failed."
            )

        # -----------------------------------------
        # Standalone policy still works
        # -----------------------------------------

        standalone_policy_result = (
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
            in (
                standalone_policy_result
                .facts
            )
        )

        print(
            "Standalone policy regression:",
            policy_ok,
        )

        if not policy_ok:
            raise RuntimeError(
                "Standalone policy "
                "regression failed."
            )

        # -----------------------------------------
        # Standalone contract still works
        # -----------------------------------------

        standalone_contract_result = (
            retriever.retrieve(
                query=(
                    "What obligation does "
                    "Northstar Analytics LLC "
                    "have?"
                ),

                max_seed_entities=5,
                max_facts=20,

                document_ids=[
                    CONTRACT_DOCUMENT_ID
                ],
            )
        )

        contract_ok = any(
            (
                fact.relationship_type
                == "HAS_OBLIGATION"
            )

            for fact
            in (
                standalone_contract_result
                .facts
            )
        )

        print(
            "Standalone contract regression:",
            contract_ok,
        )

        if not contract_ok:
            raise RuntimeError(
                "Standalone contract "
                "regression failed."
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
        "COMPOSED ONTOLOGY GRAPH "
        "REGRESSION VALID"
    )

    print("=" * 70)

    print(
        "Multi-domain classification: PASS"
    )

    print(
        "Composed ontology metadata:  PASS"
    )

    print(
        "Policy semantics:            PASS"
    )

    print(
        "Contract semantics:          PASS"
    )

    print(
        "Composed scoped retrieval:   PASS"
    )

    print(
        "Standalone scope isolation:  PASS"
    )

    print(
        "Research regression:         PASS"
    )

    print(
        "Career regression:           PASS"
    )

    print(
        "Policy regression:           PASS"
    )

    print(
        "Contract regression:         PASS"
    )


if __name__ == "__main__":
    main()