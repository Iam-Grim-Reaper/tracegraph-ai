from app.graph.store import Neo4jGraphStore


def main():
    store = Neo4jGraphStore()

    try:
        store.verify_connectivity()

        print("=" * 90)
        print("TRACEGRAPH FULL GRAPH QUALITY REPORT")
        print("=" * 90)

        # -------------------------------------------------
        # 1. Basic graph statistics
        # -------------------------------------------------
        counts = store.query(
            """
            MATCH (d:Document)
            WITH count(d) AS documents

            MATCH (c:Chunk)
            WITH
                documents,
                count(c) AS chunks

            MATCH (e:Entity)
            WITH
                documents,
                chunks,
                count(e) AS entities

            MATCH ()-[r]->()

            RETURN
                documents,
                chunks,
                entities,
                count(r) AS relationships
            """
        )

        print("\nGRAPH COUNTS")
        print("-" * 90)

        print(counts)

        # -------------------------------------------------
        # 2. Every semantic relationship
        # -------------------------------------------------
        semantic_relationships = store.query(
            """
            MATCH (source:Entity)-[r]->(target:Entity)

            WHERE NOT type(r) IN [
                'MENTIONS',
                'CONTAINS'
            ]

            RETURN
                source.name AS source_name,
                source.entity_type AS source_type,

                type(r) AS relationship_type,

                target.name AS target_name,
                target.entity_type AS target_type,

                r.confidence AS confidence,
                r.page_number AS page_number,
                r.source_chunk_id AS source_chunk_id,
                r.evidence_text AS evidence_text

            ORDER BY
                relationship_type,
                source_name,
                target_name
            """
        )

        print("\nSEMANTIC RELATIONSHIPS")
        print("-" * 90)

        print(
            f"Count: "
            f"{len(semantic_relationships)}"
        )

        for index, row in enumerate(
            semantic_relationships,
            start=1,
        ):
            print()

            print(
                f"{index}. "
                f"{row['source_name']} "
                f"[{row['source_type']}]"
            )

            print(
                f"   -[{row['relationship_type']}]->"
            )

            print(
                f"   {row['target_name']} "
                f"[{row['target_type']}]"
            )

            print(
                f"   Confidence: "
                f"{row['confidence']}"
            )

            print(
                f"   Page: "
                f"{row['page_number']}"
            )

            print(
                f"   Chunk: "
                f"{row['source_chunk_id']}"
            )

            print(
                f"   Evidence: "
                f"{row['evidence_text']}"
            )

        # -------------------------------------------------
        # 3. Specifically inspect dataset claims
        # -------------------------------------------------
        dataset_claims = store.query(
            """
            MATCH (source:Entity)-[r]->(target:Entity)

            WHERE type(r) IN [
                'TRAINED_ON',
                'EVALUATED_ON'
            ]

            RETURN
                source.name AS source_name,
                source.entity_type AS source_type,
                type(r) AS relationship_type,
                target.name AS target_name,
                target.entity_type AS target_type,
                r.confidence AS confidence,
                r.page_number AS page_number,
                r.evidence_text AS evidence_text

            ORDER BY
                relationship_type
            """
        )

        print("\nTRAINING / EVALUATION CLAIMS")
        print("-" * 90)

        if not dataset_claims:
            print(
                "No TRAINED_ON or "
                "EVALUATED_ON relationships."
            )

        for row in dataset_claims:
            print()

            print(
                f"{row['source_name']} "
                f"-[{row['relationship_type']}]-> "
                f"{row['target_name']}"
            )

            print(
                f"Source type: "
                f"{row['source_type']}"
            )

            print(
                f"Target type: "
                f"{row['target_type']}"
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

        # -------------------------------------------------
        # 4. Highest semantic-degree entities
        # -------------------------------------------------
        top_entities = store.query(
            """
            MATCH (e:Entity)-[r]-(neighbor:Entity)

            WHERE NOT type(r) IN [
                'MENTIONS',
                'CONTAINS'
            ]

            RETURN
                e.name AS name,
                e.entity_type AS entity_type,
                count(r) AS semantic_degree

            ORDER BY
                semantic_degree DESC,
                name

            LIMIT 15
            """
        )

        print("\nTOP CONNECTED ENTITIES")
        print("-" * 90)

        for row in top_entities:
            print(
                f"{row['name']} "
                f"[{row['entity_type']}] "
                f"degree={row['semantic_degree']}"
            )

        # -------------------------------------------------
        # 5. Duplicate normalized identities
        # -------------------------------------------------
        duplicates = store.query(
            """
            MATCH (e:Entity)

            WITH
                e.entity_type AS entity_type,
                e.normalized_name AS normalized_name,
                collect(e) AS entities

            WHERE size(entities) > 1

            RETURN
                entity_type,
                normalized_name,

                [
                    entity IN entities |
                    {
                        entity_id:
                            entity.entity_id,

                        name:
                            entity.name,

                        aliases:
                            coalesce(
                                entity.aliases,
                                []
                            )
                    }
                ] AS duplicates
            """
        )

        print("\nDUPLICATE NORMALIZED IDENTITIES")
        print("-" * 90)

        if not duplicates:
            print(
                "No duplicate normalized "
                "entities found."
            )

        for row in duplicates:
            print()

            print(
                f"Type: "
                f"{row['entity_type']}"
            )

            print(
                f"Normalized: "
                f"{row['normalized_name']}"
            )

            print(
                f"Nodes: "
                f"{row['duplicates']}"
            )

        # -------------------------------------------------
        # 6. Entities with semantic relationships
        # -------------------------------------------------
        connected = store.query(
            """
            MATCH (e:Entity)

            OPTIONAL MATCH (
                e
            )-[r]-(
                neighbor:Entity
            )

            WHERE NOT type(r) IN [
                'MENTIONS',
                'CONTAINS'
            ]

            WITH
                e,
                count(r) AS degree

            RETURN
                count(e) AS total_entities,

                sum(
                    CASE
                        WHEN degree > 0
                        THEN 1
                        ELSE 0
                    END
                ) AS semantically_connected
            """
        )

        print("\nSEMANTIC CONNECTIVITY")
        print("-" * 90)

        print(connected)

    finally:
        store.close()


if __name__ == "__main__":
    main()