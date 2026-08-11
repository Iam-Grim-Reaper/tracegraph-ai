from qdrant_client import QdrantClient, models

from app.core.config import settings


class HybridStore:
    DENSE_VECTOR_NAME = "dense"
    BM25_VECTOR_NAME = "bm25"

    def __init__(self):
        if not settings.qdrant_url:
            raise ValueError(
                "QDRANT_URL is not configured"
            )

        if not settings.qdrant_api_key:
            raise ValueError(
                "QDRANT_API_KEY is not configured"
            )

        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )

        self.collection_name = (
            settings.qdrant_hybrid_collection
        )

        self.vector_size = (
            settings.embedding_dimensions
        )

    def ensure_collection(self) -> None:
        if self.client.collection_exists(
            self.collection_name
        ):
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                self.DENSE_VECTOR_NAME:
                    models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE,
                    )
            },
            sparse_vectors_config={
                self.BM25_VECTOR_NAME:
                    models.SparseVectorParams(
                        modifier=models.Modifier.IDF
                    )
            },
        )

    def lexical_search(
        self,
        query: str,
        limit: int = 5,
    ):
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=models.Document(
                text=query,
                model="Qdrant/bm25",
            ),
            using=self.BM25_VECTOR_NAME,
            limit=limit,
            with_payload=True,
        )

        return response.points

    def hybrid_search(
        self,
        query: str,
        dense_vector: list[float],
        limit: int = 5,
        candidate_limit: int = 20,
    ):
        response = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense_vector,
                    using=self.DENSE_VECTOR_NAME,
                    limit=candidate_limit,
                ),
                models.Prefetch(
                    query=models.Document(
                        text=query,
                        model="Qdrant/bm25",
                    ),
                    using=self.BM25_VECTOR_NAME,
                    limit=candidate_limit,
                ),
            ],
            query=models.FusionQuery(
                fusion=models.Fusion.RRF
            ),
            limit=limit,
            with_payload=True,
        )

        return response.points