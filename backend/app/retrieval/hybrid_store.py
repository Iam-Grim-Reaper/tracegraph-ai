from qdrant_client import (
    QdrantClient,
    models,
)

from app.core.config import settings
from app.models.document import (
    Document,
    DocumentChunk,
)


class HybridStore:
    DENSE_VECTOR_NAME = "dense"
    BM25_VECTOR_NAME = "bm25"

    BM25_MODEL = "Qdrant/bm25"

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

    def ensure_collection(
        self,
    ) -> None:
        if self.client.collection_exists(
            self.collection_name
        ):
            return

        self.client.create_collection(
            collection_name=(
                self.collection_name
            ),
            vectors_config={
                self.DENSE_VECTOR_NAME:
                    models.VectorParams(
                        size=self.vector_size,
                        distance=(
                            models.Distance.COSINE
                        ),
                    )
            },
            sparse_vectors_config={
                self.BM25_VECTOR_NAME:
                    models.SparseVectorParams(
                        modifier=(
                            models.Modifier.IDF
                        )
                    )
            },
        )

    def recreate_collection(
        self,
    ) -> None:
        """
        Delete and recreate only the configured
        hybrid collection.

        Intended for migrations/re-indexing,
        not normal document ingestion.
        """

        if self.client.collection_exists(
            self.collection_name
        ):
            self.client.delete_collection(
                collection_name=(
                    self.collection_name
                )
            )

        self.ensure_collection()

    def upsert_chunks(
        self,
        document: Document,
        chunks: list[DocumentChunk],
        dense_embeddings: list[
            list[float]
        ],
    ) -> None:
        if not chunks:
            raise ValueError(
                "Cannot upsert an empty "
                "chunk list"
            )

        if (
            len(chunks)
            != len(dense_embeddings)
        ):
            raise ValueError(
                "Each chunk must have "
                "exactly one dense embedding"
            )

        points: list[
            models.PointStruct
        ] = []

        for chunk, dense_embedding in zip(
            chunks,
            dense_embeddings,
            strict=True,
        ):
            if (
                len(dense_embedding)
                != self.vector_size
            ):
                raise ValueError(
                    f"Expected vector size "
                    f"{self.vector_size}, "
                    f"received "
                    f"{len(dense_embedding)}"
                )

            # Contextual Retrieval:
            #
            # Both dense retrieval and BM25
            # index the contextualized version
            # when available.
            retrieval_text = (
                chunk.contextual_text
                or chunk.text
            )

            payload = {
                "document_id": str(
                    document.id
                ),
                "chunk_id": str(
                    chunk.id
                ),
                "filename": (
                    document.filename
                ),
                "file_type": (
                    document.file_type.value
                ),
                "title": (
                    document.metadata.title
                ),
                "chunk_index": (
                    chunk.chunk_index
                ),
                "page_number": (
                    chunk.metadata.page_number
                ),
                "section": (
                    chunk.metadata.section
                ),
                "heading": (
                    chunk.metadata.heading
                ),
                "text": (
                    chunk.text
                ),
                "contextual_text": (
                    chunk.contextual_text
                ),
            }

            payload = {
                key: value
                for key, value
                in payload.items()
                if value is not None
            }

            point = models.PointStruct(
                # Critical:
                #
                # Same stable chunk UUID used
                # by Neo4j.
                id=str(
                    chunk.id
                ),

                vector={
                    self.DENSE_VECTOR_NAME:
                        dense_embedding,

                    self.BM25_VECTOR_NAME:
                        models.Document(
                            text=retrieval_text,
                            model=(
                                self.BM25_MODEL
                            ),
                        ),
                },

                payload=payload,
            )

            points.append(
                point
            )

        self.client.upsert(
            collection_name=(
                self.collection_name
            ),
            points=points,
            wait=True,
        )

    def lexical_search(
        self,
        query: str,
        limit: int = 5,
    ):
        if not query.strip():
            raise ValueError(
                "Query cannot be empty"
            )

        response = (
            self.client.query_points(
                collection_name=(
                    self.collection_name
                ),
                query=models.Document(
                    text=query,
                    model=self.BM25_MODEL,
                ),
                using=(
                    self.BM25_VECTOR_NAME
                ),
                limit=limit,
                with_payload=True,
            )
        )

        return response.points

    def hybrid_search(
        self,
        query: str,
        dense_vector: list[float],
        limit: int = 5,
        candidate_limit: int = 20,
    ):
        if not query.strip():
            raise ValueError(
                "Query cannot be empty"
            )

        if (
            len(dense_vector)
            != self.vector_size
        ):
            raise ValueError(
                f"Expected dense query "
                f"vector size "
                f"{self.vector_size}, "
                f"received "
                f"{len(dense_vector)}"
            )

        if candidate_limit < limit:
            raise ValueError(
                "candidate_limit must be "
                "greater than or equal "
                "to limit"
            )

        response = (
            self.client.query_points(
                collection_name=(
                    self.collection_name
                ),
                prefetch=[
                    models.Prefetch(
                        query=dense_vector,
                        using=(
                            self.DENSE_VECTOR_NAME
                        ),
                        limit=(
                            candidate_limit
                        ),
                    ),

                    models.Prefetch(
                        query=models.Document(
                            text=query,
                            model=(
                                self.BM25_MODEL
                            ),
                        ),
                        using=(
                            self.BM25_VECTOR_NAME
                        ),
                        limit=(
                            candidate_limit
                        ),
                    ),
                ],
                query=models.FusionQuery(
                    fusion=(
                        models.Fusion.RRF
                    )
                ),
                limit=limit,
                with_payload=True,
            )
        )

        return response.points
    def retrieve_by_ids(
        self,
        point_ids: list[str],
    ):
        if not point_ids:
            return []

        return self.client.retrieve(
            collection_name=(
                self.collection_name
            ),
            ids=point_ids,
            with_payload=True,
            with_vectors=False,
    )

    def count_points(
        self,
    ) -> int:
        result = self.client.count(
            collection_name=(
                self.collection_name
            ),
            exact=True,
        )

        return result.count