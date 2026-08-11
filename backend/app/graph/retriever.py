from dataclasses import dataclass

from app.graph.normalizer import (
    EntityNormalizer,
)
from app.graph.store import (
    Neo4jGraphStore,
)


@dataclass
class GraphEntityMatch:
    entity_id: str
    name: str
    normalized_name: str
    entity_type: str
    aliases: list[str]


class GraphRetriever:
    def __init__(
        self,
        store: Neo4jGraphStore,
    ):
        self.store = store
        self.normalizer = EntityNormalizer()

    def find_entities(
        self,
        name: str,
        limit: int = 10,
    ) -> list[GraphEntityMatch]:
        if not name.strip():
            return []

        normalized_name = (
            self.normalizer.normalize_name(
                name
            )
        )

        rows = self.store.query(
            """
            MATCH (e:Entity)

            WHERE
                e.normalized_name =
                    $normalized_name

                OR any(
                    alias IN coalesce(
                        e.aliases,
                        []
                    )
                    WHERE
                        toLower(
                            replace(
                                alias,
                                '-',
                                ' '
                            )
                        )
                        =
                        $normalized_name
                )

            RETURN
                e.entity_id AS entity_id,
                e.name AS name,
                e.normalized_name
                    AS normalized_name,
                e.entity_type
                    AS entity_type,
                coalesce(
                    e.aliases,
                    []
                ) AS aliases

            ORDER BY
                CASE
                    WHEN e.normalized_name =
                        $normalized_name
                    THEN 0
                    ELSE 1
                END,
                e.name

            LIMIT $limit
            """,
            {
                "normalized_name": (
                    normalized_name
                ),
                "limit": limit,
            },
        )

        return [
            GraphEntityMatch(
                entity_id=row["entity_id"],
                name=row["name"],
                normalized_name=(
                    row["normalized_name"]
                ),
                entity_type=(
                    row["entity_type"]
                ),
                aliases=row["aliases"],
            )
            for row in rows
        ]

    def get_neighbors(
        self,
        entity_id: str,
        limit: int = 20,
    ) -> list[dict]:
        return self.store.query(
            """
            MATCH (
                focus:Entity {
                    entity_id: $entity_id
                }
            )-[r]-(neighbor:Entity)

            WHERE NOT type(r) IN [
                'MENTIONS',
                'CONTAINS'
            ]

            WITH
                focus,
                neighbor,
                r,
                startNode(r) AS source,
                endNode(r) AS target

            OPTIONAL MATCH (
                chunk:Chunk {
                    chunk_id:
                        r.source_chunk_id
                }
            )

            RETURN
                source.entity_id
                    AS source_entity_id,
                source.name
                    AS source_name,
                source.entity_type
                    AS source_type,

                type(r)
                    AS relationship_type,

                target.entity_id
                    AS target_entity_id,
                target.name
                    AS target_name,
                target.entity_type
                    AS target_type,

                r.confidence
                    AS confidence,
                r.evidence_text
                    AS evidence_text,
                r.page_number
                    AS page_number,
                r.source_chunk_id
                    AS source_chunk_id,
                r.source_document_id
                    AS source_document_id,

                chunk.text
                    AS source_text

            LIMIT $limit
            """,
            {
                "entity_id": entity_id,
                "limit": limit,
            },
        )

    def get_two_hop_paths(
        self,
        entity_id: str,
        limit: int = 20,
    ) -> list[dict]:
        return self.store.query(
            """
            MATCH path = (
                start:Entity {
                    entity_id: $entity_id
                }
            )-[rels*1..2]-(
                target:Entity
            )

            WHERE
                start <> target

                AND all(
                    relationship
                    IN relationships(path)
                    WHERE
                        NOT type(relationship)
                        IN [
                            'MENTIONS',
                            'CONTAINS'
                        ]
                )

            RETURN
                [
                    node IN nodes(path) |
                    {
                        entity_id:
                            node.entity_id,

                        name:
                            node.name,

                        entity_type:
                            node.entity_type
                    }
                ] AS entities,

                [
                    relationship
                    IN relationships(path) |
                    {
                        relationship_type:
                            type(
                                relationship
                            ),

                        source_entity_id:
                            startNode(
                                relationship
                            ).entity_id,

                        source_name:
                            startNode(
                                relationship
                            ).name,

                        target_entity_id:
                            endNode(
                                relationship
                            ).entity_id,

                        target_name:
                            endNode(
                                relationship
                            ).name,

                        confidence:
                            relationship
                            .confidence,

                        evidence_text:
                            relationship
                            .evidence_text,

                        source_chunk_id:
                            relationship
                            .source_chunk_id,

                        page_number:
                            relationship
                            .page_number
                    }
                ] AS relationship_steps,

                length(path) AS hops

            ORDER BY hops

            LIMIT $limit
            """,
            {
                "entity_id": entity_id,
                "limit": limit,
            },
        )