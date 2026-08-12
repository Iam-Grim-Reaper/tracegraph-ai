from abc import ABC, abstractmethod
from time import perf_counter

from qdrant_client import models

from app.core.config import settings
from app.graph.graph_query import GraphQueryRetriever
from app.graph.store import Neo4jGraphStore
from app.retrieval.embeddings import GeminiEmbeddingService
from app.retrieval.graph_hybrid_retriever import GraphHybridRetriever
from app.retrieval.hybrid_store import HybridStore
from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.vector_store import QdrantVectorStore
from evaluation.models import (
    Evidence,
    RelationshipEvidence,
    RetrievalResult,
)


VARIANT_NAMES = (
    "dense",
    "hybrid",
    "graph",
    "fused",
)


def _scope_filter(
    document_ids: list[str],
) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="document_id",
                match=models.MatchAny(
                    any=document_ids
                ),
            )
        ]
    )


class VariantAdapter(ABC):
    name: str

    @abstractmethod
    def retrieve(
        self,
        question: str,
        document_ids: list[str],
    ) -> RetrievalResult:
        raise NotImplementedError

    def close(self) -> None:
        return None


class DenseAdapter(VariantAdapter):
    """Original non-contextual dense Qdrant baseline."""

    name = "dense"
    TOP_K = 5

    def __init__(self):
        self.embedding = GeminiEmbeddingService()
        self.store = QdrantVectorStore(
            collection_name=settings.qdrant_collection
        )

    def retrieve(
        self,
        question: str,
        document_ids: list[str],
    ) -> RetrievalResult:
        started = perf_counter()
        embedding_started = perf_counter()
        vector = self.embedding.embed_query(question)
        embedding_latency = (
            perf_counter() - embedding_started
        )
        search_started = perf_counter()
        response = self.store.client.query_points(
            collection_name=self.store.collection_name,
            query=vector,
            query_filter=_scope_filter(document_ids),
            with_payload=True,
            limit=self.TOP_K,
        )
        search_latency = perf_counter() - search_started

        evidence: list[Evidence] = []
        context_parts: list[str] = []
        chunk_ids: list[str] = []
        for index, point in enumerate(
            response.points,
            start=1,
        ):
            payload = point.payload or {}
            chunk_id = str(point.id)
            label = f"Evidence {index}"
            text = str(payload.get("text", ""))
            document_id = payload.get("document_id")
            evidence.append(
                Evidence(
                    label=label,
                    kind="chunk",
                    document_id=document_id,
                    chunk_id=chunk_id,
                    text=text,
                )
            )
            chunk_ids.append(chunk_id)
            context_parts.append(
                f"[{label}]\n"
                f"Source: {payload.get('filename', 'Unknown')}\n"
                f"Page: {payload.get('page_number')}\n"
                f"Chunk ID: {chunk_id}\n\n{text}"
            )

        return RetrievalResult(
            variant=self.name,
            context="\n\n".join(context_parts),
            evidence=evidence,
            chunk_ids=chunk_ids,
            entities=[],
            relationships=[],
            retrieval_latency_seconds=(
                perf_counter() - started
            ),
            stage_latency_seconds={
                "embedding": embedding_latency,
                "dense_search": search_latency,
            },
            limits={"top_k": self.TOP_K},
        )


