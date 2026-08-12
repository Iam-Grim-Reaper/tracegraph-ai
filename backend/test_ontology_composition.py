from app.graph.ontology import (
    GENERAL_ONTOLOGY,
    POLICY_ONTOLOGY,
    RelationshipType,
    EntityType,
    compose_ontology_profiles,
)


def main():
    print("=" * 70)
    print(
        "TRACEGRAPH ONTOLOGY "
        "COMPOSITION TEST"
    )
    print("=" * 70)

    # =================================================
    # 1. Empty composition -> general
    # =================================================

    general = (
        compose_ontology_profiles(
            []
        )
    )

    print(
        "\nEmpty composition:",
        general.name,
    )

    assert (
        general
        is GENERAL_ONTOLOGY
    )

    # =================================================
    # 2. Single profile remains canonical
    # =================================================

    policy = (
        compose_ontology_profiles(
            ["policy"]
        )
    )

    print(
        "Single composition:",
        policy.name,
    )

    assert (
        policy
        is POLICY_ONTOLOGY
    )

    # =================================================
    # 3. Policy + Contract
    # =================================================

    policy_contract = (
        compose_ontology_profiles(
            [
                "policy",
                "contract",
            ]
        )
    )

    print(
        "\nComposed profile:",
        policy_contract.name,
    )

    print(
        "Version:",
        policy_contract.version,
    )

    print(
        "Entity count:",
        len(
            policy_contract.entity_types
        ),
    )

    print(
        "Relationship count:",
        len(
            policy_contract
            .relationship_types
        ),
    )

    assert (
        policy_contract.name
        == "policy+contract"
    )

    # Policy entities
    assert (
        EntityType.POLICY
        in policy_contract.entity_types
    )

    assert (
        EntityType.REGULATION
        in policy_contract.entity_types
    )

    assert (
        EntityType.CONTROL
        in policy_contract.entity_types
    )

    # Contract entities
    assert (
        EntityType.CLAUSE
        in policy_contract.entity_types
    )

    assert (
        EntityType.OBLIGATION
        in policy_contract.entity_types
    )

    assert (
        EntityType.RIGHT
        in policy_contract.entity_types
    )

    # Policy relationships
    assert (
        RelationshipType.GOVERNED_BY
        in policy_contract
        .relationship_types
    )

    assert (
        RelationshipType.HAS_EXCEPTION
        in policy_contract
        .relationship_types
    )

    # Contract relationships
    assert (
        RelationshipType.HAS_OBLIGATION
        in policy_contract
        .relationship_types
    )

    assert (
        RelationshipType.GRANTS_RIGHT
        in policy_contract
        .relationship_types
    )

    assert (
        RelationshipType.TERMINATES_ON
        in policy_contract
        .relationship_types
    )

    # Shared relationship
    assert (
        RelationshipType.REQUIRES
        in policy_contract
        .relationship_types
    )

    # =================================================
    # 4. Composition must be order-independent
    # =================================================

    reversed_composition = (
        compose_ontology_profiles(
            [
                "contract",
                "policy",
            ]
        )
    )

    print(
        "\nReverse-order profile:",
        reversed_composition.name,
    )

    assert (
        reversed_composition.name
        == policy_contract.name
    )

    assert (
        reversed_composition.entity_types
        == policy_contract.entity_types
    )

    assert (
        reversed_composition.relationship_types
        == policy_contract.relationship_types
    )

    # =================================================
    # 5. Duplicate profile names should collapse
    # =================================================

    duplicates = (
        compose_ontology_profiles(
            [
                "policy",
                "policy",
                "contract",
                "contract",
            ]
        )
    )

    assert (
        duplicates.name
        == "policy+contract"
    )

    # =================================================
    # 6. GENERAL should not alter a specialized
    #    composition.
    # =================================================

    with_general = (
        compose_ontology_profiles(
            [
                "general",
                "policy",
                "contract",
            ]
        )
    )

    assert (
        with_general.name
        == "policy+contract"
    )

    assert (
        with_general.entity_types
        == policy_contract.entity_types
    )

    # =================================================
    # 7. Research + Career
    # =================================================

    research_career = (
        compose_ontology_profiles(
            [
                "research",
                "career",
            ]
        )
    )

    print(
        "\nSecond composition:",
        research_career.name,
    )

    assert (
        research_career.name
        == "research+career"
    )

    assert (
        EntityType.MODEL
        in research_career.entity_types
    )

    assert (
        EntityType.SKILL
        in research_career.entity_types
    )

    assert (
        RelationshipType.EVALUATED_ON
        in research_career
        .relationship_types
    )

    assert (
        RelationshipType.HAS_SKILL
        in research_career
        .relationship_types
    )

    # =================================================
    # 8. Invalid profile must fail cleanly
    # =================================================

    try:
        compose_ontology_profiles(
            [
                "policy",
                "not-a-real-profile",
            ]
        )

    except ValueError:
        invalid_profile_rejected = True

    else:
        invalid_profile_rejected = False

    assert (
        invalid_profile_rejected
    )

    # =================================================
    # Success
    # =================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "ONTOLOGY COMPOSITION VALID"
    )

    print("=" * 70)

    print(
        "General fallback:            PASS"
    )

    print(
        "Single-profile identity:     PASS"
    )

    print(
        "Policy + Contract union:     PASS"
    )

    print(
        "Canonical composition name:  PASS"
    )

    print(
        "Order independence:          PASS"
    )

    print(
        "Duplicate elimination:       PASS"
    )

    print(
        "Research + Career union:     PASS"
    )

    print(
        "Invalid profile rejection:   PASS"
    )


if __name__ == "__main__":
    main()