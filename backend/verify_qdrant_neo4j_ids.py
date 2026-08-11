from app.graph.store import (
    Neo4jGraphStore,
)
from app.retrieval.hybrid_store import (
    HybridStore,
)


def get_qdrant_ids(
    store: HybridStore,
) -> set[str]:
    ids: set[str] = set()

    offset = None

    while True:
        points, offset = (
            store.client.scroll(
                collection_name=(
                    store.collection_name
                ),
                limit=100,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
        )

        for point in points:
            ids.add(
                str(point.id)
            )

        if offset is None:
            break

    return ids


def get_neo4j_ids(
    store: Neo4jGraphStore,
) -> set[str]:
    rows = store.query(
        """
        MATCH (c:Chunk)

        RETURN
            c.chunk_id AS chunk_id
        """
    )

    return {
        str(
            row["chunk_id"]
        )
        for row in rows
    }


def main():
    hybrid_store = (
        HybridStore()
    )

    graph_store = (
        Neo4jGraphStore()
    )

    try:
        graph_store\
            .verify_connectivity()

        qdrant_ids = (
            get_qdrant_ids(
                hybrid_store
            )
        )

        neo4j_ids = (
            get_neo4j_ids(
                graph_store
            )
        )

        overlap = (
            qdrant_ids
            & neo4j_ids
        )

        qdrant_only = (
            qdrant_ids
            - neo4j_ids
        )

        neo4j_only = (
            neo4j_ids
            - qdrant_ids
        )

        print("=" * 70)

        print(
            "QDRANT / NEO4J "
            "IDENTITY CHECK"
        )

        print("=" * 70)

        print(
            f"\nQdrant chunks: "
            f"{len(qdrant_ids)}"
        )

        print(
            f"Neo4j chunks: "
            f"{len(neo4j_ids)}"
        )

        print(
            f"Matching chunk IDs: "
            f"{len(overlap)}"
        )

        denominator = max(
            len(qdrant_ids),
            len(neo4j_ids),
            1,
        )

        overlap_percent = (
            len(overlap)
            / denominator
            * 100
        )

        print(
            f"Overlap: "
            f"{overlap_percent:.1f}%"
        )

        if qdrant_only:
            print(
                "\nQdrant-only IDs:"
            )

            for chunk_id in sorted(
                qdrant_only
            ):
                print(
                    f"  {chunk_id}"
                )

        if neo4j_only:
            print(
                "\nNeo4j-only IDs:"
            )

            for chunk_id in sorted(
                neo4j_only
            ):
                print(
                    f"  {chunk_id}"
                )

        success = (
            qdrant_ids
            == neo4j_ids
            and len(qdrant_ids)
            == 30
        )

        print(
            "\nIDENTITY CONTRACT VALID:",
            success,
        )

        if not success:
            raise RuntimeError(
                "Qdrant and Neo4j "
                "chunk identities do "
                "not match."
            )

    finally:
        graph_store.close()


if __name__ == "__main__":
    main()