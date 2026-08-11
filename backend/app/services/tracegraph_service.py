from app.agents.workflow import (
    build_tracegraph_workflow,
)


class TraceGraphService:
    """
    Application-level service around the
    compiled TraceGraph LangGraph workflow.

    The workflow is compiled once and reused
    across API requests.
    """

    def __init__(self):
        print(
            "Initializing TraceGraph workflow..."
        )

        self.workflow = (
            build_tracegraph_workflow()
        )

        print(
            "TraceGraph workflow ready."
        )

    def ask(
        self,
        question: str,
    ) -> dict:
        if not question.strip():
            raise ValueError(
                "Question cannot be empty"
            )

        result = self.workflow.invoke(
            {
                "question": (
                    question.strip()
                ),
                "retry_count": 0,
            }
        )

        final_answer = (
            result.get(
                "final_answer"
            )
            or result.get(
                "draft_answer"
            )
            or (
                "I could not generate "
                "a supported answer."
            )
        )

        return {
            "answer": final_answer,

            "route": result.get(
                "retrieval_route",
                "hybrid",
            ),

            "verified": result.get(
                "verification_passed",
                False,
            ),

            "verification_reason": (
                result.get(
                    "verification_reason"
                )
            ),

            "retry_count": result.get(
                "retry_count",
                0,
            ),

            "rewritten_question": (
                result.get(
                    "rewritten_question"
                )
            ),

            "retrieved_chunk_ids": (
                result.get(
                    "retrieved_chunk_ids",
                    [],
                )
            ),

            "graph_fact_count": (
                result.get(
                    "graph_fact_count",
                    0,
                )
            ),

            "used_evidence_labels": (
                result.get(
                    "used_evidence_labels",
                    [],
                )
            ),
        }


_tracegraph_service: (
    TraceGraphService | None
) = None


def get_tracegraph_service(
) -> TraceGraphService:
    """
    Lazily initialize one TraceGraphService
    instance per backend process.

    This prevents rebuilding the workflow
    and retrieval components on every
    HTTP request.
    """

    global _tracegraph_service

    if _tracegraph_service is None:
        _tracegraph_service = (
            TraceGraphService()
        )

    return _tracegraph_service