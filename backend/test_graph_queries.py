from app.graph.graph_query import (
    GraphQueryRetriever,
)
from app.graph.store import (
    Neo4jGraphStore,
)


QUERIES = [
    (
        "What dataset was "
        "ConvNeXt-Small evaluated on?"
    ),
    (
        "Who developed Grad-CAM?"
    ),
    (
        "Which models were evaluated "
        "on LC25000?"
    ),
    (
        "What method does "
        "ConvNeXt-Small use for "
        "interpretability?"
    ),
    (
        "What did Grad-CAM highlight "
        "for Colon Adenocarcinoma?"
    ),
]


def main():
    store = Neo4jGraphStore()

    try:
        store.verify_connectivity()

        retriever = (
            GraphQueryRetriever(
                store=store
            )
        )

        for query in QUERIES:
            print("\n")
            print("#" * 90)

            print(
                f"QUERY:\n{query}"
            )

            print("#" * 90)

            result = retriever.retrieve(
                query=query,
                max_seed_entities=5,
                max_facts=20,
            )

            print(
                "\nLINKED ENTITIES"
            )

            print("-" * 90)

            if not result.linked_entities:
                print(
                    "No entities linked."
                )

            for entity in (
                result.linked_entities
            ):
                print(
                    f"{entity.name} "
                    f"[{entity.entity_type}] "
                    f"score="
                    f"{entity.match_score}"
                )

            print(
                "\nGRAPH FACTS"
            )

            print("-" * 90)

            if not result.facts:
                print(
                    "No facts retrieved."
                )

            for index, fact in enumerate(
                result.facts,
                start=1,
            ):
                print(
                    f"{index}. "
                    f"{fact.source_name} "
                    f"-[{fact.relationship_type}]-> "
                    f"{fact.target_name}"
                )

                print(
                    f"   Page: "
                    f"{fact.page_number}"
                )

                print(
                    f"   Confidence: "
                    f"{fact.confidence}"
                )

                print(
                    f"   Evidence: "
                    f"{fact.evidence_text}"
                )

            print(
                "\nFORMATTED GRAPH CONTEXT"
            )

            print("-" * 90)

            print(
                retriever.format_context(
                    result
                )
            )

    finally:
        store.close()


if __name__ == "__main__":
    main()