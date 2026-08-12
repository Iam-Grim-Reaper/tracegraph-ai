from app.agents.state import (
    TraceGraphState,
)
from app.graph.graph_query import (
    GraphQueryRetriever,
)
from app.graph.store import (
    Neo4jGraphStore,
)
from app.retrieval.embeddings import (
    GeminiEmbeddingService,
)
from app.retrieval.graph_hybrid_retriever import (
    GraphHybridRetriever,
)
from app.retrieval.hybrid_store import (
    HybridStore,
)
from app.retrieval.reranker import (
    CrossEncoderReranker,
)


class RetrievalNodes:
    """
    Execute the retrieval strategy selected
    by the Retrieval Router.

    Supported paths:

    hybrid
        Contextual dense + BM25 + RRF
        + cross-encoder reranking.

    graph
        Neo4j entity linking + graph traversal.

    fused
        Qdrant hybrid retrieval + Neo4j graph
        retrieval + stable-ID fusion
        + cross-encoder reranking.

    All paths optionally respect document_ids
    supplied in TraceGraphState.
    """

    def __init__(
        self,
    ):
        self.embedding_service = (
            GeminiEmbeddingService()
        )

        self.hybrid_store = (
            HybridStore()
        )

        self.graph_store = (
            Neo4jGraphStore()
        )

        self.graph_store.verify_connectivity()

        self.graph_retriever = (
            GraphQueryRetriever(
                store=self.graph_store
            )
        )

        # Load rerankers lazily.
        self._hybrid_reranker = None
        self._fused_retriever = None

    # =================================================
    # HYBRID
    # =================================================

    def hybrid(
        self,
        state: TraceGraphState,
    ) -> dict:
        question = self._get_question(
            state
        )

        document_ids = state.get(
            "document_ids"
        )

        print(
            "Executing HYBRID retrieval..."
        )

        if document_ids:
            print(
                "Document scope:",
                document_ids,
            )

        query_vector = (
            self.embedding_service
            .embed_query(
                question
            )
        )

        candidates = (
            self.hybrid_store
            .hybrid_search(
                query=question,
                dense_vector=query_vector,
                limit=15,
                candidate_limit=30,
                document_ids=(
                    document_ids
                ),
            )
        )

        # A valid document scope can
        # legitimately produce no results.
        if not candidates:
            return {
                "research_context": (
                    "No document-scoped "
                    "retrieval evidence found."
                ),
                "retrieved_chunk_ids": [],
                "graph_fact_count": 0,
            }

        reranker = (
            self._get_hybrid_reranker()
        )

        reranked = (
            reranker.rerank(
                query=question,
                results=candidates,
                top_k=5,
            )
        )

        context_parts = []
        chunk_ids = []

        for index, item in enumerate(
            reranked,
            start=1,
        ):
            point = item.point

            payload = (
                point.payload
                or {}
            )

            chunk_id = str(
                point.id
            )

            chunk_ids.append(
                chunk_id
            )

            filename = payload.get(
                "filename",
                "Unknown",
            )

            page_number = payload.get(
                "page_number"
            )

            chunk_index = payload.get(
                "chunk_index"
            )

            text = payload.get(
                "text",
                "",
            )

            context_parts.append(
                (
                    f"[Evidence {index}]\n"
                    f"Source: {filename}\n"
                    f"Page: {page_number}\n"
                    f"Chunk: {chunk_index}\n"
                    f"Chunk ID: {chunk_id}\n"
                    f"Rerank score: "
                    f"{item.rerank_score:.4f}\n\n"
                    f"{text}"
                )
            )

        return {
            "research_context": (
                "\n\n".join(
                    context_parts
                )
            ),
            "retrieved_chunk_ids": (
                chunk_ids
            ),
            "graph_fact_count": 0,
        }

    # =================================================
    # GRAPH
    # =================================================

    def graph(
        self,
        state: TraceGraphState,
    ) -> dict:
        question = self._get_question(
            state
        )

        document_ids = state.get(
            "document_ids"
        )

        print(
            "Executing GRAPH retrieval..."
        )

        if document_ids:
            print(
                "Document scope:",
                document_ids,
            )

        result = (
            self.graph_retriever
            .retrieve(
                query=question,
                max_seed_entities=5,
                max_facts=20,
                document_ids=(
                    document_ids
                ),
            )
        )

        context = (
            self.graph_retriever
            .format_context(
                result=result,
                max_facts=12,
            )
        )

        chunk_ids = list(
            dict.fromkeys(
                fact.source_chunk_id
                for fact
                in result.facts
                if fact.source_chunk_id
            )
        )

        return {
            "research_context": context,
            "retrieved_chunk_ids": (
                chunk_ids
            ),
            "graph_fact_count": (
                len(result.facts)
            ),
        }

    # =================================================
    # FUSED
    # =================================================

    def fused(
        self,
        state: TraceGraphState,
    ) -> dict:
        question = self._get_question(
            state
        )

        document_ids = state.get(
            "document_ids"
        )

        print(
            "Executing FUSED retrieval..."
        )

        if document_ids:
            print(
                "Document scope:",
                document_ids,
            )

        retriever = (
            self._get_fused_retriever()
        )

        result = retriever.retrieve(
            query=question,
            top_k=6,
            qdrant_limit=20,
            qdrant_candidate_limit=30,
            graph_max_seed_entities=5,
            graph_max_facts=30,
            max_fused_candidates=25,
            document_ids=(
                document_ids
            ),
        )

        context_parts = []
        chunk_ids = []

        # -----------------------------------------
        # 1. Top reranked textual evidence
        # -----------------------------------------

        for index, chunk in enumerate(
            result.chunks,
            start=1,
        ):
            chunk_ids.append(
                chunk.chunk_id
            )

            graph_section = ""

            if chunk.graph_evidence:
                graph_section = (
                    "\n\nGraph support:\n"
                    + "\n".join(
                        f"- {evidence}"
                        for evidence
                        in chunk.graph_evidence
                    )
                )

            context_parts.append(
                (
                    f"[Evidence {index}]\n"
                    f"Source: {chunk.filename}\n"
                    f"Page: {chunk.page_number}\n"
                    f"Chunk: {chunk.chunk_index}\n"
                    f"Chunk ID: "
                    f"{chunk.chunk_id}\n"
                    f"Hybrid score: "
                    f"{chunk.hybrid_score}\n"
                    f"Rerank score: "
                    f"{chunk.rerank_score:.4f}\n"
                    f"Graph supported: "
                    f"{chunk.graph_supported}\n\n"
                    f"{chunk.text}"
                    f"{graph_section}"
                )
            )

        # -----------------------------------------
        # 2. Preserve graph evidence independently
        #
        # A graph fact must not disappear merely
        # because its provenance chunk did not
        # survive text reranking.
        # -----------------------------------------

        seen_graph_facts = set()

        graph_evidence_index = 1

        for fact in result.graph_facts:
            fact_key = (
                fact.source_entity_id,
                fact.relationship_type,
                fact.target_entity_id,
                fact.source_chunk_id,
            )

            if (
                fact_key
                in seen_graph_facts
            ):
                continue

            seen_graph_facts.add(
                fact_key
            )

            graph_chunk_id = (
                fact.source_chunk_id
            )

            if (
                graph_chunk_id
                and graph_chunk_id
                not in chunk_ids
            ):
                chunk_ids.append(
                    graph_chunk_id
                )

            context_parts.append(
                (
                    f"[Graph Evidence "
                    f"{graph_evidence_index}]\n"
                    f"{fact.source_name} "
                    f"-[{fact.relationship_type}]-> "
                    f"{fact.target_name}\n"
                    f"Page: "
                    f"{fact.page_number}\n"
                    f"Chunk ID: "
                    f"{fact.source_chunk_id}\n"
                    f"Document ID: "
                    f"{fact.source_document_id}\n"
                    f"Confidence: "
                    f"{fact.confidence}\n"
                    f"Evidence: "
                    f"{fact.evidence_text}"
                )
            )

            graph_evidence_index += 1

        if not context_parts:
            context_parts.append(
                "No document-scoped "
                "retrieval evidence found."
            )

        return {
            "research_context": (
                "\n\n".join(
                    context_parts
                )
            ),
            "retrieved_chunk_ids": (
                chunk_ids
            ),
            "graph_fact_count": (
                len(result.graph_facts)
            ),
        }

    # =================================================
    # Lazy dependencies
    # =================================================

    def _get_hybrid_reranker(
        self,
    ) -> CrossEncoderReranker:
        if (
            self._hybrid_reranker
            is None
        ):
            self._hybrid_reranker = (
                CrossEncoderReranker()
            )

        return self._hybrid_reranker

    def _get_fused_retriever(
        self,
    ) -> GraphHybridRetriever:
        if (
            self._fused_retriever
            is None
        ):
            self._fused_retriever = (
                GraphHybridRetriever(
                    graph_store=(
                        self.graph_store
                    )
                )
            )

        return self._fused_retriever

    # =================================================
    # State helpers
    # =================================================

    @staticmethod
    def _get_question(
        state: TraceGraphState,
    ) -> str:
        question = (
            state.get(
                "rewritten_question"
            )
            or state.get(
                "question",
                "",
            )
        )

        if not question.strip():
            raise ValueError(
                "Question cannot be empty"
            )

        return question