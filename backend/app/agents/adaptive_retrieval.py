import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import perf_counter

from app.agents.state import RetrievalRoute, TraceGraphState
from app.core.config import settings
from app.graph.graph_query import GraphFact, GraphQueryResult, GraphQueryRetriever
from app.graph.store import Neo4jGraphStore
from app.retrieval.embeddings import GeminiEmbeddingService
from app.retrieval.hybrid_store import HybridStore
from app.retrieval.reranker import CrossEncoderReranker


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
        question = state.get("rewritten_question") or state.get("question", "")
        if not question.strip():
            raise ValueError("Question cannot be empty")

        document_ids = state.get("document_ids")
        requires_decomposition = self._requires_decomposition(question)
        query_vector = self.embedding_service.embed_query(question)

        hybrid_error = None
        graph_error = None
        hybrid_latency = None
        graph_latency = None

        def hybrid_probe():
            probe_started = perf_counter()
            result = self.hybrid_store.hybrid_search(
                query=question,
                dense_vector=query_vector,
                limit=settings.adaptive_hybrid_limit,
                candidate_limit=settings.adaptive_hybrid_candidate_limit,
                document_ids=document_ids,
            )
            return result, (perf_counter() - probe_started) * 1000

        def graph_probe():
            probe_started = perf_counter()
            result = self.graph_retriever.retrieve(
                query=question,
                max_seed_entities=settings.adaptive_graph_max_seed_entities,
                max_facts=settings.adaptive_graph_max_facts,
                document_ids=document_ids,
                max_path_depth=2 if requires_decomposition else 1,
            )
            return result, (perf_counter() - probe_started) * 1000

        with ThreadPoolExecutor(max_workers=2) as executor:
            hybrid_future = executor.submit(hybrid_probe)
            graph_future = executor.submit(graph_probe)
            try:
                hybrid_points, hybrid_latency = hybrid_future.result()
            except Exception as exc:
                hybrid_points = []
                hybrid_error = exc
            try:
                graph_result, graph_latency = graph_future.result()
            except Exception as exc:
                graph_result = GraphQueryResult(question, [], [])
                graph_error = exc

        if hybrid_error is not None and graph_error is not None:
            raise RuntimeError(
                "Adaptive retrieval failed because both evidence channels were unavailable."
            ) from hybrid_error

        # A complex question may describe an entity rather than name it.
        # Reuse the already-scoped hybrid evidence chunks as bounded graph
        # provenance seeds instead of adding vocabulary rules or scanning.
        if (
            requires_decomposition
            and graph_error is None
            and not graph_result.facts
            and hybrid_points
        ):
            expansion_started = perf_counter()
            try:
                graph_result = self.graph_retriever.retrieve_by_chunk_ids(
                    query=question,
                    chunk_ids=[str(point.id) for point in hybrid_points],
                    document_ids=document_ids,
                    max_facts=settings.adaptive_graph_max_facts,
                )
                graph_latency = (
                    (graph_latency or 0.0)
                    + (perf_counter() - expansion_started) * 1000
                )
            except Exception as exc:
                graph_error = exc

        hybrid_texts = [
            str((point.payload or {}).get("text", ""))
            for point in hybrid_points
        ]
        graph_texts = [self.verbalize_graph_fact(fact) for fact in graph_result.facts]
        scores = self._get_reranker().score_texts(
            question,
            [*hybrid_texts, *graph_texts],
        )
        hybrid_scores = scores[:len(hybrid_texts)]
        graph_scores = scores[len(hybrid_texts):]

        ranked_hybrid = sorted(
            zip(hybrid_points, hybrid_scores, strict=True),
            key=lambda item: item[1],
            reverse=True,
        )
        ranked_graph = sorted(
            zip(graph_result.facts, graph_scores, strict=True),
            key=lambda item: item[1],
            reverse=True,
        )

        hybrid_signal = self._signal(hybrid_scores)
        graph_signal = self._signal(graph_scores)
        decision = self.arbitrator.decide(
            hybrid_signal,
            graph_signal,
            requires_decomposition,
        )

        degraded = hybrid_error is not None or graph_error is not None
        degradation_reason = None
        if graph_error is not None:
            decision = EvidenceDecision(
                "hybrid",
                "Graph retrieval was unavailable; document evidence was used.",
            )
            degradation_reason = "graph_unavailable"
        elif hybrid_error is not None:
            decision = EvidenceDecision(
                "graph",
                "Document retrieval was unavailable; graph evidence was used.",
            )
            degradation_reason = "hybrid_unavailable"

        if not hybrid_signal.has_evidence and not graph_signal.has_evidence:
            ranked_hybrid = []
            ranked_graph = []

        context, chunk_ids, graph_count = self._compose_context(
            decision.route,
            ranked_hybrid,
            ranked_graph,
        )

        return {
            "retrieval_route": decision.route,
            "initial_route": decision.route,
            "final_route": decision.route,
            "routing_strategy": "adaptive_evidence",
            "routing_reason": decision.reason,
            "research_context": context,
            "retrieved_chunk_ids": chunk_ids,
            "graph_fact_count": graph_count,
            "hybrid_evidence_count": hybrid_signal.candidate_count,
            "graph_evidence_count": graph_signal.candidate_count,
            "hybrid_top_relevance": hybrid_signal.top_relevance,
            "graph_top_relevance": graph_signal.top_relevance,
            "hybrid_mean_relevance": hybrid_signal.mean_top_relevance,
            "graph_mean_relevance": graph_signal.mean_top_relevance,
            "requires_decomposition": requires_decomposition,
            "degraded": degraded,
            "degradation_reason": degradation_reason,
            "query_embedding_call_count": 1,
            "hybrid_probe_latency_ms": hybrid_latency,
            "graph_probe_latency_ms": graph_latency,
            "adaptive_retrieval_latency_ms": (perf_counter() - started) * 1000,
        }

    def _get_reranker(self):
        if self._reranker is None:
            self._reranker = CrossEncoderReranker()
        return self._reranker

    @staticmethod
    def verbalize_graph_fact(fact: GraphFact) -> str:
        evidence = fact.evidence_text or ""
        return (
            f"{fact.source_name} {fact.relationship_type} "
            f"{fact.target_name}. {evidence}"
        ).strip()

    @staticmethod
    def _requires_decomposition(question: str) -> bool:
        normalized = re.sub(r"\s+", " ", question.casefold()).strip()
        request_words = re.findall(r"\b(?:who|what|which|where|when|how)\b", normalized)
        has_join = bool(re.search(r"(?:;|\bthen\b|\band\b)", normalized))
        return len(request_words) >= 2 and has_join

    @staticmethod
    def _signal(scores: list[float]) -> EvidenceSignal:
        if not scores:
            return EvidenceSignal(0, None, None, False)
        ordered = sorted(scores, reverse=True)
        top_values = ordered[:settings.adaptive_evidence_mean_top_k]
        top = ordered[0]
        return EvidenceSignal(
            candidate_count=len(scores),
            top_relevance=top,
            mean_top_relevance=sum(top_values) / len(top_values),
            has_evidence=top >= settings.adaptive_evidence_relevance_threshold,
        )

    @staticmethod
    def _compose_context(route, ranked_hybrid, ranked_graph):
        parts = []
        chunk_ids = []
        include_hybrid = route in {"hybrid", "fused"}
        include_graph = route in {"graph", "fused"}

        if include_hybrid:
            for index, (point, score) in enumerate(ranked_hybrid[:5], start=1):
                payload = point.payload or {}
                chunk_id = str(point.id)
                chunk_ids.append(chunk_id)
                parts.append(
                    f"[Evidence {index}]\nSource: {payload.get('filename', 'Unknown')}\n"
                    f"Page: {payload.get('page_number')}\nChunk: {payload.get('chunk_index')}\n"
                    f"Chunk ID: {chunk_id}\nRerank score: {score:.4f}\n\n"
                    f"{payload.get('text', '')}"
                )

        graph_count = 0
        if include_graph:
            for index, (fact, score) in enumerate(ranked_graph[:20], start=1):
                graph_count += 1
                if fact.source_chunk_id and fact.source_chunk_id not in chunk_ids:
                    chunk_ids.append(fact.source_chunk_id)
                parts.append(
                    f"[Graph Evidence {index}]\n{fact.source_name} "
                    f"-[{fact.relationship_type}]-> {fact.target_name}\n"
                    f"Page: {fact.page_number}\nChunk ID: {fact.source_chunk_id}\n"
                    f"Document ID: {fact.source_document_id}\nConfidence: {fact.confidence}\n"
                    f"Relevance: {score:.4f}\nEvidence: {fact.evidence_text}"
                )

        if not parts:
            parts.append("No document-scoped retrieval evidence found.")
        return "\n\n".join(parts), chunk_ids, graph_count
