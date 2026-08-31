import logging
from threading import Lock
from time import perf_counter

from app.agents.workflow import (
    build_tracegraph_workflow,
)
from app.services.document_catalog_service import (
    DocumentCatalogService,
)
from app.core.observability import log_event


logger = logging.getLogger(__name__)


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
        log_event(logger, logging.INFO, "workflow_initializing", operation="workflow_initialization", status="started")

        self._owned_resources: list[object] = []
        self._close_lock = Lock()
        self._closed = False
        self.workflow = build_tracegraph_workflow(self._owned_resources)

        log_event(logger, logging.INFO, "workflow_ready", operation="workflow_initialization", status="complete")

    def close(self) -> None:
        with self._close_lock:
            if self._closed:
                return
            self._closed = True

        seen: set[int] = set()
        for resource in self._owned_resources:
            if id(resource) in seen:
                continue
            seen.add(id(resource))
            close = getattr(resource, "close", None)
            if not callable(close):
                continue
            try:
                close()
            except Exception as exc:
                log_event(
                    logger,
                    logging.ERROR,
                    "resource_close_failed",
                    operation="resource_close",
                    status="failed",
                    error_type=type(exc).__name__,
                )

    def ask(
        self,
        question: str,
        document_ids: (
            list[str] | None
        ) = None,
    ) -> dict:
        question, normalized_document_ids = self._prepare_request(
            question, document_ids
        )

        started = perf_counter()
        log_event(logger, logging.INFO, "chat_workflow_started", operation="chat_workflow", status="started", document_scope_count=len(normalized_document_ids or []))

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

        response = self._serialize_result(result, normalized_document_ids)
        log_event(logger, logging.INFO, "chat_workflow_completed", operation="chat_workflow", status="complete", route=response.get("route"), hybrid_evidence_count=response.get("hybrid_evidence_count"), graph_evidence_count=response.get("graph_evidence_count"), degraded=response.get("degraded"), latency_ms=round((perf_counter() - started) * 1000, 3))
        return response

    def stream_events(self, question, document_ids=None, cancelled=None):
        if cancelled is not None and cancelled.is_set():
            return
        for payload in self._stream_events(question, document_ids, cancelled):
            if cancelled is not None and cancelled.is_set():
                return
            yield payload
            if cancelled is not None and cancelled.is_set():
                return

    def _stream_events(self, question, document_ids=None, cancelled=None):
        question, normalized_document_ids = self._prepare_request(
            question, document_ids
        )
        state = {
            "question": question,
            "document_ids": normalized_document_ids,
            "retry_count": 0,
        }
        yielded_research_start = False
        yielded_verification_start = False

        for update in self.workflow.stream(state, stream_mode="updates"):
            if cancelled is not None and cancelled.is_set():
                return
            for node_name, values in update.items():
                if not isinstance(values, dict):
                    continue
                state.update(values)
                if node_name in {
                    "adaptive_retrieval", "hybrid_retrieval",
                    "graph_retrieval", "fused_retrieval",
                }:
                    yield {
                        "type": "retrieval", "status": "complete",
                        "message": "Textual and graph evidence were evaluated.",
                    }
                    yield {
                        "type": "routing", "status": "complete",
                        "route": state.get("retrieval_route"),
                        "message": state.get("routing_reason")
                        or "A grounded retrieval strategy was selected.",
                    }
                    if state.get("decomposition_used"):
                        yield {
                            "type": "decomposition", "status": "complete",
                            "message": "The question was divided into focused retrieval steps.",
                        }
                        for item in state.get("subquestions", []):
                            yield {
                                "type": "subquestion",
                                "id": item.get("id"),
                                "route": item.get("route"),
                                "status": "complete" if item.get("route") else "limited",
                                "message": item.get("question", "Sub-question complete."),
                            }
                    yielded_research_start = True
                    yield {
                        "type": "research", "status": "started",
                        "message": "Synthesizing a grounded answer.",
                    }
                elif node_name == "research_agent":
                    if not yielded_research_start:
                        yield {
                            "type": "research", "status": "started",
                            "message": "Synthesizing a grounded answer.",
                        }
                    yield {
                        "type": "research", "status": "complete",
                        "message": "Grounded synthesis is ready for verification.",
                    }
                    yielded_verification_start = True
                    yield {
                        "type": "verification", "status": "started",
                        "message": "Checking every supported claim.",
                    }
                elif node_name == "verification_agent":
                    if not yielded_verification_start:
                        yield {
                            "type": "verification", "status": "started",
                            "message": "Checking every supported claim.",
                        }
                    yield {
                        "type": "verification", "status": "complete",
                        "message": "Verification completed.",
                    }
                elif node_name == "verification_retry":
                    yield {
                        "type": "retrieval", "status": "retrying",
                        "message": "Retrieving additional evidence for verification.",
                    }

        if cancelled is None or not cancelled.is_set():
            yield {
                "type": "completed", "status": "complete",
                "message": "TraceGraph completed the verified response.",
                "response": self._serialize_result(state, normalized_document_ids),
            }

    def _prepare_request(self, question, document_ids):
        question = question.strip()
        if not question:
            raise ValueError("Question cannot be empty")
        normalized_document_ids = self._normalize_document_ids(document_ids)
        if normalized_document_ids:
            self._validate_document_ids(normalized_document_ids)
        return question, normalized_document_ids

    @staticmethod
    def _serialize_result(result, normalized_document_ids):
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
_tracegraph_service_lock = Lock()


def get_tracegraph_service(
) -> TraceGraphService:
    """
    Lazily initialize one TraceGraphService
    instance per backend process.
    """

    global _tracegraph_service

    if _tracegraph_service is None:
        with _tracegraph_service_lock:
            if _tracegraph_service is None:
                _tracegraph_service = TraceGraphService()

    return _tracegraph_service


def close_tracegraph_service() -> None:
    global _tracegraph_service
    with _tracegraph_service_lock:
        service = _tracegraph_service
        _tracegraph_service = None
    if service is not None:
        service.close()
