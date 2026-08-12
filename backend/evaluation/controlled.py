from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.ingestion.service import IngestionService
from app.models.document import (
    Document,
    DocumentChunk,
)
from app.retrieval.graph_hybrid_retriever import (
    GraphHybridRetriever,
)
from app.retrieval.hybrid_store import HybridStore
from app.retrieval.vector_store import QdrantVectorStore
from evaluation.variants import (
    DenseAdapter,
    FusedAdapter,
    HybridAdapter,
)


EVAL_DENSE_COLLECTION = "tracegraph_eval_dense"
EVAL_HYBRID_COLLECTION = "tracegraph_eval_hybrid"

CORPUS_PATHS = (
    Path("../data/sample.pdf"),
    Path("../data/career_fixture.txt"),
    Path("../data/policy_fixture.txt"),
    Path("../data/contract_fixture.txt"),
    Path("../data/mixed_policy_contract_fixture.txt"),
)

PROVEN_REUSABLE_HYBRID_DOCUMENT_IDS = frozenset(
    {
        "1290eef8-11ec-5161-8f6f-ac5782b76b18",
    }
)


def production_collection_names() -> frozenset[str]:
    return frozenset(
        {
            settings.qdrant_collection,
            settings.qdrant_contextual_collection,
            settings.qdrant_hybrid_collection,
        }
    )


def assert_evaluation_collection(
    collection_name: str,
) -> None:
    if not collection_name.strip():
        raise ValueError(
            "Evaluation collection name cannot be empty."
        )
    if collection_name in production_collection_names():
        raise ValueError(
            "Evaluation collection must not match a "
            "production collection."
        )


@dataclass(frozen=True)
class CorpusDocument:
    document: Document
    chunks: tuple[DocumentChunk, ...]
    source_path: Path


@dataclass(frozen=True)
class ControlledIndexPlan:
    documents: tuple[CorpusDocument, ...]
    dense_embeddings_required: int
    dense_embeddings_reusable: int
    hybrid_contextualizations_required: int
    hybrid_contextualizations_reusable: int
    hybrid_embeddings_required: int
    hybrid_embeddings_reusable: int
    graph_model_calls_required: int
    dense_qdrant_writes: int
    hybrid_qdrant_writes: int
    dense_embedding_api_calls: int
    hybrid_embedding_api_calls: int
    hybrid_contextualization_api_calls: int

    @property
    def document_count(self) -> int:
        return len(self.documents)

    @property
    def chunk_count(self) -> int:
        return sum(
            len(item.chunks)
            for item in self.documents
        )


def load_controlled_corpus(
    paths: tuple[Path, ...] = CORPUS_PATHS,
) -> tuple[CorpusDocument, ...]:
    ingestion = IngestionService(max_chars=1000)
    documents = []
    for path in paths:
        result = ingestion.ingest(path)
        documents.append(
            CorpusDocument(
                document=result.document,
                chunks=tuple(result.chunks),
                source_path=path,
            )
        )
    return tuple(documents)


def build_controlled_index_plan(
    documents: tuple[CorpusDocument, ...],
) -> ControlledIndexPlan:
    reusable_hybrid_chunks = sum(
        len(item.chunks)
        for item in documents
        if str(item.document.id)
        in PROVEN_REUSABLE_HYBRID_DOCUMENT_IDS
    )
    total_chunks = sum(
        len(item.chunks)
        for item in documents
    )
    new_hybrid_chunks = total_chunks - reusable_hybrid_chunks
    documents_requiring_context = sum(
        1
        for item in documents
        if str(item.document.id)
        not in PROVEN_REUSABLE_HYBRID_DOCUMENT_IDS
    )
    dense_embedding_calls = sum(
        (len(item.chunks) + 15) // 16
        for item in documents
    )
    hybrid_embedding_calls = sum(
        (len(item.chunks) + 15) // 16
        for item in documents
        if str(item.document.id)
        not in PROVEN_REUSABLE_HYBRID_DOCUMENT_IDS
    )
    return ControlledIndexPlan(
        documents=documents,
        dense_embeddings_required=total_chunks,
        dense_embeddings_reusable=0,
        hybrid_contextualizations_required=new_hybrid_chunks,
        hybrid_contextualizations_reusable=reusable_hybrid_chunks,
        hybrid_embeddings_required=new_hybrid_chunks,
        hybrid_embeddings_reusable=reusable_hybrid_chunks,
        graph_model_calls_required=0,
        dense_qdrant_writes=total_chunks,
        hybrid_qdrant_writes=total_chunks,
        dense_embedding_api_calls=dense_embedding_calls,
        hybrid_embedding_api_calls=hybrid_embedding_calls,
        hybrid_contextualization_api_calls=(
            documents_requiring_context
        ),
    )


def dense_representation(chunk: DocumentChunk) -> str:
    return chunk.text


def hybrid_representation(chunk: DocumentChunk) -> str:
    if not chunk.contextual_text:
        raise ValueError(
            "Hybrid representation requires contextualized text."
        )
    return chunk.contextual_text


def create_controlled_dense_store() -> QdrantVectorStore:
    assert_evaluation_collection(EVAL_DENSE_COLLECTION)
    return QdrantVectorStore(
        collection_name=EVAL_DENSE_COLLECTION
    )


def create_controlled_hybrid_store() -> HybridStore:
    assert_evaluation_collection(EVAL_HYBRID_COLLECTION)
    return HybridStore(
        collection_name=EVAL_HYBRID_COLLECTION
    )


def create_controlled_fused_retriever(
    graph_store,
) -> GraphHybridRetriever:
    return GraphHybridRetriever(
        graph_store=graph_store,
        hybrid_store=create_controlled_hybrid_store(),
    )


def create_controlled_dense_adapter() -> DenseAdapter:
    assert_evaluation_collection(EVAL_DENSE_COLLECTION)
    return DenseAdapter(
        collection_name=EVAL_DENSE_COLLECTION
    )


def create_controlled_hybrid_adapter() -> HybridAdapter:
    assert_evaluation_collection(EVAL_HYBRID_COLLECTION)
    return HybridAdapter(
        collection_name=EVAL_HYBRID_COLLECTION
    )


def create_controlled_fused_adapter() -> FusedAdapter:
    assert_evaluation_collection(EVAL_HYBRID_COLLECTION)
    return FusedAdapter(
        hybrid_collection_name=EVAL_HYBRID_COLLECTION
    )
