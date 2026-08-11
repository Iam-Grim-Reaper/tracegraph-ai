from app.graph.store import Neo4jGraphStore


def main():
    store = Neo4jGraphStore()

    try:
        print("Connecting to Neo4j...")

        store.verify_connectivity()

        print("Neo4j connection established.")

        result = store.query(
            """
            RETURN
                1 AS ok,
                'TraceGraph AI' AS project
            """
        )

        print("Test query result:")
        print(result)

    finally:
        store.close()


if __name__ == "__main__":
    main()