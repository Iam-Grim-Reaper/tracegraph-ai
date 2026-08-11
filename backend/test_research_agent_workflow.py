from app.agents.workflow import (
    build_tracegraph_workflow,
)


def main():
    graph = (
        build_tracegraph_workflow()
    )

    question = (
        "What interpretability method "
        "does ConvNeXt-Small use and "
        "who developed it?"
    )

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
        "\nROUTE:"
    )

    print(
        result.get(
            "retrieval_route"
        )
    )

    print(
        "\nRETRIEVED CHUNKS:"
    )

    print(
        len(
            result.get(
                "retrieved_chunk_ids",
                [],
            )
        )
    )

    print(
        "\nGRAPH FACTS:"
    )

    print(
        result.get(
            "graph_fact_count",
            0,
        )
    )

    print(
        "\nDRAFT ANSWER"
    )

    print("-" * 90)

    print(
        result.get(
            "draft_answer"
        )
    )

    print(
        "\nUSED EVIDENCE"
    )

    print("-" * 90)

    for label in result.get(
        "used_evidence_labels",
        [],
    ):
        print(
            f"- {label}"
        )

    if not result.get(
        "draft_answer",
        "",
    ).strip():
        raise RuntimeError(
            "Research Agent returned "
            "no answer"
        )


if __name__ == "__main__":
    main()