class HybridAdapter(VariantAdapter):
    name = "hybrid"
    CANDIDATE_LIMIT = 30
    RRF_LIMIT = 15
    TOP_K = 5

    def __init__(self):
        self.embedding = GeminiEmbeddingService()
        self.store = HybridStore()
        self.reranker = CrossEncoderReranker()

    def retrieve(
        self,
        question: str,
        document_ids: list[str],
    ) -> RetrievalResult:
        started = perf_counter()
        embedding_started = perf_counter()
        vector = self.embedding.embed_query(question)
        embedding_latency = (
            perf_counter() - embedding_started
        )
        search_started = perf_counter()
        candidates = self.store.hybrid_search(
            query=question,
            dense_vector=vector,
            limit=self.RRF_LIMIT,
            candidate_limit=self.CANDIDATE_LIMIT,
            document_ids=document_ids,
        )
        search_latency = perf_counter() - search_started
        rerank_started = perf_counter()
        reranked = self.reranker.rerank(
            query=question,
            results=candidates,
            top_k=self.TOP_K,
        ) if candidates else []
        rerank_latency = perf_counter() - rerank_started

        evidence: list[Evidence] = []
        context_parts: list[str] = []
        chunk_ids: list[str] = []
        for index, item in enumerate(reranked, start=1):
            point = item.point
            payload = point.payload or {}
            chunk_id = str(point.id)
            label = f"Evidence {index}"
            text = str(payload.get("text", ""))
            evidence.append(
                Evidence(
                    label=label,
                    kind="chunk",
                    document_id=payload.get("document_id"),
                    chunk_id=chunk_id,
                    text=text,
                )
            )
            chunk_ids.append(chunk_id)
            context_parts.append(
                f"[{label}]\n"
                f"Source: {payload.get('filename', 'Unknown')}\n"
                f"Page: {payload.get('page_number')}\n"
                f"Chunk ID: {chunk_id}\n\n{text}"
            )

        return RetrievalResult(
            variant=self.name,
            context="\n\n".join(context_parts),
            evidence=evidence,
            chunk_ids=chunk_ids,
            entities=[],
            relationships=[],
            retrieval_latency_seconds=(
                perf_counter() - started
            ),
            stage_latency_seconds={
                "embedding": embedding_latency,
                "hybrid_search": search_latency,
                "reranking": rerank_latency,
            },
            limits={
                "candidate_limit": self.CANDIDATE_LIMIT,
                "rrf_limit": self.RRF_LIMIT,
                "top_k": self.TOP_K,
            },
        )


class GraphAdapter(VariantAdapter):
    name = "graph"
    MAX_SEED_ENTITIES = 5
    MAX_FACTS = 20

    def __init__(self):
        self.store = Neo4jGraphStore()
        self.store.verify_connectivity()
        self.retriever = GraphQueryRetriever(self.store)

    def close(self) -> None:
        self.store.close()

    def retrieve(
        self,
        question: str,
        document_ids: list[str],
    ) -> RetrievalResult:
        started = perf_counter()
        result = self.retriever.retrieve(
            query=question,
            max_seed_entities=self.MAX_SEED_ENTITIES,
            max_facts=self.MAX_FACTS,
            document_ids=document_ids,
        )
        retrieval_latency = perf_counter() - started
        evidence: list[Evidence] = []
        relationships: list[RelationshipEvidence] = []
        context_parts: list[str] = []
        chunk_ids: list[str] = []
        for index, fact in enumerate(result.facts, start=1):
            label = f"Graph Evidence {index}"
            text = (
                f"{fact.source_name} "
                f"-[{fact.relationship_type}]-> "
                f"{fact.target_name}\n"
                f"Evidence: {fact.evidence_text}"
            )
            evidence.append(
                Evidence(
                    label=label,
                    kind="graph",
                    document_id=fact.source_document_id,
                    chunk_id=fact.source_chunk_id,
                    text=text,
                )
            )
            relationships.append(
                RelationshipEvidence(
                    source=fact.source_name,
                    relationship=fact.relationship_type,
                    target=fact.target_name,
                    document_id=fact.source_document_id,
                    chunk_id=fact.source_chunk_id,
                )
            )
            if fact.source_chunk_id:
                chunk_ids.append(fact.source_chunk_id)
            context_parts.append(f"[{label}]\n{text}")

        return RetrievalResult(
            variant=self.name,
            context="\n\n".join(context_parts),
            evidence=evidence,
            chunk_ids=list(dict.fromkeys(chunk_ids)),
            entities=list(
                dict.fromkeys(
                    [item.name for item in result.linked_entities]
                    + [fact.source_name for fact in result.facts]
                    + [fact.target_name for fact in result.facts]
                )
            ),
            relationships=relationships,
            retrieval_latency_seconds=retrieval_latency,
            stage_latency_seconds={
                "graph_retrieval": retrieval_latency
            },
            limits={
                "max_seed_entities": self.MAX_SEED_ENTITIES,
                "max_facts": self.MAX_FACTS,
            },
        )


