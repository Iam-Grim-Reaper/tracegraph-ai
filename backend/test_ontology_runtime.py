from app.graph.ontology import (
    CAREER_ONTOLOGY,
    POLICY_ONTOLOGY,
    RESEARCH_ONTOLOGY,
)
from app.graph.postprocessor import (
    GraphPostProcessor,
)
from app.graph.validator import (
    GraphRelationshipValidator,
)


def main():
    print("=" * 70)
    print("TRACEGRAPH ONTOLOGY RUNTIME TEST")
    print("=" * 70)

    research_processor = (
        GraphPostProcessor(
            ontology_profile=(
                RESEARCH_ONTOLOGY
            )
        )
    )

    career_processor = (
        GraphPostProcessor(
            ontology_profile=(
                CAREER_ONTOLOGY
            )
        )
    )

    policy_processor = (
        GraphPostProcessor(
            ontology_profile=(
                POLICY_ONTOLOGY
            )
        )
    )

    assert (
        research_processor
        .ontology_profile
        .name
        == "research"
    )

    assert (
        career_processor
        .ontology_profile
        .name
        == "career"
    )

    assert (
        policy_processor
        .ontology_profile
        .name
        == "policy"
    )

    assert isinstance(
        research_processor.validator,
        GraphRelationshipValidator,
    )

    assert (
        research_processor
        .validator
        .ontology_profile
        .name
        == "research"
    )

    assert (
        career_processor
        .validator
        .ontology_profile
        .name
        == "career"
    )

    assert (
        policy_processor
        .validator
        .ontology_profile
        .name
        == "policy"
    )

    print(
        "Research processor: PASS"
    )

    print(
        "Career processor:   PASS"
    )

    print(
        "Policy processor:   PASS"
    )

    print("\n" + "=" * 70)
    print(
        "ONTOLOGY RUNTIME PROPAGATION VALID"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()