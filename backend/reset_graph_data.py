from app.graph.store import Neo4jGraphStore


def get_counts(
    store: Neo4jGraphStore,
) -> dict:
    documents = store.query(
        """
        MATCH (d:Document)
        RETURN count(d) AS count
        """
    )[0]["count"]

    chunks = store.query(
        """
        MATCH (c:Chunk)
        RETURN count(c) AS count
        """
    )[0]["count"]

    entities = store.query(
        """
        MATCH (e:Entity)
        RETURN count(e) AS count
        """
    )[0]["count"]

    relationships = store.query(
        """
        MATCH ()-[r]->()
        RETURN count(r) AS count
        """
    )[0]["count"]

    return {
        "documents": documents,
        "chunks": chunks,
        "entities": entities,
        "relationships": relationships,
    }


def main():
    store = Neo4jGraphStore()

    try:
        store.verify_connectivity()

        print("=" * 70)
        print("TRACEGRAPH GRAPH RESET")
        print("=" * 70)

        before = get_counts(
            store
        )

        print("\nBefore reset:")
        print(before)

        # Delete only TraceGraph application
        # nodes and their relationships.
        #
        # Constraints and indexes remain.
        store.query(
            """
            MATCH (n)

            WHERE
                n:Document
                OR n:Chunk
                OR n:Entity

            DETACH DELETE n
            """
        )

        after = get_counts(
            store
        )

        print("\nAfter reset:")
        print(after)

        print("\nConstraints:")
        constraints = store.query(
            """
            SHOW CONSTRAINTS
            YIELD name, type
            RETURN name, type
            ORDER BY name
            """
        )

        for row in constraints:
            print(row)

        print("\nIndexes:")
        indexes = store.query(
            """
            SHOW INDEXES
            YIELD name, type
            RETURN name, type
            ORDER BY name
            """
        )

        for row in indexes:
            print(row)

    finally:
        store.close()


if __name__ == "__main__":
    main()