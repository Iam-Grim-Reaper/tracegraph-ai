from dataclasses import dataclass
from pathlib import Path

from app.graph.indexer import (
    GraphIndexer,
)
from app.ingestion.service import (
    IngestionService,
)
from app.retrieval.hybrid_indexer import (
    HybridIndexer,
)


@dataclass
class DocumentIndexingResult:
    document_id: str
    filename: str
    file_type: str
    title: str | None

    chunk_count: int

    qdrant_indexed_chunks: int

    graph_entity_count: int
    graph_relationship_count: int
    graph_rejected_relationship_count: int

    graph_cached_chunks: int
    graph_extracted_chunks: int

    status: str = "ready"


class DocumentIndexingService:
    """
    Complete TraceGraph document indexing
    orchestration service.

    One call performs:

        file
          ↓
        ingestion
          ↓
        stable chunks
          ↓
        contextual hybrid indexing
          ↓
        knowledge-graph indexing
          ↓
        ready
    """

    def __init__(
        self,
        max_chars: int = 1000,
        graph_batch_size: int = 5,
    ):
        self.ingestion_service = (
            IngestionService(
                max_chars=max_chars
            )
        )

        self.graph_batch_size = (
            graph_batch_size
        )

    def index_file(
        self,
        file_path: str | Path,
    ) -> DocumentIndexingResult:
        path = Path(
            file_path
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Document not found: "
                f"{path}"
            )

        print("=" * 70)

        print(
            "TRACEGRAPH DOCUMENT INDEX"
        )

        print("=" * 70)

        # ---------------------------------
        # 1. Parse + stable chunking
        # ---------------------------------

        print(
            "\n[1/3] Ingesting document..."
        )

        ingestion = (
            self.ingestion_service
            .ingest(
                path
            )
        )

        document = (
            ingestion.document
        )

        chunks = (
            ingestion.chunks
        )

        if not chunks:
            raise RuntimeError(
                "Document ingestion "
                "produced no chunks"
            )

        print(
            "Document ID:",
            document.id,
        )

        print(
            "Filename:",
            document.filename,
        )

        print(
            "Chunks:",
            len(chunks),
        )

        # Hybrid contextualization requires
        # document-level context.
        #
        # TextChunker does not overlap chunks,
        # so joining the chunk text gives us
        # the complete chunkable document text.
        document_text = (
            "\n\n".join(
                chunk.text
                for chunk in chunks
                if chunk.text.strip()
            )
        )

        if not document_text.strip():
            raise RuntimeError(
                "Document contains no "
                "usable text"
            )

        # ---------------------------------
        # 2. Qdrant hybrid indexing
        # ---------------------------------

        print(
            "\n[2/3] Building hybrid index..."
        )

        hybrid_indexer = (
            HybridIndexer()
        )

        qdrant_count = (
            hybrid_indexer.index(
                document=document,
                chunks=chunks,
                document_text=(
                    document_text
                ),

                # Never destroy the collection
                # when a user uploads another
                # document.
                reset_collection=False,
            )
        )

        print(
            "Qdrant chunks indexed:",
            qdrant_count,
        )

        # ---------------------------------
        # 3. Neo4j graph indexing
        # ---------------------------------

        print(
            "\n[3/3] Building "
            "knowledge graph..."
        )

        graph_indexer = (
            GraphIndexer(
                batch_size=(
                    self.graph_batch_size
                )
            )
        )

        graph_stats = (
            graph_indexer.index(
                document=document,
                chunks=chunks,
            )
        )

        print("\n" + "=" * 70)

        print(
            "DOCUMENT READY"
        )

        print("=" * 70)

        print(
            "Document ID:",
            document.id,
        )

        print(
            "Chunks:",
            len(chunks),
        )

        print(
            "Entities:",
            graph_stats.entity_count,
        )

        print(
            "Semantic relationships:",
            graph_stats
            .semantic_relationship_count,
        )

        return DocumentIndexingResult(
            document_id=str(
                document.id
            ),
            filename=(
                document.filename
            ),
            file_type=(
                document.file_type.value
            ),
            title=(
                document.metadata.title
            ),
            chunk_count=(
                len(chunks)
            ),
            qdrant_indexed_chunks=(
                qdrant_count
            ),
            graph_entity_count=(
                graph_stats.entity_count
            ),
            graph_relationship_count=(
                graph_stats
                .semantic_relationship_count
            ),
            graph_rejected_relationship_count=(
                graph_stats
                .rejected_relationship_count
            ),
            graph_cached_chunks=(
                graph_stats.cached_chunks
            ),
            graph_extracted_chunks=(
                graph_stats.extracted_chunks
            ),
        )