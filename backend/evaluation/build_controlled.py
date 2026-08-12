"""Build isolated, matched-corpus evaluation indexes."""

import argparse
from dataclasses import dataclass

from qdrant_client import models

from app.core.config import settings
from app.retrieval.contextualizer import Contextualizer
from app.retrieval.embeddings import GeminiEmbeddingService
from app.retrieval.hybrid_store import HybridStore
from app.retrieval.vector_store import QdrantVectorStore
from evaluation.controlled import (
    EVAL_DENSE_COLLECTION,
    EVAL_HYBRID_COLLECTION,
    PROVEN_REUSABLE_HYBRID_DOCUMENT_IDS,
    ControlledIndexPlan,
    assert_evaluation_collection,
    assert_non_destructive,
    build_controlled_index_plan,
    dense_representation,
    hybrid_representation,
    load_controlled_corpus,
)


@dataclass(frozen=True)
class BuildResult:
    dense_points_written: int
    hybrid_points_written: int


def format_plan(plan: ControlledIndexPlan) -> str:
    lines = (
        f"documents: {plan.document_count}",
        f"chunks: {plan.chunk_count}",
        f"dense vectors required: {plan.dense_embeddings_required}",
        "hybrid vectors/context payloads reusable: "
        f"{plan.hybrid_embeddings_reusable}",
        "hybrid chunks requiring contextualization/embedding: "
        f"{plan.hybrid_embeddings_required}",
        f"graph/model extraction calls: {plan.graph_model_calls_required}",
        f"dense point writes: {plan.dense_qdrant_writes}",
        f"hybrid point writes: {plan.hybrid_qdrant_writes}",
        "estimated dense embedding API calls: "
        f"{plan.dense_embedding_api_calls}",
        "estimated hybrid embedding API calls: "
        f"{plan.hybrid_embedding_api_calls}",
        "estimated contextualization calls: "
        f"{plan.hybrid_contextualization_api_calls}",
        f"estimated total provider calls: {plan.total_provider_calls}",
    )
    return "\n".join(lines)


def _copy_reusable_hybrid_points(
    source: HybridStore,
    target: HybridStore,
    chunk_ids: list[str],
) -> int:
    points = source.client.retrieve(
        collection_name=source.collection_name,
        ids=chunk_ids,
        with_payload=True,
        with_vectors=True,
    )
    by_id = {str(point.id): point for point in points}
    if set(by_id) != set(chunk_ids):
        missing = sorted(set(chunk_ids) - set(by_id))
        raise RuntimeError(
            "Verified reusable hybrid points are missing: "
            + ", ".join(missing)
        )

    copied = []
    for chunk_id in chunk_ids:
        point = by_id[chunk_id]
        payload = dict(point.payload or {})
        vectors = point.vector
        if (
            payload.get("chunk_id") != chunk_id
            or not payload.get("contextual_text")
            or not isinstance(vectors, dict)
            or HybridStore.DENSE_VECTOR_NAME not in vectors
            or HybridStore.BM25_VECTOR_NAME not in vectors
        ):
            raise RuntimeError(
                f"Hybrid point {chunk_id} is not safely reusable."
            )
        copied.append(
            models.PointStruct(
                id=chunk_id,
                vector=vectors,
                payload=payload,
            )
        )

    target.client.upsert(
        collection_name=target.collection_name,
        points=copied,
        wait=True,
    )
    return len(copied)


def build_controlled_indexes(
    *,
    dense_collection: str = EVAL_DENSE_COLLECTION,
    hybrid_collection: str = EVAL_HYBRID_COLLECTION,
    recreate: bool = False,
) -> BuildResult:
    assert_evaluation_collection(dense_collection)
    assert_evaluation_collection(hybrid_collection)
    assert_non_destructive(recreate)
    if dense_collection != EVAL_DENSE_COLLECTION:
        raise ValueError("Dense collection name must be the controlled default.")
    if hybrid_collection != EVAL_HYBRID_COLLECTION:
        raise ValueError("Hybrid collection name must be the controlled default.")

    corpus = load_controlled_corpus()
    dense_store = QdrantVectorStore(collection_name=dense_collection)
    hybrid_store = HybridStore(collection_name=hybrid_collection)
    source_hybrid = HybridStore(
        collection_name=settings.qdrant_hybrid_collection
    )
    embedding = GeminiEmbeddingService()
    contextualizer = Contextualizer()

    # ensure_collection creates only missing evaluation collections and
    # deliberately reuses existing ones on an idempotent rerun.
    dense_store.ensure_collection()
    hybrid_store.ensure_collection()

    dense_written = 0
    for item in corpus:
        texts = [dense_representation(chunk) for chunk in item.chunks]
        vectors = embedding.embed_documents(
            texts=texts,
            title=item.document.metadata.title,
        )
        dense_store.upsert_chunks(
            document=item.document,
            chunks=list(item.chunks),
            embeddings=vectors,
        )
        dense_written += len(item.chunks)

    reusable_ids = [
        str(chunk.id)
        for item in corpus
        if str(item.document.id) in PROVEN_REUSABLE_HYBRID_DOCUMENT_IDS
        for chunk in item.chunks
    ]
    hybrid_written = _copy_reusable_hybrid_points(
        source_hybrid,
        hybrid_store,
        reusable_ids,
    )

    for item in corpus:
        if str(item.document.id) in PROVEN_REUSABLE_HYBRID_DOCUMENT_IDS:
            continue
        document_text = item.source_path.read_text(encoding="utf-8")
        chunks = contextualizer.contextualize_chunks(
            document=item.document,
            chunks=list(item.chunks),
            document_text=document_text,
        )
        texts = [hybrid_representation(chunk) for chunk in chunks]
        vectors = embedding.embed_documents(
            texts=texts,
            title=item.document.metadata.title,
        )
        hybrid_store.upsert_chunks(item.document, chunks, vectors)
        hybrid_written += len(chunks)

    return BuildResult(dense_written, hybrid_written)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build isolated TraceGraph controlled indexes."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Always refused; evaluation indexes are non-destructive.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    corpus = load_controlled_corpus()
    plan = build_controlled_index_plan(corpus)
    assert_non_destructive(args.recreate)
    print("CONTROLLED MATCHED-CORPUS INDEX PLAN")
    print(f"dense collection: {EVAL_DENSE_COLLECTION}")
    print(f"hybrid collection: {EVAL_HYBRID_COLLECTION}")
    print(format_plan(plan))
    if args.dry_run:
        print("DRY RUN: no collections created and no provider calls made.")
        return 0
    result = build_controlled_indexes()
    print(f"dense points written: {result.dense_points_written}")
    print(f"hybrid points written: {result.hybrid_points_written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
