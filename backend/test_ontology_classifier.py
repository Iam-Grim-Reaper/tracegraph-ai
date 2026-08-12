from app.graph.ontology_classifier import (
    OntologyClassifier,
)


def classify_text(
    classifier: OntologyClassifier,
    text: str,
):
    scores = (
        classifier._score_profiles(
            text
        )
    )

    return max(
        scores,
        key=scores.get,
    ), scores


def main():
    print("=" * 70)
    print(
        "TRACEGRAPH ONTOLOGY "
        "CLASSIFIER TEST"
    )
    print("=" * 70)

    classifier = (
        OntologyClassifier(
            enable_llm_fallback=False
        )
    )

    research_text = """
    Abstract

    We evaluate a deep learning model on
    multiple datasets. The model was trained
    on the training dataset and benchmarked
    using accuracy, precision, recall and F1
    score. Experimental results are discussed
    in the methodology and evaluation section.
    References include Smith et al.
    """

    career_text = """
    Resume

    Professional Experience

    Senior Data Engineer

    Technical Skills:
    Python, Spark, SQL, Azure

    Education:
    Master of Science

    Certifications:
    Microsoft Azure certification
    """

    policy_text = """
    Information Security Policy

    This policy establishes regulatory and
    compliance requirements. All personnel
    must comply with security controls and
    procedures. The organization follows GDPR
    data protection requirements.
    """

    contract_text = """
    Services Agreement

    This contract is entered into by the
    parties on the effective date.

    The parties agree to the obligations,
    confidentiality requirements, governing
    law, liability provisions and termination
    clauses contained in this agreement.
    """

    cases = {
        "research": research_text,
        "career": career_text,
        "policy": policy_text,
        "contract": contract_text,
    }

    for expected, text in cases.items():
        detected, scores = (
            classify_text(
                classifier,
                text,
            )
        )

        print(
            f"\nExpected: {expected}"
        )

        print(
            f"Detected: {detected}"
        )

        print(
            "Scores:",
            scores,
        )

        assert (
            detected
            == expected
        )

    print(
        "\n" + "=" * 70
    )

    print(
        "ONTOLOGY CLASSIFIER "
        "DETERMINISTIC TEST VALID"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()