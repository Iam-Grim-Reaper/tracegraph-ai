from typing import Literal, TypedDict


RetrievalRoute = Literal[
    "hybrid",
    "graph",
    "fused",
]


class TraceGraphState(
    TypedDict,
    total=False,
):
    # ---------------------------------
    # Original user question
    # ---------------------------------
    question: str

    # ---------------------------------
    # Retrieval Router output
    # ---------------------------------
    retrieval_route: RetrievalRoute
    routing_reason: str
    routing_strategy: str
    initial_route: RetrievalRoute
    final_route: RetrievalRoute
    hybrid_evidence_count: int
    graph_evidence_count: int
    hybrid_top_relevance: float | None
    graph_top_relevance: float | None
    hybrid_mean_relevance: float | None
    graph_mean_relevance: float | None
    requires_decomposition: bool
    degraded: bool
    degradation_reason: str | None
    query_embedding_call_count: int
    query_embedding_latency_ms: float | None
    hybrid_probe_latency_ms: float | None
    graph_probe_latency_ms: float | None
    reranker_latency_ms: float | None
    reranker_input_count: int | None
    reranker_total_chars: int | None
    reranker_max_chars: int | None
    adaptive_retrieval_latency_ms: float | None
    decomposition_used: bool
    decomposition_degraded: bool
    decomposition_call_count: int
    decomposition_latency_ms: float | None
    subquestion_count: int
    subquestions: list[dict]
    qdrant_call_count: int
    neo4j_call_count: int
    crossencoder_call_count: int
    evidence_items: list[dict]

    # ---------------------------------
    # Research Agent
    # ---------------------------------
    research_context: str

    retrieved_chunk_ids: list[str]

    graph_fact_count: int

    # ---------------------------------
    # Draft answer
    # ---------------------------------
    draft_answer: str
    used_evidence_labels: list[str]

    # ---------------------------------
    # Verification Agent
    # ---------------------------------
    verification_passed: bool

    verification_reason: str

    unsupported_claims: list[str]

    # ---------------------------------
    # Retry control
    # ---------------------------------
    retry_count: int

    rewritten_question: str | None

    # ---------------------------------
    # Retrieval scope
    #
    # None:
    #     all indexed documents
    #
    # list[str]:
    #     selected documents only
    # ---------------------------------
    document_ids: list[str] | None

    # ---------------------------------
    # Final output
    # ---------------------------------
    final_answer: str
