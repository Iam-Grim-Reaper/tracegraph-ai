from app.retrieval.embeddings import (
    GeminiEmbeddingService,
)
from app.retrieval.hybrid_store import (
    HybridStore,
)
from app.retrieval.reranker import (
    CrossEncoderReranker,
)


def print_hybrid_results(results):
    print("\nHYBRID RRF BEFORE RERANKING")
    print("=" * 80)

    for rank, result in enumerate(
        results,
        start=1,
    ):
        payload = result.payload or {}

        print(
            f"\nRank {rank}"
            f" | RRF Score: {result.score:.4f}"
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


def print_reranked_results(results):
    print("\nRERANKED RESULTS")
    print("=" * 80)

    for rank, item in enumerate(
        results,
        start=1,
    ):
        result = item.point
        payload = result.payload or {}

        print(
            f"\nRank {rank}"
            f" | Rerank Score: "
            f"{item.rerank_score:.4f}"
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


def main():
    queries = [
        (
            "What is the main topic discussed "
            "in this document?"
        ),
        (
            "What does Grad-CAM show "
            "in this system?"
        ),
        (
            "Why is Macenko stain "
            "normalization used?"
        ),
    ]

    embeddings = GeminiEmbeddingService()
    hybrid_store = HybridStore()

    reranker = CrossEncoderReranker()

    for query in queries:
        print("\n\n")
        print("#" * 80)
        print("QUERY:")
        print(query)
        print("#" * 80)

        query_vector = (
            embeddings.embed_query(query)
        )

        # Retrieve more candidates than we
        # eventually give to the LLM.
        hybrid_results = (
            hybrid_store.hybrid_search(
                query=query,
                dense_vector=query_vector,
                limit=10,
                candidate_limit=20,
            )
        )

        reranked_results = (
            reranker.rerank(
                query=query,
                results=hybrid_results,
                top_k=5,
            )
        )

        print_hybrid_results(
            hybrid_results
        )

        print_reranked_results(
            reranked_results
        )


if __name__ == "__main__":
    main()