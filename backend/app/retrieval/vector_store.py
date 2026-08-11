from qdrant_client import QdrantClient, models

from app.core.config import settings
from app.models.document import (
    Document,
    DocumentChunk,
)


class QdrantVectorStore:
    def __init__(self):
        if not settings.qdrant_url:
            raise ValueError(
                "QDRANT_URL is not configured"
            )

        if not settings.qdrant_api_key:
            raise ValueError(
                "QDRANT_API_KEY is not configured"
            )

        self.collection_name = (
            settings.qdrant_collection
        )

        self.vector_size = (
            settings.embedding_dimensions
        )

        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )

    def ensure_collection(self) -> None:
        if self.collection_exists():
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size,
                distance=models.Distance.COSINE,
            ),
        )

    def collection_exists(self) -> bool:
        return self.client.collection_exists(
            collection_name=self.collection_name
        )

    def upsert_chunks(
        self,
        document: Document,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError(
                "Each chunk must have exactly "
                "one embedding"
            )

        points: list[models.PointStruct] = []

        for chunk, embedding in zip(
            chunks,
            embeddings,
            strict=True,
        ):
            if len(embedding) != self.vector_size:
                raise ValueError(
                    f"Expected vector size "
                    f"{self.vector_size}, "
                    f"received {len(embedding)}"
                )

            payload = {
                "document_id": str(document.id),
                "filename": document.filename,
                "file_type": document.file_type.value,
                "title": document.metadata.title,
                "chunk_index": chunk.chunk_index,
                "page_number": (
                    chunk.metadata.page_number
                ),
                "section": chunk.metadata.section,
                "heading": chunk.metadata.heading,
                "text": chunk.text,
                "contextual_text": (
                    chunk.contextual_text
                ),
            }

            payload = {
                key: value
                for key, value in payload.items()
                if value is not None
            }

            points.append(
                models.PointStruct(
                    id=str(chunk.id),
                    vector=embedding,
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )

    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
    ):
        if len(query_vector) != self.vector_size:
            raise ValueError(
                f"Expected query vector size "
                f"{self.vector_size}, "
                f"received {len(query_vector)}"
            )

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            with_payload=True,
            limit=limit,
        )

        return response.points