class FusedAdapter(VariantAdapter):
    name = "fused"
    TOP_K = 5
    QDRANT_LIMIT = 20
    QDRANT_CANDIDATE_LIMIT = 30
    GRAPH_MAX_SEED_ENTITIES = 5
    GRAPH_MAX_FACTS = 20
    MAX_FUSED_CANDIDATES = 25

    def __init__(self):
        self.store = Neo4jGraphStore()
        self.store.verify_connectivity()
        self.retriever = GraphHybridRetriever(self.store)

    def close(self) -> None:
        self.store.close()

    def retrieve(
        self,
        question: str,
        document_ids: list[str],
    ) -> RetrievalResult:
        started = perf_counter()
        result = self.retriever.retrieve(
            query=question,
            top_k=self.TOP_K,
            qdrant_limit=self.QDRANT_LIMIT,
            qdrant_candidate_limit=self.QDRANT_CANDIDATE_LIMIT,
            graph_max_seed_entities=self.GRAPH_MAX_SEED_ENTITIES,
            graph_max_facts=self.GRAPH_MAX_FACTS,
            max_fused_candidates=self.MAX_FUSED_CANDIDATES,
            document_ids=document_ids,
        )
        retrieval_latency = perf_counter() - started
        evidence: list[Evidence] = []
        context_parts: list[str] = []
        chunk_ids: list[str] = []
        relationships: list[RelationshipEvidence] = []

        payload_points = (
            self.retriever.hybrid_store.retrieve_by_ids(
                [chunk.chunk_id for chunk in result.chunks]
            )
        )
        document_by_chunk = {
            str(point.id): (point.payload or {}).get("document_id")
            for point in payload_points
        }

        for index, chunk in enumerate(result.chunks, start=1):
            label = f"Evidence {index}"
            evidence.append(
                Evidence(
                    label=label,
                    kind="chunk",
                    document_id=document_by_chunk.get(
                        chunk.chunk_id
                    ),
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                )
            )
            chunk_ids.append(chunk.chunk_id)
            context_parts.append(
                f"[{label}]\nSource: {chunk.filename}\n"
                f"Page: {chunk.page_number}\n"
                f"Chunk ID: {chunk.chunk_id}\n\n{chunk.text}"
            )

        for index, fact in enumerate(result.graph_facts, start=1):
            label = f"Graph Evidence {index}"
            text = (
                f"{fact.source_name} "
                f"-[{fact.relationship_type}]-> "
                f"{fact.target_name}\n"
                f"Evidence: {fact.evidence_text}"
            )
            evidence.append(
                Evidence(
                    label=label,
                    kind="graph",
                    document_id=fact.source_document_id,
                    chunk_id=fact.source_chunk_id,
                    text=text,
                )
            )
            relationships.append(
                RelationshipEvidence(
                    source=fact.source_name,
                    relationship=fact.relationship_type,
                    target=fact.target_name,
                    document_id=fact.source_document_id,
                    chunk_id=fact.source_chunk_id,
                )
            )
            if fact.source_chunk_id:
                chunk_ids.append(fact.source_chunk_id)
            context_parts.append(f"[{label}]\n{text}")

        return RetrievalResult(
            variant=self.name,
            context="\n\n".join(context_parts),
            evidence=evidence,
            chunk_ids=list(dict.fromkeys(chunk_ids)),
            entities=list(
                dict.fromkeys(
                    [item.name for item in result.linked_entities]
                    + [fact.source_name for fact in result.graph_facts]
                    + [fact.target_name for fact in result.graph_facts]
                )
            ),
            relationships=relationships,
            retrieval_latency_seconds=retrieval_latency,
            stage_latency_seconds={
                "fused_retrieval": retrieval_latency
            },
            limits={
                "top_k": self.TOP_K,
                "qdrant_limit": self.QDRANT_LIMIT,
                "qdrant_candidate_limit": self.QDRANT_CANDIDATE_LIMIT,
                "graph_max_seed_entities": self.GRAPH_MAX_SEED_ENTITIES,
                "graph_max_facts": self.GRAPH_MAX_FACTS,
                "max_fused_candidates": self.MAX_FUSED_CANDIDATES,
            },
        )


def create_adapter(name: str) -> VariantAdapter:
    adapters = {
        "dense": DenseAdapter,
        "hybrid": HybridAdapter,
        "graph": GraphAdapter,
        "fused": FusedAdapter,
    }
    try:
        return adapters[name]()
    except KeyError as exc:
        raise ValueError(
            f"Unknown evaluation variant: {name}"
        ) from exc
