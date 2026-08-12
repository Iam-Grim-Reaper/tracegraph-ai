from app.graph.store import Neo4jGraphStore


def main():
    store = Neo4jGraphStore()

    try:
        store.verify_connectivity()

        print("=" * 70)
        print("GRAPH STATE")
        print("=" * 70)

        document_count = store.query(
            """
            MATCH (d:Document)
            RETURN count(d) AS count
            """
        )[0]["count"]

        chunk_count = store.query(
            """
            MATCH (c:Chunk)
            RETURN count(c) AS count
            """
        )[0]["count"]

        entity_count = store.query(
            """
            MATCH (e:Entity)
            RETURN count(e) AS count
            """
        )[0]["count"]

        semantic_count = store.query(
            """
            MATCH ()-[r]->()

            WHERE NOT type(r) IN [
                'MENTIONS',
                'CONTAINS'
            ]

            RETURN count(r) AS count
            """
        )[0]["count"]

        print(
            f"Documents: {document_count}"
        )

        print(
            f"Chunks: {chunk_count}"
        )

        print(
            f"Entities: {entity_count}"
        )

        print(
            "Semantic relationships: "
            f"{semantic_count}"
        )

        print("\n" + "=" * 70)
        print("GRAD-CAM GLOBAL RESOLUTION")
        print("=" * 70)

        grad_cam_entities = store.query(
            """
            MATCH (e:Entity)

            WHERE
                e.entity_type = 'Method'

                AND (
                    e.normalized_name =
                        'grad cam'

                    OR 'grad cam' IN
                        coalesce(
                            e.normalized_aliases,
                            []
                        )
                )

            RETURN DISTINCT
                e.entity_id AS entity_id,
                e.name AS name,
                e.normalized_name
                    AS normalized_name,
                coalesce(
                    e.aliases,
                    []
                ) AS aliases,
                coalesce(
                    e.normalized_aliases,
                    []
                ) AS normalized_aliases
            """
        )

        print(
            "Grad-CAM canonical entities:",
            len(grad_cam_entities),
        )

        for entity in grad_cam_entities:
            print()

            print(
                f"ID: {entity['entity_id']}"
            )

            print(
                f"Name: {entity['name']}"
            )

            print(
                "Normalized name: "
                f"{entity['normalized_name']}"
            )

            print(
                f"Aliases: "
                f"{entity['aliases']}"
            )

            print(
                "Normalized aliases: "
                f"{entity['normalized_aliases']}"
            )

        print("\n" + "=" * 70)
        print("GRAD-CAM RELATIONSHIPS")
        print("=" * 70)

        relationships = store.query(
            """
            MATCH (grad:Entity)-[r]-(neighbor:Entity)

            WHERE
                grad.entity_type = 'Method'

                AND (
                    grad.normalized_name =
                        'grad cam'

                    OR 'grad cam' IN
                        coalesce(
                            grad.normalized_aliases,
                            []
                        )
                )

                AND NOT type(r) IN [
                    'MENTIONS',
                    'CONTAINS'
                ]

            WITH
                grad,
                neighbor,
                r,
                startNode(r) AS source,
                endNode(r) AS target

            RETURN
                source.name AS source_name,
                type(r) AS relationship_type,
                target.name AS target_name,
                r.confidence AS confidence,
                r.page_number AS page_number,
                r.evidence_text AS evidence_text

            ORDER BY page_number
            """
        )

        print(
            "Relationship count:",
            len(relationships),
        )

        for row in relationships:
            print()

            print(
                f"{row['source_name']} "
                f"-[{row['relationship_type']}]-> "
                f"{row['target_name']}"
            )

            print(
                f"Confidence: "
                f"{row['confidence']}"
            )

            print(
                f"Page: "
                f"{row['page_number']}"
            )

            print(
                f"Evidence: "
                f"{row['evidence_text']}"
            )

    finally:
        store.close()


if __name__ == "__main__":
    main()
