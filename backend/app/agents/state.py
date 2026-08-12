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