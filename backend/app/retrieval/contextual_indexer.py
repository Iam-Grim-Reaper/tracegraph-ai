from app.core.config import settings
from app.models.document import (
    Document,
    DocumentChunk,
)
from app.retrieval.contextualizer import Contextualizer
from app.retrieval.embeddings import GeminiEmbeddingService
from app.retrieval.vector_store import QdrantVectorStore


class ContextualVectorIndexer:
    def __init__(self):
        self.contextualizer = Contextualizer()

        self.embedding_service = (
            GeminiEmbeddingService()
        )

        self.vector_store = QdrantVectorStore(
            collection_name=(
                settings.qdrant_contextual_collection
            )
        )

    def index(
        self,
        document: Document,
        chunks: list[DocumentChunk],
        document_text: str,
    ) -> int:
        if not chunks:
            raise ValueError(
                "Cannot index a document with no chunks"
            )

        self.vector_store.ensure_collection()

        contextualized_chunks = (
            self.contextualizer.contextualize_chunks(
                document=document,
                chunks=chunks,
                document_text=document_text,
            )
        )

        texts = [
            chunk.contextual_text
            for chunk in contextualized_chunks
            if chunk.contextual_text is not None
        ]

        if len(texts) != len(contextualized_chunks):
            raise RuntimeError(
                "One or more chunks were not contextualized"
            )

        embeddings = (
            self.embedding_service.embed_documents(
                texts=texts,
                title=document.metadata.title,
            )
        )

        self.vector_store.upsert_chunks(
            document=document,
            chunks=contextualized_chunks,
            embeddings=embeddings,
        )

        return len(contextualized_chunks)