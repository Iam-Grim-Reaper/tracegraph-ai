from dataclasses import dataclass

from app.graph.store import Neo4jGraphStore
from app.models.document import Document
from app.retrieval.hybrid_store import HybridStore


INDEXING = "indexing"
READY = "ready"
FAILED = "failed"


@dataclass(frozen=True)
class ReadinessMigrationResult:
    documents_migrated: int
    points_updated: int
    documents_skipped: int
    errors: int


class DocumentReadinessService:
    """Coordinates fail-closed readiness across Neo4j and Qdrant."""

    def __init__(self, graph_store=None, hybrid_store=None):
        self.graph_store = graph_store or Neo4jGraphStore()
        self.hybrid_store = hybrid_store or HybridStore()
        self._owns_graph_store = graph_store is None

    def close(self) -> None:
        if self._owns_graph_store:
            self.graph_store.close()

    def is_ready(self, document_id: str) -> bool:
        rows = self.graph_store.query(
            """
            MATCH (d:Document {document_id: $document_id})
            RETURN d.indexing_status = $ready AS ready
            """,
            {"document_id": document_id, "ready": READY},
        )
        return bool(rows and rows[0].get("ready"))

    def begin_indexing(self, document: Document) -> bool:
        rows = self.graph_store.query(
            """
            MERGE (d:Document {document_id: $document_id})
            ON CREATE SET d.indexing_status = $indexing
            WITH d, d.indexing_status = $ready AS already_ready
            SET d.indexing_status = CASE
                WHEN already_ready THEN $ready
                ELSE $indexing
            END,
            d.filename = $filename,
            d.file_type = $file_type,
            d.title = $title,
            d.author = $author
            RETURN already_ready
            """,
            {
                "document_id": str(document.id),
                "filename": document.filename,
                "file_type": document.file_type.value,
                "title": document.metadata.title,
                "author": document.metadata.author,
                "indexing": INDEXING,
                "ready": READY,
            },
        )
        return not bool(rows and rows[0].get("already_ready"))

    def mark_failed(self, document_id: str) -> None:
        self.graph_store.query(
            """
            MATCH (d:Document {document_id: $document_id})
            WHERE d.indexing_status <> $ready
            SET d.indexing_status = $failed
            """,
            {"document_id": document_id, "ready": READY, "failed": FAILED},
        )

    def finalize(self, document_id: str) -> int:
        # Qdrant first, Neo4j/catalog last. Until the final Neo4j write,
        # public scope selection remains closed.
        points_updated = self.hybrid_store.set_document_status(
            document_id,
            READY,
        )
        try:
            self.graph_store.query(
                """
                MATCH (d:Document {document_id: $document_id})
                WHERE d.indexing_status IN [$indexing, $failed]
                SET d.indexing_status = $ready
                """,
                {
                    "document_id": document_id,
                    "indexing": INDEXING,
                    "failed": FAILED,
                    "ready": READY,
                },
            )
        except Exception:
            self.hybrid_store.set_document_status(document_id, INDEXING)
            raise
        return points_updated

    def migrate_legacy_ready_documents(self, limit: int = 1000) -> ReadinessMigrationResult:
        if limit < 1 or limit > 10000:
            raise ValueError("Migration limit must be between 1 and 10000")
        self.hybrid_store.ensure_collection()
        self.graph_store.query(
            """
            CREATE INDEX document_indexing_status
            IF NOT EXISTS
            FOR (d:Document)
            ON (d.indexing_status)
            """
        )
        rows = self.graph_store.query(
            """
            MATCH (d:Document)-[:CONTAINS]->(:Chunk)
            WHERE d.indexing_status IS NULL
            RETURN DISTINCT d.document_id AS document_id
            ORDER BY document_id
            LIMIT $limit
            """,
            {"limit": limit},
        )
        migrated = 0
        points = 0
        errors = 0
        for row in rows:
            document_id = row["document_id"]
            try:
                points += self.hybrid_store.set_document_status(document_id, READY)
                self.graph_store.query(
                    """
                    MATCH (d:Document {document_id: $document_id})
                    WHERE d.indexing_status IS NULL
                    SET d.indexing_status = $ready
                    """,
                    {"document_id": document_id, "ready": READY},
                )
                migrated += 1
            except Exception:
                try:
                    self.hybrid_store.set_document_status(document_id, INDEXING)
                except Exception:
                    pass
                errors += 1
        return ReadinessMigrationResult(
            documents_migrated=migrated,
            points_updated=points,
            documents_skipped=0,
            errors=errors,
        )
