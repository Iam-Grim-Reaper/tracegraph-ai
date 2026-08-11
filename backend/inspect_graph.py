from app.graph.store import Neo4jGraphStore


def main():
    store = Neo4jGraphStore()

    try:
        store.verify_connectivity()

        print("\nALL SEMANTIC RELATIONSHIPS")
        print("=" * 80)

        relationships = store.query(
            """
            MATCH (source:Entity)-[r]->(target:Entity)

            WHERE NOT type(r) IN [
                'MENTIONS',
                'CONTAINS'
            ]

            RETURN
                source.entity_id AS source_id,
                source.name AS source_name,
                source.entity_type AS source_type,

                type(r) AS relationship_type,

                target.entity_id AS target_id,
                target.name AS target_name,
                target.entity_type AS target_type,

                r.confidence AS confidence,
                r.source_chunk_id AS source_chunk_id,
                r.page_number AS page_number,
                r.evidence_text AS evidence_text

            ORDER BY
                relationship_type,
                source_name,
                target_name
            """
        )

        print(
            f"Semantic relationship count: "
            f"{len(relationships)}"
        )

        for row in relationships:
            print("\n")
            print(
                f"{row['source_name']} "
                f"[{row['source_type']}]"
            )

            print(
                f"  -[{row['relationship_type']}]->"
            )

            print(
                f"{row['target_name']} "
                f"[{row['target_type']}]"
            )

            print(
                f"Source ID: "
                f"{row['source_id']}"
            )

            print(
                f"Target ID: "
                f"{row['target_id']}"
            )

            print(
                f"Page: "
                f"{row['page_number']}"
            )

            print(
                f"Evidence: "
                f"{row['evidence_text']}"
            )

        print("\n\nCONVNEXT-SMALL NODES")
        print("=" * 80)

        convnext = store.query(
            """
            MATCH (e:Entity)
            WHERE e.normalized_name =
                'convnext small'

            OPTIONAL MATCH (e)-[r]-(neighbor:Entity)

            RETURN
                e.entity_id AS entity_id,
                e.name AS entity_name,
                e.entity_type AS entity_type,
                type(r) AS relationship_type,
                neighbor.name AS neighbor_name,
                neighbor.entity_type
                    AS neighbor_type
            """
        )

        for row in convnext:
            print(row)

        print("\n\nGRAD-CAM NODES")
        print("=" * 80)

        grad_cam = store.query(
            """
            MATCH (e:Entity)

            WHERE
                e.normalized_name =
                    'grad cam'
                OR any(
                    alias IN coalesce(
                        e.aliases,
                        []
                    )
                    WHERE
                        toLower(alias) =
                        'grad-cam'
                )

            OPTIONAL MATCH (e)-[r]-(neighbor:Entity)

            RETURN
                e.entity_id AS entity_id,
                e.name AS entity_name,
                e.normalized_name
                    AS normalized_name,
                e.entity_type AS entity_type,
                e.aliases AS aliases,
                type(r) AS relationship_type,
                neighbor.name AS neighbor_name,
                neighbor.entity_type
                    AS neighbor_type
            """
        )

        for row in grad_cam:
            print(row)

    finally:
        store.close()


if __name__ == "__main__":
    main()