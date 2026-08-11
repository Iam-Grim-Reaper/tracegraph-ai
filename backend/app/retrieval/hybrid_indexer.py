from app.models.document import (
    Document,
    DocumentChunk,
)
from app.retrieval.contextualizer import (
    Contextualizer,
)
from app.retrieval.embeddings import (
    GeminiEmbeddingService,
)
from app.retrieval.hybrid_store import (
    HybridStore,
)


class HybridIndexer:
    def __init__(
        self,
    ):
        self.contextualizer = (
            Contextualizer()
        )

        self.embedding_service = (
            GeminiEmbeddingService()
        )

        self.hybrid_store = (
            HybridStore()
        )

    def index(
        self,
        document: Document,
        chunks: list[DocumentChunk],
        document_text: str,
        reset_collection: bool = False,
    ) -> int:
        if not chunks:
            raise ValueError(
                "Cannot index a document "
                "with no chunks"
            )

        if not document_text.strip():
            raise ValueError(
                "document_text cannot "
                "be empty"
            )

        # During our stable-ID migration
        # we intentionally recreate the old
        # experimental hybrid collection.
        if reset_collection:
            self.hybrid_store\
                .recreate_collection()

        else:
            self.hybrid_store\
                .ensure_collection()

        # ---------------------------------
        # Contextual Retrieval
        # ---------------------------------
        contextualized_chunks = (
            self.contextualizer
            .contextualize_chunks(
                document=document,
                chunks=chunks,
                document_text=(
                    document_text
                ),
            )
        )

        contextual_texts = [
            chunk.contextual_text
            for chunk
            in contextualized_chunks
            if (
                chunk.contextual_text
                is not None
            )
        ]

        if (
            len(contextual_texts)
            != len(
                contextualized_chunks
            )
        ):
            raise RuntimeError(
                "One or more chunks were "
                "not contextualized"
            )

        # ---------------------------------
        # Gemini dense embeddings
        # ---------------------------------
        dense_embeddings = (
            self.embedding_service
            .embed_documents(
                texts=(
                    contextual_texts
                ),
                title=(
                    document.metadata.title
                ),
            )
        )

        # ---------------------------------
        # Dense + BM25 hybrid indexing
        # ---------------------------------
        self.hybrid_store\
            .upsert_chunks(
                document=document,
                chunks=(
                    contextualized_chunks
                ),
                dense_embeddings=(
                    dense_embeddings
                ),
            )

        return len(
            contextualized_chunks
        )