import json

from app.api.document_models import (
    DocumentSummary,
)
from app.graph.store import (
    Neo4jGraphStore,
)


class DocumentCatalogService:
    """
    Read-only document catalog backed by
    the TraceGraph Neo4j global graph.

    Returns:

    - document metadata
    - ontology metadata
    - ontology classification metadata
    - graph statistics
    """

    def list_documents(
        self,
    ) -> list[
        DocumentSummary
    ]:
        store = (
            Neo4jGraphStore()
        )

        try:
            store.verify_connectivity()

            rows = (
                store.query(
                    """
                    MATCH (
                        d:Document
                    )

                    OPTIONAL MATCH (
                        d
                    )-[:CONTAINS]->(
                        c:Chunk
                    )

                    WITH
                        d,

                        count(
                            DISTINCT c
                        ) AS chunk_count

                    OPTIONAL MATCH (
                        c2:Chunk
                    )-[:MENTIONS]->(
                        e:Entity
                    )

                    WHERE
                        c2.document_id =
                            d.document_id

                    WITH
                        d,

                        chunk_count,

                        count(
                            DISTINCT e
                        ) AS entity_count

                    OPTIONAL MATCH (
                        :Entity
                    )-[r]->(
                        :Entity
                    )

                    WHERE
                        r.source_document_id =
                            d.document_id

                        AND NOT type(r) IN [
                            'CONTAINS',
                            'MENTIONS'
                        ]

                    RETURN
                        d.document_id
                            AS document_id,

                        d.filename
                            AS filename,

                        d.file_type
                            AS file_type,

                        d.title
                            AS title,

                        d.author
                            AS author,

                        d.ontology_profile
                            AS ontology_profile,

                        d.ontology_version
                            AS ontology_version,

                        d.ontology_profiles
                            AS ontology_profiles,

                        d.ontology_confidence
                            AS ontology_confidence,

                        d.ontology_method
                            AS ontology_method,

                        d.ontology_reason
                            AS ontology_reason,

                        d.ontology_scores_json
                            AS ontology_scores_json,

                        chunk_count,

                        entity_count,

                        count(
                            DISTINCT r
                        ) AS
                            graph_relationship_count

                    ORDER BY
                        filename
                    """
                )
            )

            return [
                self._row_to_summary(
                    row
                )

                for row
                in rows
            ]

        finally:
            store.close()

    def get_document(
        self,
        document_id: str,
    ) -> (
        DocumentSummary
        | None
    ):
        store = (
            Neo4jGraphStore()
        )

        try:
            store.verify_connectivity()

            rows = (
                store.query(
                    """
                    MATCH (
                        d:Document {
                            document_id:
                                $document_id
                        }
                    )

                    OPTIONAL MATCH (
                        d
                    )-[:CONTAINS]->(
                        c:Chunk
                    )

                    WITH
                        d,

                        count(
                            DISTINCT c
                        ) AS chunk_count

                    OPTIONAL MATCH (
                        c2:Chunk
                    )-[:MENTIONS]->(
                        e:Entity
                    )

                    WHERE
                        c2.document_id =
                            d.document_id

                    WITH
                        d,

                        chunk_count,

                        count(
                            DISTINCT e
                        ) AS entity_count

                    OPTIONAL MATCH (
                        :Entity
                    )-[r]->(
                        :Entity
                    )

                    WHERE
                        r.source_document_id =
                            d.document_id

                        AND NOT type(r) IN [
                            'CONTAINS',
                            'MENTIONS'
                        ]

                    RETURN
                        d.document_id
                            AS document_id,

                        d.filename
                            AS filename,

                        d.file_type
                            AS file_type,

                        d.title
                            AS title,

                        d.author
                            AS author,

                        d.ontology_profile
                            AS ontology_profile,

                        d.ontology_version
                            AS ontology_version,

                        d.ontology_profiles
                            AS ontology_profiles,

                        d.ontology_confidence
                            AS ontology_confidence,

                        d.ontology_method
                            AS ontology_method,

                        d.ontology_reason
                            AS ontology_reason,

                        d.ontology_scores_json
                            AS ontology_scores_json,

                        chunk_count,

                        entity_count,

                        count(
                            DISTINCT r
                        ) AS
                            graph_relationship_count
                    """,
                    {
                        "document_id": (
                            document_id
                        )
                    },
                )
            )

            if not rows:
                return None

            return (
                self._row_to_summary(
                    rows[0]
                )
            )

        finally:
            store.close()

    # =====================================================
    # Row conversion
    # =====================================================

    @classmethod
    def _row_to_summary(
        cls,
        row: dict,
    ) -> DocumentSummary:
        ontology_profile = (
            row.get(
                "ontology_profile"
            )
        )

        ontology_profiles = (
            cls._resolve_profiles(
                ontology_profile=(
                    ontology_profile
                ),

                stored_profiles=(
                    row.get(
                        "ontology_profiles"
                    )
                ),
            )
        )

        ontology_scores = (
            cls._parse_scores(
                row.get(
                    "ontology_scores_json"
                )
            )
        )

        return (
            DocumentSummary(
                document_id=(
                    row["document_id"]
                ),

                filename=(
                    row["filename"]
                ),

                file_type=(
                    row["file_type"]
                ),

                title=(
                    row.get(
                        "title"
                    )
                ),

                author=(
                    row.get(
                        "author"
                    )
                ),

                ontology_profile=(
                    ontology_profile
                ),

                ontology_version=(
                    row.get(
                        "ontology_version"
                    )
                ),

                ontology_profiles=(
                    ontology_profiles
                ),

                ontology_confidence=(
                    row.get(
                        "ontology_confidence"
                    )
                ),

                ontology_method=(
                    row.get(
                        "ontology_method"
                    )
                ),

                ontology_reason=(
                    row.get(
                        "ontology_reason"
                    )
                ),

                ontology_scores=(
                    ontology_scores
                ),

                chunk_count=(
                    row.get(
                        "chunk_count",
                        0,
                    )
                ),

                entity_count=(
                    row.get(
                        "entity_count",
                        0,
                    )
                ),

                graph_relationship_count=(
                    row.get(
                        "graph_relationship_count",
                        0,
                    )
                ),
            )
        )

    # =====================================================
    # Backward-compatible ontology profile handling
    # =====================================================

    @staticmethod
    def _resolve_profiles(
        ontology_profile: (
            str | None
        ),
        stored_profiles,
    ) -> list[str]:
        """
        Older documents may have ontology_profile
        but not ontology_profiles.

        Reconstruct the components when possible.

        Example:

            policy+contract

        becomes:

            ["policy", "contract"]
        """

        if stored_profiles:
            return [
                str(
                    profile
                )

                for profile
                in stored_profiles

                if str(
                    profile
                ).strip()
            ]

        if not ontology_profile:
            return []

        parts = [
            component.strip()

            for component
            in ontology_profile.split("+")

            if component.strip()
        ]

        return (
            parts
            or [
                ontology_profile
            ]
        )

    # =====================================================
    # Score parsing
    # =====================================================

    @staticmethod
    def _parse_scores(
        value,
    ) -> dict[
        str,
        float,
    ]:
        if not value:
            return {}

        if isinstance(
            value,
            dict,
        ):
            return {
                str(key): float(
                    score
                )

                for key, score
                in value.items()
            }

        if not isinstance(
            value,
            str,
        ):
            return {}

        try:
            parsed = (
                json.loads(
                    value
                )
            )

        except (
            json.JSONDecodeError,
            TypeError,
        ):
            return {}

        if not isinstance(
            parsed,
            dict,
        ):
            return {}

        scores: dict[
            str,
            float,
        ] = {}

        for key, score in (
            parsed.items()
        ):
            try:
                scores[
                    str(
                        key
                    )
                ] = float(
                    score
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

        return scores