from app.api.document_models import (
    DocumentSummary,
)
from app.graph.store import (
    Neo4jGraphStore,
)


class DocumentCatalogService:
    """
    Read-only document catalog backed
    by the TraceGraph Neo4j graph.
    """

    def list_documents(
        self,
    ) -> list[DocumentSummary]:
        store = Neo4jGraphStore()

        try:
            store.verify_connectivity()

            rows = store.query(
                """
                MATCH (d:Document)

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

            return [
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
                    title=row.get(
                        "title"
                    ),
                    author=row.get(
                        "author"
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
                for row in rows
            ]

        finally:
            store.close()

    def get_document(
        self,
        document_id: str,
    ) -> DocumentSummary | None:
        documents = (
            self.list_documents()
        )

        for document in documents:
            if (
                document.document_id
                == document_id
            ):
                return document

        return None