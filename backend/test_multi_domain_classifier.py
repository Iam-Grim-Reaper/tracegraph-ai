from pathlib import Path

from app.graph.ontology_classifier import (
    OntologyClassifier,
)
from app.ingestion.service import (
    IngestionService,
)


MIXED_PATH = Path(
    "../data/mixed_policy_contract_fixture.txt"
)

POLICY_PATH = Path(
    "../data/policy_fixture.txt"
)

CONTRACT_PATH = Path(
    "../data/contract_fixture.txt"
)


def classify_file(
    path: Path,
):
    ingestion = (
        IngestionService(
            max_chars=1000
        )
        .ingest(
            path
        )
    )

    document = (
        ingestion.document
    )

    document_text = (
        "\n\n".join(
            chunk.text
            for chunk
            in ingestion.chunks
            if chunk.text.strip()
        )
    )

    classifier = (
        OntologyClassifier(
            enable_llm_fallback=False
        )
    )

    return (
        classifier.classify(
            document=document,
            document_text=document_text,
        )
    )


def main():
    print("=" * 70)

    print(
        "TRACEGRAPH MULTI-DOMAIN "
        "CLASSIFIER TEST"
    )

    print("=" * 70)

    # =================================================
    # Mixed policy + contract
    # =================================================

    mixed = (
        classify_file(
            MIXED_PATH
        )
    )

    print(
        "\nMixed profile:",
        mixed.profile.name,
    )

    print(
        "Selected profiles:",
        mixed.selected_profiles,
    )

    print(
        "Confidence:",
        f"{mixed.confidence:.2f}",
    )

    print(
        "Method:",
        mixed.method,
    )

    print(
        "Scores:",
        mixed.scores,
    )

    if (
        mixed.profile.name
        != "policy+contract"
    ):
        raise RuntimeError(
            "Expected mixed document "
            "to classify as "
            "policy+contract, received "
            f"'{mixed.profile.name}'."
        )

    if (
        mixed.selected_profiles
        != (
            "policy",
            "contract",
        )
    ):
        raise RuntimeError(
            "Mixed document did not "
            "select policy and contract."
        )

    # =================================================
    # Pure policy must remain policy
    # =================================================

    policy = (
        classify_file(
            POLICY_PATH
        )
    )

    print(
        "\nPolicy fixture:",
        policy.profile.name,
    )

    print(
        "Policy scores:",
        policy.scores,
    )

    if (
        policy.profile.name
        != "policy"
    ):
        raise RuntimeError(
            "Pure policy fixture was "
            "incorrectly composed as "
            f"'{policy.profile.name}'."
        )

    # =================================================
    # Pure contract must remain contract
    #
    # Existing contract scores were roughly:
    #
    # policy   = 12
    # contract = 62
    #
    # The relative threshold should prevent
    # accidental composition.
    # =================================================

    contract = (
        classify_file(
            CONTRACT_PATH
        )
    )

    print(
        "\nContract fixture:",
        contract.profile.name,
    )

    print(
        "Contract scores:",
        contract.scores,
    )

    if (
        contract.profile.name
        != "contract"
    ):
        raise RuntimeError(
            "Pure contract fixture was "
            "incorrectly composed as "
            f"'{contract.profile.name}'."
        )

    print(
        "\n" + "=" * 70
    )

    print(
        "MULTI-DOMAIN CLASSIFIER VALID"
    )

    print("=" * 70)

    print(
        "Policy + Contract:      PASS"
    )

    print(
        "Pure Policy preserved:  PASS"
    )

    print(
        "Pure Contract preserved: PASS"
    )


if __name__ == "__main__":
    main()