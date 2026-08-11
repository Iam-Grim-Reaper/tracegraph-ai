from app.agents.workflow import (
    build_tracegraph_workflow,
)


QUESTIONS = [
    (
        "What accuracy did the "
        "model achieve?"
    ),

    (
        "Who developed Grad-CAM?"
    ),

    (
        "What interpretability method "
        "does ConvNeXt-Small use and "
        "who developed it?"
    ),
]


def main():
    graph = (
        build_tracegraph_workflow()
    )

    for question in QUESTIONS:
        print("\n")
        print("=" * 90)

        print(
            f"QUESTION:\n{question}"
        )

        print("=" * 90)

        result = graph.invoke(
            {
                "question": question,
                "retry_count": 0,
            }
        )

        print(
            "\nROUTE:",
            result[
                "retrieval_route"
            ],
        )

        print(
            "RETRIEVED CHUNKS:",
            len(
                result.get(
                    "retrieved_chunk_ids",
                    [],
                )
            ),
        )

        print(
            "GRAPH FACTS:",
            result.get(
                "graph_fact_count",
                0,
            ),
        )

        print(
            "\nRESEARCH CONTEXT"
        )

        print("-" * 90)

        context = result.get(
            "research_context",
            "",
        )

        print(
            context[:3000]
        )

        if not context.strip():
            raise RuntimeError(
                "Retrieval returned "
                "empty research context"
            )


if __name__ == "__main__":
    main()