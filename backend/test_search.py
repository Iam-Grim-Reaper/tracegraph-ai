from app.retrieval.embeddings import GeminiEmbeddingService
from app.retrieval.vector_store import QdrantVectorStore


def main():
    query = "What is the main topic discussed in this document?"

    embedding_service = GeminiEmbeddingService()
    vector_store = QdrantVectorStore()

    query_vector = embedding_service.embed_query(query)

    results = vector_store.search(
        query_vector=query_vector,
        limit=5,
    )

    print(f"\nQUERY: {query}")
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


if __name__ == "__main__":
    main()