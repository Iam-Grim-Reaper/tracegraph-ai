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
        "\nDRAFT ANSWER:"
    )

    print(
        result.get(
            "draft_answer"
        )
    )

    print(
        "\nVERIFICATION PASSED:"
    )

    print(
        result.get(
            "verification_passed"
        )
    )

    print(
        "\nVERIFICATION REASON:"
    )

    print(
        result.get(
            "verification_reason"
        )
    )

    print(
        "\nUNSUPPORTED CLAIMS:"
    )

    unsupported = result.get(
        "unsupported_claims",
        [],
    )

    if unsupported:
        for claim in unsupported:
            print(
                f"- {claim}"
            )
    else:
        print(
            "None"
        )

    print(
        "\nRETRY COUNT:"
    )

    print(
        result.get(
            "retry_count",
            0,
        )
    )

    rewritten = result.get(
        "rewritten_question"
    )

    if rewritten:
        print(
            "\nREWRITTEN QUESTION:"
        )

        print(
            rewritten
        )

    print(
        "\nFINAL ANSWER"
    )

    print("-" * 90)

    print(
        result.get(
            "final_answer"
        )
    )

    if not result.get(
        "final_answer",
        "",
    ).strip():
        raise RuntimeError(
            "Workflow returned no "
            "final answer"
        )


if __name__ == "__main__":
    main()