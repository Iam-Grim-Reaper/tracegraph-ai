from app.agents.workflow import (
    build_tracegraph_workflow,
)


def main():
    graph = (
        build_tracegraph_workflow()
    )

    questions = [
        (
            "What accuracy did the "
            "model achieve?"
        ),
        (
            "Who developed Grad-CAM?"
        ),
        (
            "What interpretability "
            "method does ConvNeXt-Small "
            "use and who developed it?"
        ),
    ]

    for question in questions:
        print("\n" + "=" * 80)

        print(
            f"QUESTION:\n{question}"
        )

        result = graph.invoke(
            {
                "question": question,
                "retry_count": 0,
            }
        )

        print(
            "\nRoute:",
            result[
                "retrieval_route"
            ],
        )

        print(
            "Reason:",
            result[
                "routing_reason"
            ],
        )

        print(
            "Path result:",
            result[
                "research_context"
            ],
        )


if __name__ == "__main__":
    main()