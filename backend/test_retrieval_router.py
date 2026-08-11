from app.agents.retrieval_router import (
    RetrievalRouter,
)


QUESTIONS = [
    (
        "What accuracy did the model "
        "achieve?"
    ),
    (
        "Who developed Grad-CAM?"
    ),
    (
        "What dataset was "
        "ConvNeXt-Small evaluated on?"
    ),
    (
        "What interpretability method "
        "does ConvNeXt-Small use and "
        "who developed that method?"
    ),
    (
        "Which models were evaluated "
        "on LC25000 and which one uses "
        "Grad-CAM?"
    ),
    (
        "Summarize the methodology "
        "used in the paper."
    ),
]


def main():
    router = RetrievalRouter()

    print("=" * 80)
    print("TRACEGRAPH RETRIEVAL ROUTER")
    print("=" * 80)

    for question in QUESTIONS:
        decision = router.route(
            question
        )

        print()

        print(
            f"Question:\n{question}"
        )

        print(
            f"\nRoute: "
            f"{decision.route}"
        )

        print(
            f"Reason: "
            f"{decision.reason}"
        )

        print("-" * 80)


if __name__ == "__main__":
    main()