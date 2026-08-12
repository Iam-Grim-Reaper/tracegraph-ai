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