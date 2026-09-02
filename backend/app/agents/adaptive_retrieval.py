import re
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import perf_counter

from app.agents.state import RetrievalRoute, TraceGraphState
from app.core.config import settings
from app.core.observability import log_event
from app.graph.graph_query import GraphFact, GraphQueryResult, GraphQueryRetriever
from app.graph.store import Neo4jGraphStore
from app.retrieval.embeddings import GeminiEmbeddingService
from app.retrieval.hybrid_store import HybridStore
from app.retrieval.reranker import CrossEncoderReranker


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvidenceSignal:
    candidate_count: int
    top_relevance: float | None
    mean_top_relevance: float | None
    has_evidence: bool


@dataclass(frozen=True)
class EvidenceDecision:
    route: RetrievalRoute
    reason: str


class EvidenceArbitrator:
    def decide(
        self,
        hybrid: EvidenceSignal,
        graph: EvidenceSignal,
        requires_decomposition: bool,
    ) -> EvidenceDecision:
        if requires_decomposition and (
            hybrid.has_evidence or graph.has_evidence
        ):
            return EvidenceDecision(
                "fused",
                "The question requires multiple pieces of evidence.",
            )

        if hybrid.has_evidence and graph.has_evidence:
            hybrid_top = hybrid.top_relevance or 0.0
            graph_top = graph.top_relevance or 0.0
            margin = settings.adaptive_evidence_dominance_margin

            if graph_top - hybrid_top >= margin:
                return EvidenceDecision(
                    "graph",
                    "Relevant evidence was primarily found in the knowledge graph.",
                )

            if hybrid_top - graph_top >= margin:
                return EvidenceDecision(
                    "hybrid",
                    "Relevant evidence was primarily found in document text.",
                )

            return EvidenceDecision(
                "fused",
                "Both textual and graph evidence were useful.",
            )

        if graph.has_evidence:
            return EvidenceDecision(
                "graph",
                "Relevant evidence was primarily found in the knowledge graph.",
            )

        if hybrid.has_evidence:
            return EvidenceDecision(
                "hybrid",
                "Relevant evidence was primarily found in document text.",
            )

        return EvidenceDecision(
            "fused",
            "No sufficiently relevant retrieval evidence was found.",
        )


