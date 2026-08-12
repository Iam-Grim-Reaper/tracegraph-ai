from app.graph.ontology import (
    get_ontology_profile,
)
from app.graph.schema import (
    EntityType,
    RelationshipType,
)


def main():
    print("=" * 70)
    print(
        "TRACEGRAPH ONTOLOGY V2 TEST"
    )
    print("=" * 70)

    research = (
        get_ontology_profile(
            "research"
        )
    )

    career = (
        get_ontology_profile(
            "career"
        )
    )

    policy = (
        get_ontology_profile(
            "policy"
        )
    )

    contract = (
        get_ontology_profile(
            "contract"
        )
    )

    general = (
        get_ontology_profile(
            "general"
        )
    )

    # -----------------------------------------
    # Universal Core should exist everywhere.
    # -----------------------------------------

    for profile in (
        research,
        career,
        policy,
        contract,
        general,
    ):
        assert (
            EntityType.PERSON
            in profile.entity_types
        )

        assert (
            EntityType.ORGANIZATION
            in profile.entity_types
        )

        assert (
            RelationshipType.RELATED_TO
            in profile.relationship_types
        )

        assert (
            RelationshipType.CONTAINS
            not in
            profile
            .extractable_relationship_types
        )

        assert (
            RelationshipType.MENTIONS
            not in
            profile
            .extractable_relationship_types
        )

    # -----------------------------------------
    # Research
    # -----------------------------------------

    assert (
        EntityType.MODEL
        in research.entity_types
    )

    assert (
        EntityType.DATASET
        in research.entity_types
    )

    assert (
        RelationshipType.TRAINED_ON
        in research.relationship_types
    )

    # -----------------------------------------
    # Career
    # -----------------------------------------

    assert (
        EntityType.ROLE
        in career.entity_types
    )

    assert (
        EntityType.SKILL
        in career.entity_types
    )

    assert (
        RelationshipType.WORKED_AT
        in career.relationship_types
    )

    # Research-only semantics should
    # not leak into career.
    assert (
        RelationshipType.TRAINED_ON
        not in career.relationship_types
    )

    # -----------------------------------------
    # Policy
    # -----------------------------------------

    assert (
        EntityType.POLICY
        in policy.entity_types
    )

    assert (
        EntityType.REGULATION
        in policy.entity_types
    )

    assert (
        RelationshipType.PROHIBITS
        in policy.relationship_types
    )

    # -----------------------------------------
    # Contract
    # -----------------------------------------

    assert (
        EntityType.PARTY
        in contract.entity_types
    )

    assert (
        EntityType.OBLIGATION
        in contract.entity_types
    )

    assert (
        RelationshipType.HAS_OBLIGATION
        in contract.relationship_types
    )

    print(
        "\nGeneral:",
        len(
            general.entity_types
        ),
        "entities /",
        len(
            general
            .extractable_relationship_types
        ),
        "extractable relationships",
    )

    print(
        "Research:",
        len(
            research.entity_types
        ),
        "entities /",
        len(
            research
            .extractable_relationship_types
        ),
        "extractable relationships",
    )

    print(
        "Career:",
        len(
            career.entity_types
        ),
        "entities /",
        len(
            career
            .extractable_relationship_types
        ),
        "extractable relationships",
    )

    print(
        "Policy:",
        len(
            policy.entity_types
        ),
        "entities /",
        len(
            policy
            .extractable_relationship_types
        ),
        "extractable relationships",
    )

    print(
        "Contract:",
        len(
            contract.entity_types
        ),
        "entities /",
        len(
            contract
            .extractable_relationship_types
        ),
        "extractable relationships",
    )

    print("\n" + "=" * 70)
    print(
        "ONTOLOGY V2 FOUNDATION VALID"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()