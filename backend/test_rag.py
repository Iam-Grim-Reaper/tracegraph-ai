from app.retrieval.rag import BaselineRAGService


def main():
    question = (
        "What is the main topic discussed "
        "in this document?"
    )

    rag = BaselineRAGService()

    result = rag.answer(
        question=question,
        top_k=5,
    )

    print("\nQUESTION")
    print("=" * 80)
    print(question)

    print("\nANSWER")
    print("=" * 80)
    print(result["answer"])

    print("\nSOURCES")
    print("=" * 80)

    for source in result["sources"]:
        print(
            f"[{source['id']}] "
            f"{source['filename']} "
            f"| Page {source['page_number']} "
            f"| Chunk {source['chunk_index']} "
            f"| Score {source['score']:.4f}"
        )


if __name__ == "__main__":
    main()