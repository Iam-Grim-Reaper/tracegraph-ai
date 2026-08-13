from app.agents.workflow import (
    build_tracegraph_workflow,
)
from app.services.document_catalog_service import (
    DocumentCatalogService,
)


class TraceGraphService:
    """
    Application-level service around the
    compiled TraceGraph LangGraph workflow.

    The workflow is compiled once and reused
    across API requests.

    Retrieval can optionally be restricted to
    selected document IDs.
    """

    def __init__(
        self,
    ):
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
        document_ids: (
            list[str] | None
        ) = None,
    ) -> dict:
        question = (
            question.strip()
        )

        if not question:
            raise ValueError(
                "Question cannot be empty"
            )

        normalized_document_ids = (
            self._normalize_document_ids(
                document_ids
            )
        )

        # -----------------------------------------
        # Validate requested documents.
        #
        # This prevents a typo or stale frontend
        # state from silently producing an empty
        # retrieval result.
        # -----------------------------------------

        if normalized_document_ids:
            self._validate_document_ids(
                normalized_document_ids
            )

        print(
            "TraceGraph question:",
            question,
        )

        if normalized_document_ids:
            print(
                "TraceGraph document scope:",
                normalized_document_ids,
            )

        else:
            print(
                "TraceGraph document scope: "
                "ALL DOCUMENTS"
            )

        result = (
            self.workflow.invoke(
                {
                    "question": (
                        question
                    ),

                    "document_ids": (
                        normalized_document_ids
                    ),

                    "retry_count": 0,
                }
            )
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

        evidence_items = result.get("evidence_items", [])
        documents_by_id = {
            document.document_id: document.filename
            for document in DocumentCatalogService().list_documents()
        }
        for item in evidence_items:
            if not item.get("filename") and item.get("document_id"):
                item["filename"] = documents_by_id.get(item["document_id"])

        used_labels = result.get("used_evidence_labels", [])
        verified = result.get("verification_passed", False)
        degraded = result.get("degraded", False)
        decomposition_degraded = result.get("decomposition_degraded", False)
        if degraded:
            answer_status = "degraded_retrieval"
        elif verified and used_labels:
            answer_status = "verified_answer"
        elif verified:
            answer_status = "verified_abstention"
        elif used_labels or decomposition_degraded:
            answer_status = "partial_grounded_answer"
        else:
            answer_status = "grounded_abstention"

        return {
            "answer": (
                final_answer
            ),

            "route": (
                result.get(
                    "retrieval_route",
                    "hybrid",
                )
            ),

            "strategy": result.get(
                "routing_strategy",
                "legacy",
            ),
            "initial_route": result.get(
                "initial_route",
                result.get("retrieval_route", "hybrid"),
            ),
            "final_route": result.get(
                "final_route",
                result.get("retrieval_route", "hybrid"),
            ),
            "routing_reason": result.get("routing_reason"),
            "hybrid_evidence_count": result.get("hybrid_evidence_count", 0),
            "graph_evidence_count": result.get("graph_evidence_count", 0),
            "hybrid_top_relevance": result.get("hybrid_top_relevance"),
            "graph_top_relevance": result.get("graph_top_relevance"),
            "requires_decomposition": result.get("requires_decomposition", False),
            "degraded": result.get("degraded", False),
            "degradation_reason": result.get("degradation_reason"),
            "query_embedding_call_count": result.get("query_embedding_call_count", 0),
            "hybrid_probe_latency_ms": result.get("hybrid_probe_latency_ms"),
            "graph_probe_latency_ms": result.get("graph_probe_latency_ms"),
            "adaptive_retrieval_latency_ms": result.get("adaptive_retrieval_latency_ms"),
            "decomposition_used": result.get("decomposition_used", False),
            "decomposition_degraded": result.get("decomposition_degraded", False),
            "decomposition_call_count": result.get("decomposition_call_count", 0),
            "decomposition_latency_ms": result.get("decomposition_latency_ms"),
            "subquestion_count": result.get("subquestion_count", 0),
            "subquestions": result.get("subquestions", []),
            "qdrant_call_count": result.get("qdrant_call_count", 0),
            "neo4j_call_count": result.get("neo4j_call_count", 0),
            "crossencoder_call_count": result.get("crossencoder_call_count", 0),
            "evidence_items": evidence_items,
            "answer_status": answer_status,

            "verified": (
                result.get(
                    "verification_passed",
                    False,
                )
            ),

            "verification_reason": (
                result.get(
                    "verification_reason"
                )
            ),

            "retry_count": (
                result.get(
                    "retry_count",
                    0,
                )
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

            "document_ids": (
                normalized_document_ids
            ),
        }

    @staticmethod
    def _normalize_document_ids(
        document_ids: (
            list[str] | None
        ),
    ) -> list[str] | None:
        if document_ids is None:
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
            raise ValueError(
                "document_ids cannot "
                "contain only empty values."
            )

        return normalized

    @staticmethod
    def _validate_document_ids(
        document_ids: list[str],
    ) -> None:
        catalog = (
            DocumentCatalogService()
        )

        indexed_documents = (
            catalog.list_documents()
        )

        indexed_ids = {
            document.document_id
            for document
            in indexed_documents
        }

        missing_ids = [
            document_id
            for document_id
            in document_ids
            if document_id
            not in indexed_ids
        ]

        if missing_ids:
            raise ValueError(
                "One or more selected "
                "documents do not exist: "
                + ", ".join(
                    missing_ids
                )
            )


_tracegraph_service: (
    TraceGraphService | None
) = None


def get_tracegraph_service(
) -> TraceGraphService:
    """
    Lazily initialize one TraceGraphService
    instance per backend process.
    """

    global _tracegraph_service

    if (
        _tracegraph_service
        is None
    ):
        _tracegraph_service = (
            TraceGraphService()
        )

    return _tracegraph_service
