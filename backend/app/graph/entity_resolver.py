from app.graph.models import (
    GraphEntity,
    GraphRelationship,
)
from app.graph.normalizer import (
    EntityNormalizer,
)
from app.graph.postprocessor import (
    ProcessedChunkGraph,
)
from app.graph.store import (
    Neo4jGraphStore,
)


class GlobalEntityResolver:
    def __init__(
        self,
        store: Neo4jGraphStore,
    ):
        self.store = store
        self.normalizer = EntityNormalizer()

    def resolve(
        self,
        graph: ProcessedChunkGraph,
    ) -> ProcessedChunkGraph:
        """
        Resolve chunk-local entities against
        entities that already exist globally
        in Neo4j.
        """

        id_map: dict[str, str] = {}

        resolved_entities: dict[
            str,
            GraphEntity,
        ] = {}

        for entity in graph.entities:
            resolved = self._resolve_entity(
                entity
            )

            id_map[
                entity.entity_id
            ] = resolved.entity_id

            existing = resolved_entities.get(
                resolved.entity_id
            )

            if existing is None:
                resolved_entities[
                    resolved.entity_id
                ] = resolved

            else:
                resolved_entities[
                    resolved.entity_id
                ] = self._merge_entities(
                    existing,
                    resolved,
                )

        resolved_relationships: list[
            GraphRelationship
        ] = []

        seen_relationships: set[
            tuple[str, str, str, str]
        ] = set()

        for relationship in graph.relationships:
            source_id = id_map.get(
                relationship.source_entity_id,
                relationship.source_entity_id,
            )

            target_id = id_map.get(
                relationship.target_entity_id,
                relationship.target_entity_id,
            )

            # Alias resolution can theoretically
            # cause both ends of an extracted
            # relation to become the same entity.
            # Do not create self-loop assertions.
            if source_id == target_id:
                continue

            relationship_key = (
                source_id,
                target_id,
                relationship
                .relationship_type
                .value,
                relationship.source_chunk_id,
            )

            if (
                relationship_key
                in seen_relationships
            ):
                continue

            seen_relationships.add(
                relationship_key
            )

            resolved_relationships.append(
                GraphRelationship(
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                    relationship_type=(
                        relationship
                        .relationship_type
                    ),
                    confidence=(
                        relationship.confidence
                    ),
                    evidence_text=(
                        relationship.evidence_text
                    ),
                    source_document_id=(
                        relationship
                        .source_document_id
                    ),
                    source_chunk_id=(
                        relationship
                        .source_chunk_id
                    ),
                    page_number=(
                        relationship.page_number
                    ),
                )
            )

        return ProcessedChunkGraph(
            entities=list(
                resolved_entities.values()
            ),
            relationships=(
                resolved_relationships
            ),
            rejected_relationships=(
                graph.rejected_relationships
            ),
        )

    def _resolve_entity(
        self,
        entity: GraphEntity,
    ) -> GraphEntity:
        normalized_aliases = sorted(
            {
                self.normalizer.normalize_name(
                    alias
                )
                for alias in entity.aliases
                if alias.strip()
            }
        )

        rows = self.store.query(
            """
            MATCH (e:Entity)

            WHERE
                e.entity_type =
                    $entity_type

                AND (
                    e.normalized_name =
                        $normalized_name

                    OR $normalized_name IN
                        coalesce(
                            e.normalized_aliases,
                            []
                        )

                    OR any(
                        candidate_alias
                        IN $normalized_aliases

                        WHERE
                            candidate_alias =
                                e.normalized_name
                    )

                    OR any(
                        candidate_alias
                        IN $normalized_aliases

                        WHERE candidate_alias IN
                            coalesce(
                                e.normalized_aliases,
                                []
                            )
                    )

                    OR toLower(e.name) =
                        toLower($raw_name)

                    OR any(
                        existing_alias
                        IN coalesce(
                            e.aliases,
                            []
                        )

                        WHERE
                            toLower(
                                existing_alias
                            )
                            =
                            toLower(
                                $raw_name
                            )
                    )

                    OR any(
                        candidate_alias
                        IN $raw_aliases

                        WHERE
                            toLower(
                                candidate_alias
                            )
                            =
                            toLower(
                                e.name
                            )
                    )

                    OR any(
                        candidate_alias
                        IN $raw_aliases

                        WHERE any(
                            existing_alias
                            IN coalesce(
                                e.aliases,
                                []
                            )

                            WHERE
                                toLower(
                                    candidate_alias
                                )
                                =
                                toLower(
                                    existing_alias
                                )
                        )
                    )
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
                ) AS aliases,
                coalesce(
                    e.normalized_aliases,
                    []
                ) AS normalized_aliases

            LIMIT 10
            """,
            {
                "entity_type": (
                    entity.entity_type.value
                ),
                "normalized_name": (
                    entity.normalized_name
                ),
                "normalized_aliases": (
                    normalized_aliases
                ),
                "raw_name": entity.name,
                "raw_aliases": (
                    entity.aliases
                ),
            },
        )

        if not rows:
            return entity

        best_match = self._select_best_match(
            entity=entity,
            rows=rows,
        )

        merged_aliases = (
            self._merge_alias_values(
                canonical_name=(
                    best_match["name"]
                ),
                existing_aliases=(
                    best_match["aliases"]
                ),
                candidate=entity,
            )
        )

        return GraphEntity(
            entity_id=(
                best_match["entity_id"]
            ),
            name=best_match["name"],
            normalized_name=(
                best_match["normalized_name"]
            ),
            entity_type=entity.entity_type,
            aliases=merged_aliases,
        )

    def _select_best_match(
        self,
        entity: GraphEntity,
        rows: list[dict],
    ) -> dict:
        candidate_keys = {
            entity.normalized_name,
        }

        candidate_keys.update(
            self.normalizer.normalize_name(
                alias
            )
            for alias in entity.aliases
            if alias.strip()
        )

        def score(
            row: dict,
        ) -> tuple[int, int]:
            existing_keys = {
                row["normalized_name"],
            }

            existing_keys.update(
                self.normalizer.normalize_name(
                    alias
                )
                for alias in row["aliases"]
                if alias.strip()
            )

            overlap = len(
                candidate_keys
                & existing_keys
            )

            exact_name = int(
                entity.normalized_name
                ==
                row["normalized_name"]
            )

            return (
                exact_name,
                overlap,
            )

        return max(
            rows,
            key=score,
        )

    def _merge_entities(
        self,
        first: GraphEntity,
        second: GraphEntity,
    ) -> GraphEntity:
        aliases = (
            self._merge_alias_values(
                canonical_name=first.name,
                existing_aliases=(
                    first.aliases
                ),
                candidate=second,
            )
        )

        return GraphEntity(
            entity_id=first.entity_id,
            name=first.name,
            normalized_name=(
                first.normalized_name
            ),
            entity_type=first.entity_type,
            aliases=aliases,
        )

    def _merge_alias_values(
        self,
        canonical_name: str,
        existing_aliases: list[str],
        candidate: GraphEntity,
    ) -> list[str]:
        canonical_normalized = (
            self.normalizer.normalize_name(
                canonical_name
            )
        )

        alias_map: dict[
            str,
            str,
        ] = {}

        values = [
            *existing_aliases,
            candidate.name,
            *candidate.aliases,
        ]

        for value in values:
            if not value.strip():
                continue

            normalized = (
                self.normalizer.normalize_name(
                    value
                )
            )

            if (
                normalized
                == canonical_normalized
            ):
                continue

            alias_map[
                normalized
            ] = value.strip()

        return sorted(
            alias_map.values(),
            key=str.casefold,
        )