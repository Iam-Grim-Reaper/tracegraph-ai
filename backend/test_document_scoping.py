from app.graph.graph_query import (
    GraphQueryRetriever,
)
from app.graph.store import (
    Neo4jGraphStore,
)
from app.retrieval.hybrid_store import (
    HybridStore,
)


REAL_DOCUMENT_ID = (
    "1290eef8-11ec-5161-8f6f-"
    "ac5782b76b18"
)

FAKE_DOCUMENT_ID = (
    "00000000-0000-0000-0000-"
    "000000000000"
)


def main():
    print("=" * 70)

    print(
        "TRACEGRAPH DOCUMENT "
        "SCOPING TEST"
    )

    print("=" * 70)

    # =================================================
    # Qdrant
    # =================================================

    print(
        "\nTesting Qdrant "
        "document scope..."
    )

    hybrid_store = (
        HybridStore()
    )

    # Also ensures document_id payload
    # index exists.
    hybrid_store.ensure_collection()

    real_qdrant = (
        hybrid_store.lexical_search(
            query="Grad-CAM",
            limit=10,
            document_ids=[
                REAL_DOCUMENT_ID
            ],
        )
    )

    fake_qdrant = (
        hybrid_store.lexical_search(
            query="Grad-CAM",
            limit=10,
            document_ids=[
                FAKE_DOCUMENT_ID
            ],
        )
    )

    print(
        "Real document results:",
        len(real_qdrant),
    )

    print(
        "Fake document results:",
        len(fake_qdrant),
    )

    if not real_qdrant:
        raise RuntimeError(
            "Qdrant failed to retrieve "
            "from the selected document."
        )

    if fake_qdrant:
        raise RuntimeError(
            "Qdrant leaked results "
            "outside the selected "
            "document scope."
        )

    # Verify every returned payload.
    for point in real_qdrant:
        payload = (
            point.payload
            or {}
        )

        if (
            payload.get(
                "document_id"
            )
            != REAL_DOCUMENT_ID
        ):
            raise RuntimeError(
                "Qdrant returned a point "
                "from the wrong document."
            )

    # =================================================
    # Neo4j
    # =================================================

    print(
        "\nTesting Neo4j "
        "document scope..."
    )

    graph_store = (
        Neo4jGraphStore()
    )

    try:
        graph_store.verify_connectivity()

        retriever = (
            GraphQueryRetriever(
                store=graph_store
            )
        )

        real_graph = (
            retriever.retrieve(
                query=(
                    "Who developed "
                    "Grad-CAM?"
                ),
                document_ids=[
                    REAL_DOCUMENT_ID
                ],
            )
        )

        fake_graph = (
            retriever.retrieve(
                query=(
                    "Who developed "
                    "Grad-CAM?"
                ),
                document_ids=[
                    FAKE_DOCUMENT_ID
                ],
            )
        )

        print(
            "Real document "
            "linked entities:",
            len(
                real_graph
                .linked_entities
            ),
        )

        print(
            "Real document facts:",
            len(
                real_graph.facts
            ),
        )

        print(
            "Fake document "
            "linked entities:",
            len(
                fake_graph
                .linked_entities
            ),
        )

        print(
            "Fake document facts:",
            len(
                fake_graph.facts
            ),
        )

        if not real_graph.facts:
            raise RuntimeError(
                "Neo4j failed to retrieve "
                "facts from the selected "
                "document."
            )

        if (
            fake_graph.linked_entities
            or fake_graph.facts
        ):
            raise RuntimeError(
                "Neo4j leaked graph "
                "information outside the "
                "selected document scope."
            )

        # Provenance assertion.
        for fact in real_graph.facts:
            if (
                fact.source_document_id
                != REAL_DOCUMENT_ID
            ):
                raise RuntimeError(
                    "Neo4j returned a graph "
                    "fact from the wrong "
                    "document."
                )

    finally:
        graph_store.close()

    # =================================================
    # Success
    # =================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "DOCUMENT SCOPE VALID"
    )

    print("=" * 70)

    print(
        "Qdrant selected scope: PASS"
    )

    print(
        "Qdrant isolation:      PASS"
    )

    print(
        "Neo4j selected scope:  PASS"
    )

    print(
        "Neo4j isolation:       PASS"
    )


if __name__ == "__main__":
    main()