from app.models.document import IngestionResult
from app.retrieval.embeddings import (
    GeminiEmbeddingService,
)
from app.retrieval.vector_store import (
    QdrantVectorStore,
)


class VectorIndexer:
    def __init__(self):
        self.embedding_service = (
            GeminiEmbeddingService()
        )

        self.vector_store = (
            QdrantVectorStore()
        )

    def index(
        self,
        result: IngestionResult,
    ) -> int:
        self.vector_store.ensure_collection()

        document = result.document
        chunks = result.chunks

        if not chunks:
            raise ValueError(
                "Cannot index a document with no chunks"
            )

        texts = [
            chunk.contextual_text
            or chunk.text
            for chunk in chunks
        ]

        embeddings = (
            self.embedding_service.embed_documents(
                texts=texts,
                title=document.metadata.title,
            )
        )

        self.vector_store.upsert_chunks(
            document=document,
            chunks=chunks,
            embeddings=embeddings,
        )

        return len(chunks)