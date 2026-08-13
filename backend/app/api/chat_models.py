from pydantic import (
    BaseModel,
    Field,
)


class ChatRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
        description=(
            "Question to answer using "
            "TraceGraph retrieval."
        ),
    )

    document_ids: (
        list[str] | None
    ) = Field(
        default=None,
        min_length=1,
        max_length=50,
        description=(
            "Optional document IDs that "
            "restrict retrieval to the "
            "selected documents. "
            "If omitted, all indexed "
            "documents are searched."
        ),
    )


class ChatResponse(BaseModel):
    answer: str

    route: str
    strategy: str = "legacy"
    initial_route: str | None = None
    final_route: str | None = None
    routing_reason: str | None = None
    hybrid_evidence_count: int = 0
    graph_evidence_count: int = 0
    hybrid_top_relevance: float | None = None
    graph_top_relevance: float | None = None
    requires_decomposition: bool = False
    degraded: bool = False
    degradation_reason: str | None = None
    query_embedding_call_count: int = 0
    hybrid_probe_latency_ms: float | None = None
    graph_probe_latency_ms: float | None = None
    adaptive_retrieval_latency_ms: float | None = None
    decomposition_used: bool = False
    decomposition_degraded: bool = False
    decomposition_call_count: int = 0
    decomposition_latency_ms: float | None = None
    subquestion_count: int = 0
    subquestions: list[dict] = Field(default_factory=list)
    qdrant_call_count: int = 0
    neo4j_call_count: int = 0
    crossencoder_call_count: int = 0

    verified: bool

    verification_reason: (
        str | None
    ) = None

    retry_count: int

    rewritten_question: (
        str | None
    ) = None

    retrieved_chunk_ids: list[str]

    graph_fact_count: int

    used_evidence_labels: list[str]

    document_ids: (
        list[str] | None
    ) = None
