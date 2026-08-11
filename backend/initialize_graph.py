from app.graph.schema import (
    ALLOWED_ENTITY_TYPES,
    ALLOWED_RELATIONSHIP_TYPES,
    initialize_graph_schema,
)
from app.graph.store import Neo4jGraphStore


def main():
    store = Neo4jGraphStore()

    try:
        store.verify_connectivity()

        initialize_graph_schema(
            store=store
        )

        print("\nAllowed entity types:")
        for entity_type in sorted(
            ALLOWED_ENTITY_TYPES
        ):
            print(f"  - {entity_type}")

        print("\nAllowed relationship types:")
        for relationship_type in sorted(
            ALLOWED_RELATIONSHIP_TYPES
        ):
            print(
                f"  - {relationship_type}"
            )

        constraints = store.query(
            """
            SHOW CONSTRAINTS
            YIELD name, type
            RETURN name, type
            ORDER BY name
            """
        )

        indexes = store.query(
            """
            SHOW INDEXES
            YIELD name, type
            RETURN name, type
            ORDER BY name
            """
        )

        print("\nConstraints:")
        for item in constraints:
            print(item)

        print("\nIndexes:")
        for item in indexes:
            print(item)

    finally:
        store.close()


if __name__ == "__main__":
    main()