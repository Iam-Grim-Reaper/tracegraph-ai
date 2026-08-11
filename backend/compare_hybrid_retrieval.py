from app.core.config import settings
from app.retrieval.embeddings import GeminiEmbeddingService
from app.retrieval.hybrid_store import HybridStore
from app.retrieval.vector_store import QdrantVectorStore


def print_results(
    title: str,
    results,
):
    print(f"\n{title}")
    print("=" * 80)

    for rank, result in enumerate(
        results,
        start=1,
    ):
        payload = result.payload or {}

        print(
            f"\nRank {rank}"
            f" | Score: {result.score:.4f}"
            f" | Page: {payload.get('page_number')}"
            f" | Chunk: {payload.get('chunk_index')}"
        )

        print("-" * 80)

        print(
            payload.get(
                "text",
                "",
            )[:500]
        )


def run_query(query: str):
    print("\n\n")
    print("#" * 80)
    print("QUERY:")
    print(query)
    print("#" * 80)

    embeddings = GeminiEmbeddingService()

    query_vector = embeddings.embed_query(
        query
    )

    contextual_store = QdrantVectorStore(
        collection_name=(
            settings.qdrant_contextual_collection
        )
    )

    hybrid_store = HybridStore()

    dense_results = contextual_store.search(
        query_vector=query_vector,
        limit=5,
    )

    lexical_results = (
        hybrid_store.lexical_search(
            query=query,
            limit=5,
        )
    )

    hybrid_results = (
        hybrid_store.hybrid_search(
            query=query,
            dense_vector=query_vector,
            limit=5,
            candidate_limit=20,
        )
    )

    print_results(
        "CONTEXTUAL DENSE",
        dense_results,
    )

    print_results(
        "BM25 LEXICAL",
        lexical_results,
    )

    print_results(
        "HYBRID RRF",
        hybrid_results,
    )


def main():
    queries = [
        (
            "What is the main topic discussed "
            "in this document?"
        ),
        "Macenko stain normalization",
        "Grad-CAM",
    ]

    for query in queries:
        run_query(query)


if __name__ == "__main__":
    main()