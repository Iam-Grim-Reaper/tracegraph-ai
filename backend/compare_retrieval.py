from app.core.config import settings
from app.retrieval.embeddings import GeminiEmbeddingService
from app.retrieval.vector_store import QdrantVectorStore


def print_results(title: str, results):
    print(f"\n{title}")
    print("=" * 80)

    for rank, result in enumerate(results, start=1):
        payload = result.payload or {}

        page_number = payload.get("page_number")
        chunk_index = payload.get("chunk_index")
        filename = payload.get("filename", "Unknown")
        text = payload.get("text", "")

        print(
            f"\nRank {rank}"
            f" | Score: {result.score:.4f}"
            f" | File: {filename}"
            f" | Page: {page_number}"
            f" | Chunk: {chunk_index}"
        )

        print("-" * 80)
        print(text[:500])


def main():
    query = "What is the main topic discussed in this document?"

    embedding_service = GeminiEmbeddingService()

    query_vector = embedding_service.embed_query(query)

    baseline_store = QdrantVectorStore(
        collection_name=settings.qdrant_collection
    )

    contextual_store = QdrantVectorStore(
        collection_name=settings.qdrant_contextual_collection
    )

    baseline_results = baseline_store.search(
        query_vector=query_vector,
        limit=5,
    )

    contextual_results = contextual_store.search(
        query_vector=query_vector,
        limit=5,
    )

    print("\nQUERY")
    print("=" * 80)
    print(query)

    print_results(
        "BASELINE VECTOR RETRIEVAL",
        baseline_results,
    )

    print_results(
        "CONTEXTUAL VECTOR RETRIEVAL",
        contextual_results,
    )


if __name__ == "__main__":
    main()