from app.graph.store import (
    Neo4jGraphStore,
)
from app.retrieval.graph_hybrid_retriever import (
    GraphHybridRetriever,
)


QUERIES = [
    (
        "What interpretability method "
        "does ConvNeXt-Small use, and "
        "who developed that method?"
    ),
    (
        "Which models were evaluated "
        "on LC25000 and which one uses "
        "Grad-CAM?"
    ),
    (
        "What did Grad-CAM reveal for "
        "Colon Adenocarcinoma?"
    ),
]


def main():
    store = Neo4jGraphStore()

    try:
        store.verify_connectivity()

        retriever = (
            GraphHybridRetriever(
                graph_store=store
            )
        )

        for query in QUERIES:
            print("\n")
            print("=" * 90)

            print(
                f"QUERY:\n{query}"
            )

            print("=" * 90)

            result = (
                retriever.retrieve(
                    query=query,
                    top_k=5,
                    qdrant_limit=20,
                    qdrant_candidate_limit=30,
                    graph_max_facts=30,
                    max_fused_candidates=25,
                )
            )

            print(
                "\nLINKED GRAPH ENTITIES"
            )

            print("-" * 90)

            if not result.linked_entities:
                print(
                    "No graph entities linked."
                )

            for entity in (
                result.linked_entities
            ):
                print(
                    f"{entity.name} "
                    f"[{entity.entity_type}]"
                )

            print(
                "\nTOP FUSED CHUNKS"
            )

            print("-" * 90)

            for index, chunk in enumerate(
                result.chunks,
                start=1,
            ):
                print()

                print(
                    f"{index}. "
                    f"Chunk {chunk.chunk_index}"
                )

                print(
                    f"   ID: "
                    f"{chunk.chunk_id}"
                )

                print(
                    f"   Page: "
                    f"{chunk.page_number}"
                )

                print(
                    f"   Hybrid score: "
                    f"{chunk.hybrid_score}"
                )

                print(
                    f"   Pre-fusion score: "
                    f"{chunk.pre_fusion_score:.4f}"
                )

                print(
                    f"   Rerank score: "
                    f"{chunk.rerank_score:.4f}"
                )

                print(
                    f"   Graph supported: "
                    f"{chunk.graph_supported}"
                )

                print(
                    f"   Graph fact count: "
                    f"{chunk.graph_fact_count}"
                )

                if chunk.graph_evidence:
                    print(
                        "   Graph evidence:"
                    )

                    for evidence in (
                        chunk.graph_evidence
                    ):
                        print(
                            f"      - "
                            f"{evidence}"
                        )

                preview = (
                    chunk.text
                    .replace(
                        "\n",
                        " ",
                    )
                    [:300]
                )

                print(
                    f"   Text: "
                    f"{preview}..."
                )

    finally:
        store.close()


if __name__ == "__main__":
    main()