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

    def __init__(
        self,
        collection_name: str | None = None,
    ):
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
            collection_name
            or settings.qdrant_hybrid_collection
        )

        self.vector_size = (
            settings.embedding_dimensions
        )

    # =================================================
    # Collection management
    # =================================================

    def ensure_collection(
        self,
    ) -> None:
        """
        Ensure the TraceGraph hybrid collection
        exists and that document_id is indexed
        for efficient document-scoped retrieval.
        """

        collection_exists = (
            self.client.collection_exists(
                self.collection_name
            )
        )

        if not collection_exists:
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

        # The collection may already exist from
        # earlier development work.
        #
        # Therefore this must run for BOTH:
        #
        # - newly created collections
        # - existing collections
        #
        # document_id becomes our retrieval-scope
        # boundary between uploaded documents.
        self.ensure_document_id_index()

    def ensure_document_id_index(
        self,
    ) -> None:
        """
        Ensure Qdrant has a keyword payload
        index on document_id.

        This improves filtering performance when
        retrieval is scoped to one or more
        selected documents.
        """

        collection_info = (
            self.client.get_collection(
                self.collection_name
            )
        )

        payload_schema = (
            getattr(
                collection_info,
                "payload_schema",
                {},
            )
            or {}
        )

        if (
            "document_id"
            in payload_schema
        ):
            return

        print(
            "Creating Qdrant "
            "document_id payload index..."
        )

        self.client.create_payload_index(
            collection_name=(
                self.collection_name
            ),
            field_name="document_id",
            field_schema=(
                models.PayloadSchemaType.KEYWORD
            ),
            wait=True,
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

    # =================================================
    # Document-scope helpers
    # =================================================

    @staticmethod
    def _normalize_document_ids(
        document_ids: (
            list[str] | None
        ),
    ) -> list[str] | None:
        """
        Normalize document IDs used for
        retrieval filtering.

        Removes:

        - empty values
        - surrounding whitespace
        - duplicate IDs

        None means:
            retrieve across all documents.
        """

        if not document_ids:
            return None

        normalized = list(
            dict.fromkeys(
                document_id.strip()
                for document_id
                in document_ids
                if (
                    document_id
                    and document_id.strip()
                )
            )
        )

        if not normalized:
            return None

        return normalized

    def _build_document_filter(
        self,
        document_ids: (
            list[str] | None
        ),
    ) -> models.Filter | None:
        """
        Build a Qdrant filter restricting
        retrieval to selected document IDs.

        Multiple IDs are supported so that
        the frontend can eventually allow:

            selected_documents = [
                document_a,
                document_b,
            ]

        None means no document restriction.
        """

        normalized = (
            self._normalize_document_ids(
                document_ids
            )
        )

        if normalized is None:
            return None

        return models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id",
                    match=(
                        models.MatchAny(
                            any=normalized
                        )
                    ),
                )
            ]
        )

    # =================================================
    # Indexing
    # =================================================

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

        for (
            chunk,
            dense_embedding,
        ) in zip(
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

            # -----------------------------------------
            # Contextual Retrieval
            #
            # Both dense retrieval and BM25 use the
            # contextualized version when available.
            # -----------------------------------------

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

            # Qdrant does not need None-valued
            # metadata fields.
            payload = {
                key: value
                for key, value
                in payload.items()
                if value is not None
            }

            point = (
                models.PointStruct(
                    # ---------------------------------
                    # Critical TraceGraph invariant:
                    #
                    # Qdrant point ID
                    # =
                    # Neo4j Chunk.chunk_id
                    # =
                    # stable DocumentChunk UUID
                    # ---------------------------------

                    id=str(
                        chunk.id
                    ),

                    vector={
                        self.DENSE_VECTOR_NAME:
                            dense_embedding,

                        self.BM25_VECTOR_NAME:
                            models.Document(
                                text=(
                                    retrieval_text
                                ),
                                model=(
                                    self.BM25_MODEL
                                ),
                            ),
                    },

                    payload=payload,
                )
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

    # =================================================
    # Lexical BM25 retrieval
    # =================================================

    def lexical_search(
        self,
        query: str,
        limit: int = 5,
        document_ids: (
            list[str] | None
        ) = None,
    ):
        if not query.strip():
            raise ValueError(
                "Query cannot be empty"
            )

        document_filter = (
            self._build_document_filter(
                document_ids
            )
        )

        response = (
            self.client.query_points(
                collection_name=(
                    self.collection_name
                ),

                query=models.Document(
                    text=query,
                    model=(
                        self.BM25_MODEL
                    ),
                ),

                using=(
                    self.BM25_VECTOR_NAME
                ),

                # ---------------------------------
                # None:
                #     all documents
                #
                # Filter:
                #     selected documents only
                # ---------------------------------
                query_filter=(
                    document_filter
                ),

                limit=limit,

                with_payload=True,
            )
        )

        return response.points

    # =================================================
    # Hybrid retrieval:
    #
    # Dense
    # +
    # BM25
    # +
    # Reciprocal Rank Fusion
    # =================================================

    def hybrid_search(
        self,
        query: str,
        dense_vector: list[float],
        limit: int = 5,
        candidate_limit: int = 20,
        document_ids: (
            list[str] | None
        ) = None,
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

        document_filter = (
            self._build_document_filter(
                document_ids
            )
        )

        response = (
            self.client.query_points(
                collection_name=(
                    self.collection_name
                ),

                # ---------------------------------
                # Candidate retrieval
                #
                # 1. Dense semantic retrieval
                # 2. BM25 lexical retrieval
                # ---------------------------------

                prefetch=[
                    models.Prefetch(
                        query=(
                            dense_vector
                        ),

                        using=(
                            self
                            .DENSE_VECTOR_NAME
                        ),

                        limit=(
                            candidate_limit
                        ),
                    ),

                    models.Prefetch(
                        query=(
                            models.Document(
                                text=query,

                                model=(
                                    self
                                    .BM25_MODEL
                                ),
                            )
                        ),

                        using=(
                            self
                            .BM25_VECTOR_NAME
                        ),

                        limit=(
                            candidate_limit
                        ),
                    ),
                ],

                # ---------------------------------
                # Reciprocal Rank Fusion
                # ---------------------------------

                query=(
                    models.FusionQuery(
                        fusion=(
                            models
                            .Fusion
                            .RRF
                        )
                    )
                ),

                # ---------------------------------
                # Document scope
                #
                # The filter applies to the query
                # pipeline, constraining retrieval
                # to the selected document IDs.
                # ---------------------------------

                query_filter=(
                    document_filter
                ),

                limit=limit,

                with_payload=True,
            )
        )

        return response.points

    # =================================================
    # Stable-ID retrieval
    # =================================================

    def retrieve_by_ids(
        self,
        point_ids: list[str],
    ):
        """
        Retrieve exact chunks by stable ID.

        Used by Graph + Hybrid fusion when graph
        retrieval identifies a provenance chunk
        that did not survive Qdrant's initial
        hybrid candidate set.
        """

        if not point_ids:
            return []

        return (
            self.client.retrieve(
                collection_name=(
                    self.collection_name
                ),

                ids=point_ids,

                with_payload=True,

                with_vectors=False,
            )
        )

    # =================================================
    # Collection statistics
    # =================================================

    def count_points(
        self,
    ) -> int:
        result = (
            self.client.count(
                collection_name=(
                    self.collection_name
                ),

                exact=True,
            )
        )

        return result.count