class AdaptiveEvidenceRetriever:
    """Retrieve first, then select how the evidence is composed."""

    def __init__(
        self,
        embedding_service=None,
        hybrid_store=None,
        graph_retriever=None,
        reranker=None,
    ):
        self.embedding_service = embedding_service or GeminiEmbeddingService()
        self.hybrid_store = hybrid_store or HybridStore()

        if graph_retriever is None:
            graph_store = Neo4jGraphStore()
            graph_store.verify_connectivity()
            self.graph_retriever = GraphQueryRetriever(graph_store)
        else:
            self.graph_retriever = graph_retriever

        self._reranker = reranker
        self.arbitrator = EvidenceArbitrator()

    def __call__(self, state: TraceGraphState) -> dict:
        started = perf_counter()

        question = (
            state.get("rewritten_question")
            or state.get("question", "")
        )

        if not question.strip():
            raise ValueError("Question cannot be empty")

        document_ids = state.get("document_ids")
        requires_decomposition = self._requires_decomposition(question)

        # ---------------------------------------------------------
        # Query embedding
        # ---------------------------------------------------------

        embedding_started = perf_counter()

        query_vector = self.embedding_service.embed_query(
            question
        )

        query_embedding_latency_ms = (
            perf_counter() - embedding_started
        ) * 1000

        # ---------------------------------------------------------
        # Parallel retrieval probes
        # ---------------------------------------------------------

        hybrid_error = None
        graph_error = None
        hybrid_latency = None
        graph_latency = None
        neo4j_call_count = 1

        def hybrid_probe():
            probe_started = perf_counter()

            result = self.hybrid_store.hybrid_search(
                query=question,
                dense_vector=query_vector,
                limit=settings.adaptive_hybrid_limit,
                candidate_limit=settings.adaptive_hybrid_candidate_limit,
                document_ids=document_ids,
            )

            return (
                result,
                (perf_counter() - probe_started) * 1000,
            )

        def graph_probe():
            probe_started = perf_counter()

            result = self.graph_retriever.retrieve(
                query=question,
                max_seed_entities=settings.adaptive_graph_max_seed_entities,
                max_facts=settings.adaptive_graph_max_facts,
                document_ids=document_ids,
                max_path_depth=(
                    2
                    if requires_decomposition
                    else 1
                ),
            )

            return (
                result,
                (perf_counter() - probe_started) * 1000,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            hybrid_future = executor.submit(
                hybrid_probe
            )
            graph_future = executor.submit(
                graph_probe
            )

            try:
                hybrid_points, hybrid_latency = (
                    hybrid_future.result()
                )
            except Exception as exc:
                hybrid_points = []
                hybrid_error = exc

            try:
                graph_result, graph_latency = (
                    graph_future.result()
                )
            except Exception as exc:
                graph_result = GraphQueryResult(
                    question,
                    [],
                    [],
                )
                graph_error = exc

        if (
            hybrid_error is not None
            and graph_error is not None
        ):
            raise RuntimeError(
                "Adaptive retrieval failed because both evidence "
                "channels were unavailable."
            ) from hybrid_error

        # A complex question may describe an entity rather than name it.
        # Reuse the already-scoped hybrid evidence chunks as bounded graph
        # provenance seeds instead of adding vocabulary rules or scanning.

        if (
            (
                requires_decomposition
                or state.get(
                    "provenance_expand",
                    False,
                )
            )
            and graph_error is None
            and not graph_result.facts
            and hybrid_points
        ):
            expansion_started = perf_counter()

            try:
                neo4j_call_count += 1

                graph_result = (
                    self.graph_retriever.retrieve_by_chunk_ids(
                        query=question,
                        chunk_ids=[
                            str(point.id)
                            for point in hybrid_points
                        ],
                        document_ids=document_ids,
                        max_facts=(
                            settings.adaptive_graph_max_facts
                        ),
                    )
                )

                graph_latency = (
                    (graph_latency or 0.0)
                    + (
                        perf_counter()
                        - expansion_started
                    )
                    * 1000
                )

            except Exception as exc:
                graph_error = exc

        # ---------------------------------------------------------
        # Build reranker input
        # ---------------------------------------------------------

        hybrid_texts = [
            str(
                (point.payload or {}).get(
                    "text",
                    "",
                )
            )
            for point in hybrid_points
        ]

        graph_texts = [
            self.verbalize_graph_fact(fact)
            for fact in graph_result.facts
        ]

        reranker_texts = [
            *hybrid_texts,
            *graph_texts,
        ]

        # ---------------------------------------------------------
        # CrossEncoder reranking
        # ---------------------------------------------------------

        reranker_started = perf_counter()

        scores = self._get_reranker().score_texts(
            question,
            reranker_texts,
        )

        reranker_latency_ms = (
            perf_counter() - reranker_started
        ) * 1000

        # Split the shared CrossEncoder result back into
        # document and graph evidence scores.

        hybrid_scores = scores[
            :len(hybrid_texts)
        ]

        graph_scores = scores[
            len(hybrid_texts):
        ]

        # ---------------------------------------------------------
        # Rank evidence
        # ---------------------------------------------------------

        ranked_hybrid = sorted(
            zip(
                hybrid_points,
                hybrid_scores,
                strict=True,
            ),
            key=lambda item: item[1],
            reverse=True,
        )

        ranked_graph = sorted(
            zip(
                graph_result.facts,
                graph_scores,
                strict=True,
            ),
            key=lambda item: item[1],
            reverse=True,
        )

        hybrid_signal = self._signal(
            hybrid_scores
        )

        graph_signal = self._signal(
            graph_scores
        )

        decision = self.arbitrator.decide(
            hybrid_signal,
            graph_signal,
            requires_decomposition,
        )

        # ---------------------------------------------------------
        # Degraded-mode handling
        # ---------------------------------------------------------

        degraded = (
            hybrid_error is not None
            or graph_error is not None
        )

        degradation_reason = None

        if graph_error is not None:
            decision = EvidenceDecision(
                "hybrid",
                (
                    "Graph retrieval was unavailable; "
                    "document evidence was used."
                ),
            )

            degradation_reason = (
                "graph_unavailable"
            )

        elif hybrid_error is not None:
            decision = EvidenceDecision(
                "graph",
                (
                    "Document retrieval was unavailable; "
                    "graph evidence was used."
                ),
            )

            degradation_reason = (
                "hybrid_unavailable"
            )

        if (
            not hybrid_signal.has_evidence
            and not graph_signal.has_evidence
        ):
            ranked_hybrid = []
            ranked_graph = []

        # ---------------------------------------------------------
        # Compose final evidence context
        # ---------------------------------------------------------

        (
            context,
            chunk_ids,
            graph_count,
            evidence_items,
        ) = self._compose_context(
            decision.route,
            ranked_hybrid,
            ranked_graph,
        )

        latency_ms = (
            perf_counter() - started
        ) * 1000

        # ---------------------------------------------------------
        # Diagnostics + workflow state
        # ---------------------------------------------------------

        result = {
            "retrieval_route": decision.route,
            "initial_route": decision.route,
            "final_route": decision.route,
            "routing_strategy": "adaptive_evidence",
            "routing_reason": decision.reason,
            "research_context": context,
            "retrieved_chunk_ids": chunk_ids,
            "graph_fact_count": graph_count,
            "hybrid_evidence_count": (
                hybrid_signal.candidate_count
            ),
            "graph_evidence_count": (
                graph_signal.candidate_count
            ),
            "hybrid_top_relevance": (
                hybrid_signal.top_relevance
            ),
            "graph_top_relevance": (
                graph_signal.top_relevance
            ),
            "hybrid_mean_relevance": (
                hybrid_signal.mean_top_relevance
            ),
            "graph_mean_relevance": (
                graph_signal.mean_top_relevance
            ),
            "requires_decomposition": (
                requires_decomposition
            ),
            "degraded": degraded,
            "degradation_reason": (
                degradation_reason
            ),

            # Embedding diagnostics
            "query_embedding_call_count": 1,
            "query_embedding_latency_ms": (
                query_embedding_latency_ms
            ),

            # Retrieval diagnostics
            "hybrid_probe_latency_ms": (
                hybrid_latency
            ),
            "graph_probe_latency_ms": (
                graph_latency
            ),

            # CrossEncoder diagnostics
            "reranker_latency_ms": (
                reranker_latency_ms
            ),
            "reranker_input_count": len(
                reranker_texts
            ),
            "reranker_total_chars": sum(
                len(text)
                for text in reranker_texts
            ),
            "reranker_max_chars": max(
                (
                    len(text)
                    for text in reranker_texts
                ),
                default=0,
            ),

            # Overall retrieval timing
            "adaptive_retrieval_latency_ms": (
                latency_ms
            ),

            "grounded_entities": (
                self._grounded_entities(
                    ranked_graph
                )
            ),
            "qdrant_call_count": 1,
            "neo4j_call_count": (
                neo4j_call_count
            ),
            "crossencoder_call_count": (
                1 if scores else 0
            ),
            "evidence_items": evidence_items,
        }

        log_event(
            logger,
            logging.INFO,
            "adaptive_retrieval_completed",
            operation="adaptive_retrieval",
            status="complete",
            route=decision.route,
            hybrid_evidence_count=len(
                ranked_hybrid
            ),
            graph_evidence_count=len(
                ranked_graph
            ),
            degraded=degraded,
            latency_ms=round(
                latency_ms,
                3,
            ),
            query_embedding_latency_ms=round(
                query_embedding_latency_ms,
                3,
            ),
            reranker_latency_ms=round(
                reranker_latency_ms,
                3,
            ),
            reranker_input_count=len(
                reranker_texts
            ),
            reranker_total_chars=sum(
                len(text)
                for text in reranker_texts
            ),
            reranker_max_chars=max(
                (
                    len(text)
                    for text in reranker_texts
                ),
                default=0,
            ),
        )

        return result

    def _get_reranker(self):
        if self._reranker is None:
            self._reranker = (
                CrossEncoderReranker()
            )

        return self._reranker

    @staticmethod
    def verbalize_graph_fact(
        fact: GraphFact,
    ) -> str:
        evidence = (
            fact.evidence_text
            or ""
        )

        return (
            f"{fact.source_name} "
            f"{fact.relationship_type} "
            f"{fact.target_name}. "
            f"{evidence}"
        ).strip()

    @staticmethod
    def _requires_decomposition(
        question: str,
    ) -> bool:
        normalized = re.sub(
            r"\s+",
            " ",
            question.casefold(),
        ).strip()

        request_words = re.findall(
            r"\b(?:who|what|which|where|when|how)\b",
            normalized,
        )

        has_join = bool(
            re.search(
                r"(?:;|\bthen\b|\band\b)",
                normalized,
            )
        )

        return (
            len(request_words) >= 2
            and has_join
        )

    @staticmethod
    def _signal(
        scores: list[float],
    ) -> EvidenceSignal:
        if not scores:
            return EvidenceSignal(
                0,
                None,
                None,
                False,
            )

        ordered = sorted(
            scores,
            reverse=True,
        )

        top_values = ordered[
            :settings.adaptive_evidence_mean_top_k
        ]

        top = ordered[0]

        return EvidenceSignal(
            candidate_count=len(scores),
            top_relevance=top,
            mean_top_relevance=(
                sum(top_values)
                / len(top_values)
            ),
            has_evidence=(
                top
                >= settings.adaptive_evidence_relevance_threshold
            ),
        )

    @staticmethod
    def _compose_context(
        route,
        ranked_hybrid,
        ranked_graph,
    ):
        parts = []
        chunk_ids = []
        evidence_items = []

        include_hybrid = route in {
            "hybrid",
            "fused",
        }

        include_graph = route in {
            "graph",
            "fused",
        }

        if include_hybrid:
            for index, (
                point,
                score,
            ) in enumerate(
                ranked_hybrid[:5],
                start=1,
            ):
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

                parts.append(
                    f"[Evidence {index}]\n"
                    f"Source: "
                    f"{payload.get('filename', 'Unknown')}\n"
                    f"Page: "
                    f"{payload.get('page_number')}\n"
                    f"Chunk: "
                    f"{payload.get('chunk_index')}\n"
                    f"Chunk ID: "
                    f"{chunk_id}\n"
                    f"Rerank score: "
                    f"{score:.4f}\n\n"
                    f"{payload.get('text', '')}"
                )

                evidence_items.append(
                    {
                        "label": (
                            f"Evidence {index}"
                        ),
                        "kind": "text",
                        "text": str(
                            payload.get(
                                "text",
                                "",
                            )
                        ),
                        "document_id": (
                            payload.get(
                                "document_id"
                            )
                        ),
                        "filename": (
                            payload.get(
                                "filename"
                            )
                        ),
                        "chunk_id": (
                            chunk_id
                        ),
                        "chunk_index": (
                            payload.get(
                                "chunk_index"
                            )
                        ),
                        "page_number": (
                            payload.get(
                                "page_number"
                            )
                        ),
                        "source_locator": (
                            payload.get(
                                "source_locator"
                            )
                        ),
                        "retrieval_route": (
                            "hybrid"
                        ),
                        "relevance": (
                            score
                        ),
                    }
                )

        graph_count = 0

        if include_graph:
            for index, (
                fact,
                score,
            ) in enumerate(
                ranked_graph[:20],
                start=1,
            ):
                graph_count += 1

                if (
                    fact.source_chunk_id
                    and fact.source_chunk_id
                    not in chunk_ids
                ):
                    chunk_ids.append(
                        fact.source_chunk_id
                    )

                parts.append(
                    f"[Graph Evidence {index}]\n"
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
                    f"Relevance: "
                    f"{score:.4f}\n"
                    f"Evidence: "
                    f"{fact.evidence_text}"
                )

                evidence_items.append(
                    {
                        "label": (
                            f"Graph Evidence {index}"
                        ),
                        "kind": "graph",
                        "text": (
                            fact.evidence_text
                            or fact.source_text
                            or ""
                        ),
                        "document_id": (
                            fact.source_document_id
                        ),
                        "filename": None,
                        "chunk_id": (
                            fact.source_chunk_id
                        ),
                        "chunk_index": None,
                        "page_number": (
                            fact.page_number
                        ),
                        "source_locator": (
                            {
                                "type": (
                                    fact.source_locator_type
                                ),
                                "label": (
                                    fact.source_locator_label
                                ),
                            }
                            if fact.source_locator_label
                            else (
                                {
                                    "type": "page",
                                    "label": (
                                        f"Page "
                                        f"{fact.page_number}"
                                    ),
                                }
                                if fact.page_number
                                else None
                            )
                        ),
                        "retrieval_route": (
                            "graph"
                        ),
                        "relevance": (
                            score
                        ),
                        "graph_fact": {
                            "source": (
                                fact.source_name
                            ),
                            "relationship": (
                                fact.relationship_type
                            ),
                            "target": (
                                fact.target_name
                            ),
                        },
                    }
                )

        if not parts:
            parts.append(
                "No document-scoped retrieval "
                "evidence found."
            )

        return (
            "\n\n".join(parts),
            chunk_ids,
            graph_count,
            evidence_items,
        )

    @staticmethod
    def _grounded_entities(
        ranked_graph,
    ):
        entities = []

        for fact, _ in ranked_graph:
            for name in (
                fact.source_name,
                fact.target_name,
            ):
                if (
                    name
                    and name not in entities
                ):
                    entities.append(
                        name
                    )

        return entities
