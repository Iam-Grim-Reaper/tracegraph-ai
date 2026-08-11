from dataclasses import dataclass

from app.graph.graph_query import (
    GraphFact,
    GraphQueryRetriever,
    LinkedGraphEntity,
)
from app.graph.store import (
    Neo4jGraphStore,
)
from app.retrieval.embeddings import (
    GeminiEmbeddingService,
)
from app.retrieval.hybrid_store import (
    HybridStore,
)
from app.retrieval.reranker import (
    CrossEncoderReranker,
)


@dataclass
class TraceGraphChunkResult:
    chunk_id: str

    filename: str
    page_number: int | None
    chunk_index: int | None

    text: str
    contextual_text: str | None

    hybrid_score: float | None

    graph_supported: bool
    graph_fact_count: int
    graph_evidence: list[str]

    pre_fusion_score: float

    rerank_score: float


@dataclass
class TraceGraphRetrievalResult:
    query: str

    linked_entities: list[
        LinkedGraphEntity
    ]

    graph_facts: list[
        GraphFact
    ]

    chunks: list[
        TraceGraphChunkResult
    ]


class GraphHybridRetriever:
    """
    TraceGraph retrieval pipeline.

    Combines:

    1. Gemini dense retrieval
    2. Qdrant BM25
    3. Qdrant RRF fusion
    4. Neo4j graph retrieval
    5. Stable chunk-ID fusion
    6. Cross-encoder reranking
    """

    def __init__(
        self,
        graph_store: Neo4jGraphStore,
    ):
        self.graph_store = (
            graph_store
        )

        self.embedding_service = (
            GeminiEmbeddingService()
        )

        self.hybrid_store = (
            HybridStore()
        )

        self.graph_retriever = (
            GraphQueryRetriever(
                store=graph_store
            )
        )

        self.reranker = (
            CrossEncoderReranker()
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        qdrant_limit: int = 20,
        qdrant_candidate_limit: int = 30,
        graph_max_seed_entities: int = 5,
        graph_max_facts: int = 30,
        max_fused_candidates: int = 25,
    ) -> TraceGraphRetrievalResult:
        if not query.strip():
            raise ValueError(
                "Query cannot be empty"
            )

        # -----------------------------------------
        # 1. Dense query embedding
        # -----------------------------------------
        query_vector = (
            self.embedding_service
            .embed_query(
                query
            )
        )

        # -----------------------------------------
        # 2. Qdrant:
        #
        # contextual dense + BM25 + RRF
        # -----------------------------------------
        qdrant_results = (
            self.hybrid_store
            .hybrid_search(
                query=query,
                dense_vector=query_vector,
                limit=qdrant_limit,
                candidate_limit=(
                    qdrant_candidate_limit
                ),
            )
        )

        # -----------------------------------------
        # 3. Neo4j graph retrieval
        # -----------------------------------------
        graph_result = (
            self.graph_retriever
            .retrieve(
                query=query,
                max_seed_entities=(
                    graph_max_seed_entities
                ),
                max_facts=(
                    graph_max_facts
                ),
            )
        )

        # -----------------------------------------
        # 4. Group graph evidence by the
        #    provenance chunk that produced it.
        # -----------------------------------------
        graph_support: dict[
            str,
            list[GraphFact],
        ] = {}

        for fact in graph_result.facts:
            chunk_id = (
                fact.source_chunk_id
            )

            if not chunk_id:
                continue

            graph_support.setdefault(
                chunk_id,
                [],
            ).append(
                fact
            )

        # -----------------------------------------
        # 5. Start the candidate set with
        #    Qdrant hybrid candidates.
        # -----------------------------------------
        candidate_by_id: dict[
            str,
            object,
        ] = {}

        hybrid_score_by_id: dict[
            str,
            float,
        ] = {}

        for point in qdrant_results:
            chunk_id = str(
                point.id
            )

            candidate_by_id[
                chunk_id
            ] = point

            hybrid_score_by_id[
                chunk_id
            ] = float(
                point.score
            )

        # -----------------------------------------
        # 6. Find graph-supported chunks that
        #    Qdrant did NOT return.
        #
        #    Stable IDs let us fetch those exact
        #    chunks from Qdrant.
        # -----------------------------------------
        missing_graph_ids = [
            chunk_id
            for chunk_id
            in graph_support
            if chunk_id
            not in candidate_by_id
        ]

        graph_only_points = (
            self.hybrid_store
            .retrieve_by_ids(
                missing_graph_ids
            )
        )

        for point in graph_only_points:
            chunk_id = str(
                point.id
            )

            candidate_by_id[
                chunk_id
            ] = point

        # -----------------------------------------
        # 7. Candidate-level fusion score
        #
        # Qdrant score and graph support are
        # different signals, so we normalize the
        # Qdrant side before combining them.
        #
        # This score is ONLY used to constrain the
        # candidate pool before cross-encoder
        # reranking.
        # -----------------------------------------
        max_hybrid_score = max(
            hybrid_score_by_id.values(),
            default=0.0,
        )

        def calculate_pre_fusion_score(
            chunk_id: str,
        ) -> float:
            raw_hybrid_score = (
                hybrid_score_by_id.get(
                    chunk_id,
                    0.0,
                )
            )

            if max_hybrid_score > 0:
                normalized_hybrid = (
                    raw_hybrid_score
                    / max_hybrid_score
                )
            else:
                normalized_hybrid = 0.0

            graph_fact_count = len(
                graph_support.get(
                    chunk_id,
                    [],
                )
            )

            # Three or more supporting facts
            # reaches the maximum graph signal.
            graph_score = min(
                graph_fact_count / 3.0,
                1.0,
            )

            return (
                0.75
                * normalized_hybrid
                +
                0.25
                * graph_score
            )

        ordered_candidate_ids = sorted(
            candidate_by_id,
            key=(
                calculate_pre_fusion_score
            ),
            reverse=True,
        )

        selected_ids = (
            ordered_candidate_ids[
                :max_fused_candidates
            ]
        )

        candidate_points = [
            candidate_by_id[
                chunk_id
            ]
            for chunk_id
            in selected_ids
        ]

        # -----------------------------------------
        # 8. Cross-encoder reranking
        # -----------------------------------------
        reranked = (
            self.reranker.rerank(
                query=query,
                results=candidate_points,
                top_k=top_k,
            )
        )

        # -----------------------------------------
        # 9. Build rich TraceGraph results
        # -----------------------------------------
        final_results: list[
            TraceGraphChunkResult
        ] = []

        for reranked_item in reranked:
            point = (
                reranked_item.point
            )

            chunk_id = str(
                point.id
            )

            payload = (
                point.payload
                or {}
            )

            supporting_facts = (
                graph_support.get(
                    chunk_id,
                    [],
                )
            )

            graph_evidence = []

            for fact in supporting_facts:
                evidence = (
                    f"{fact.source_name} "
                    f"-[{fact.relationship_type}]-> "
                    f"{fact.target_name}"
                )

                if fact.evidence_text:
                    evidence += (
                        f" | "
                        f"{fact.evidence_text}"
                    )

                graph_evidence.append(
                    evidence
                )

            final_results.append(
                TraceGraphChunkResult(
                    chunk_id=chunk_id,

                    filename=(
                        payload.get(
                            "filename",
                            "Unknown",
                        )
                    ),

                    page_number=(
                        payload.get(
                            "page_number"
                        )
                    ),

                    chunk_index=(
                        payload.get(
                            "chunk_index"
                        )
                    ),

                    text=(
                        payload.get(
                            "text",
                            "",
                        )
                    ),

                    contextual_text=(
                        payload.get(
                            "contextual_text"
                        )
                    ),

                    hybrid_score=(
                        hybrid_score_by_id.get(
                            chunk_id
                        )
                    ),

                    graph_supported=bool(
                        supporting_facts
                    ),

                    graph_fact_count=len(
                        supporting_facts
                    ),

                    graph_evidence=(
                        graph_evidence
                    ),

                    pre_fusion_score=(
                        calculate_pre_fusion_score(
                            chunk_id
                        )
                    ),

                    rerank_score=(
                        reranked_item
                        .rerank_score
                    ),
                )
            )

        return TraceGraphRetrievalResult(
            query=query,

            linked_entities=(
                graph_result
                .linked_entities
            ),

            graph_facts=(
                graph_result.facts
            ),

            chunks=(
                final_results
            ),
        )