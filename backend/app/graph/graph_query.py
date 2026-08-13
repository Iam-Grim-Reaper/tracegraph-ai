from dataclasses import dataclass

from app.graph.normalizer import (
    EntityNormalizer,
)
from app.graph.store import (
    Neo4jGraphStore,
)


@dataclass
class LinkedGraphEntity:
    entity_id: str
    name: str
    entity_type: str
    aliases: list[str]
    match_score: int


@dataclass
class GraphFact:
    source_entity_id: str
    source_name: str
    source_type: str

    relationship_type: str

    target_entity_id: str
    target_name: str
    target_type: str

    confidence: float | None
    evidence_text: str | None

    source_document_id: str | None
    source_chunk_id: str | None
    page_number: int | None

    source_text: str | None
    source_locator_type: str | None = None
    source_locator_label: str | None = None


@dataclass
class GraphQueryResult:
    query: str

    linked_entities: list[
        LinkedGraphEntity
    ]

    facts: list[
        GraphFact
    ]


class GraphQueryRetriever:
    def __init__(
        self,
        store: Neo4jGraphStore,
    ):
        self.store = store

        self.normalizer = (
            EntityNormalizer()
        )

    def link_entities(
        self,
        query: str,
        limit: int = 5,
        document_ids: (
            list[str] | None
        ) = None,
    ) -> list[LinkedGraphEntity]:
        if not query.strip():
            return []

        normalized_query = (
            self.normalizer
            .normalize_name(
                query
            )
        )

        scoped_document_ids = (
            document_ids
            if document_ids
            else None
        )

        rows = self.store.query(
            """
            MATCH (e:Entity)

            WITH
                e,
                coalesce(
                    e.normalized_aliases,
                    []
                ) AS normalized_aliases

            WHERE
                (
                    $normalized_query
                    CONTAINS
                    e.normalized_name

                    OR any(
                        alias
                        IN normalized_aliases

                        WHERE
                            $normalized_query
                            CONTAINS alias
                    )
                )

                AND (
                    $document_ids IS NULL

                    OR EXISTS {
                        MATCH (
                            scope_chunk:Chunk
                        )-[:MENTIONS]->(
                            e
                        )

                        WHERE
                            scope_chunk.document_id
                            IN $document_ids
                    }
                )

            WITH
                e,

                CASE
                    WHEN
                        $normalized_query =
                        e.normalized_name

                    THEN 10000

                    ELSE size(
                        e.normalized_name
                    )
                END AS match_score

            RETURN
                e.entity_id
                    AS entity_id,

                e.name
                    AS name,

                e.entity_type
                    AS entity_type,

                coalesce(
                    e.aliases,
                    []
                ) AS aliases,

                match_score

            ORDER BY
                match_score DESC,
                name

            LIMIT $limit
            """,
            {
                "normalized_query": (
                    normalized_query
                ),

                "document_ids": (
                    scoped_document_ids
                ),

                "limit": limit,
            },
        )

        return [
            LinkedGraphEntity(
                entity_id=(
                    row["entity_id"]
                ),

                name=(
                    row["name"]
                ),

                entity_type=(
                    row["entity_type"]
                ),

                aliases=(
                    row["aliases"]
                ),

                match_score=(
                    row["match_score"]
                ),
            )

            for row in rows
        ]

    def retrieve(
        self,
        query: str,
        max_seed_entities: int = 5,
        max_facts: int = 30,
        document_ids: (
            list[str] | None
        ) = None,
        max_path_depth: int = 2,
    ) -> GraphQueryResult:
        if max_path_depth not in {1, 2}:
            raise ValueError(
                "max_path_depth must be 1 or 2"
            )
        linked_entities = (
            self.link_entities(
                query=query,

                limit=(
                    max_seed_entities
                ),

                document_ids=(
                    document_ids
                ),
            )
        )

        if not linked_entities:
            return GraphQueryResult(
                query=query,
                linked_entities=[],
                facts=[],
            )

        facts: list[
            GraphFact
        ] = []

        seen: set[
            tuple[
                str,
                str,
                str,
                str | None,
            ]
        ] = set()

        for entity in linked_entities:
            rows = (
                self._retrieve_facts(
                    entity_id=(
                        entity.entity_id
                    ),

                    limit=max_facts,

                    document_ids=(
                        document_ids
                    ),
                    max_path_depth=(
                        max_path_depth
                    ),
                )
            )

            for row in rows:
                key = (
                    row[
                        "source_entity_id"
                    ],

                    row[
                        "relationship_type"
                    ],

                    row[
                        "target_entity_id"
                    ],

                    row[
                        "source_chunk_id"
                    ],
                )

                if key in seen:
                    continue

                seen.add(
                    key
                )

                facts.append(
                    GraphFact(
                        source_entity_id=(
                            row[
                                "source_entity_id"
                            ]
                        ),

                        source_name=(
                            row[
                                "source_name"
                            ]
                        ),

                        source_type=(
                            row[
                                "source_type"
                            ]
                        ),

                        relationship_type=(
                            row[
                                "relationship_type"
                            ]
                        ),

                        target_entity_id=(
                            row[
                                "target_entity_id"
                            ]
                        ),

                        target_name=(
                            row[
                                "target_name"
                            ]
                        ),

                        target_type=(
                            row[
                                "target_type"
                            ]
                        ),

                        confidence=(
                            row["confidence"]
                        ),

                        evidence_text=(
                            row[
                                "evidence_text"
                            ]
                        ),

                        source_document_id=(
                            row[
                                "source_document_id"
                            ]
                        ),

                        source_chunk_id=(
                            row[
                                "source_chunk_id"
                            ]
                        ),

                        page_number=(
                            row[
                                "page_number"
                            ]
                        ),

                        source_text=(
                            row[
                                "source_text"
                            ]
                        ),
                        source_locator_type=row.get("source_locator_type"),
                        source_locator_label=row.get("source_locator_label"),
                    )
                )

                if (
                    len(facts)
                    >= max_facts
                ):
                    break

            if (
                len(facts)
                >= max_facts
            ):
                break

        return GraphQueryResult(
            query=query,

            linked_entities=(
                linked_entities
            ),

            facts=facts,
        )

    def _retrieve_facts(
        self,
        entity_id: str,
        limit: int,
        document_ids: (
            list[str] | None
        ) = None,
        max_path_depth: int = 2,
    ) -> list[dict]:
        scoped_document_ids = (
            document_ids
            if document_ids
            else None
        )

        cypher = """
            MATCH path = (
                seed:Entity {
                    entity_id:
                        $entity_id
                }
            )-[rels*1..__MAX_PATH_DEPTH__]-(
                other:Entity
            )

            WHERE
                seed <> other

                AND all(
                    relationship
                    IN relationships(path)

                    WHERE
                        NOT type(
                            relationship
                        )
                        IN [
                            'CONTAINS',
                            'MENTIONS'
                        ]

                        AND (
                            $document_ids
                                IS NULL

                            OR relationship
                                .source_document_id
                                IN $document_ids
                        )
                )

            UNWIND
                relationships(path)
                AS relationship

            WITH DISTINCT
                relationship

            WITH
                relationship,

                startNode(
                    relationship
                ) AS source,

                endNode(
                    relationship
                ) AS target

            OPTIONAL MATCH (
                chunk:Chunk {
                    chunk_id:
                        relationship
                        .source_chunk_id
                }
            )

            RETURN
                source.entity_id
                    AS source_entity_id,

                source.name
                    AS source_name,

                source.entity_type
                    AS source_type,

                type(
                    relationship
                ) AS relationship_type,

                target.entity_id
                    AS target_entity_id,

                target.name
                    AS target_name,

                target.entity_type
                    AS target_type,

                relationship.confidence
                    AS confidence,

                relationship.evidence_text
                    AS evidence_text,

                relationship
                    .source_document_id
                    AS source_document_id,

                relationship
                    .source_chunk_id
                    AS source_chunk_id,

                relationship.page_number
                    AS page_number,

                chunk.text
                    AS source_text,

                chunk.source_locator_type
                    AS source_locator_type,

                chunk.source_locator_label
                    AS source_locator_label

            LIMIT $limit
            """.replace(
                "__MAX_PATH_DEPTH__",
                str(max_path_depth),
            )

        return self.store.query(
            cypher,
            {
                "entity_id": (
                    entity_id
                ),

                "document_ids": (
                    scoped_document_ids
                ),

                "limit": limit,
            },
        )

    def retrieve_by_chunk_ids(
        self,
        query: str,
        chunk_ids: list[str],
        document_ids: list[str] | None = None,
        max_facts: int = 20,
    ) -> GraphQueryResult:
        """Retrieve bounded semantic facts owned by evidence chunks."""
        if not chunk_ids:
            return GraphQueryResult(query, [], [])

        rows = self.store.query(
            """
            MATCH (source:Entity)-[relationship]->(target:Entity)
            WHERE relationship.source_chunk_id IN $chunk_ids
              AND NOT type(relationship) IN ['CONTAINS', 'MENTIONS']
              AND (
                $document_ids IS NULL
                OR relationship.source_document_id IN $document_ids
              )
            OPTIONAL MATCH (chunk:Chunk {
                chunk_id: relationship.source_chunk_id
            })
            RETURN
                source.entity_id AS source_entity_id,
                source.name AS source_name,
                source.entity_type AS source_type,
                type(relationship) AS relationship_type,
                target.entity_id AS target_entity_id,
                target.name AS target_name,
                target.entity_type AS target_type,
                relationship.confidence AS confidence,
                relationship.evidence_text AS evidence_text,
                relationship.source_document_id AS source_document_id,
                relationship.source_chunk_id AS source_chunk_id,
                relationship.page_number AS page_number,
                chunk.text AS source_text,
                chunk.source_locator_type AS source_locator_type,
                chunk.source_locator_label AS source_locator_label
            LIMIT $limit
            """,
            {
                "chunk_ids": list(dict.fromkeys(chunk_ids)),
                "document_ids": document_ids if document_ids else None,
                "limit": max_facts,
            },
        )

        facts = [
            GraphFact(**row)
            for row in rows
        ]
        return GraphQueryResult(query, [], facts)

    @staticmethod
    def format_context(
        result: GraphQueryResult,
        max_facts: int = 12,
    ) -> str:
        if not result.facts:
            return (
                "No graph evidence found."
            )

        sections: list[str] = []

        for index, fact in enumerate(
            result.facts[
                :max_facts
            ],
            start=1,
        ):
            section = (
                f"[Graph Evidence {index}]\n"
                f"{fact.source_name} "
                f"-[{fact.relationship_type}]-> "
                f"{fact.target_name}\n"
                f"Page: "
                f"{fact.page_number}\n"
                f"Chunk: "
                f"{fact.source_chunk_id}\n"
                f"Confidence: "
                f"{fact.confidence}\n"
                f"Evidence: "
                f"{fact.evidence_text}"
            )

            sections.append(
                section
            )

        return "\n\n".join(
            sections
        )
