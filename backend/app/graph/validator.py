from dataclasses import dataclass

from app.graph.models import (
    RelationshipCandidate,
)
from app.graph.ontology import (
    OntologyProfile,
    RESEARCH_ONTOLOGY,
)
from app.graph.schema import (
    EntityType,
    RelationshipType,
)


@dataclass
class RejectedRelationship:
    relationship: RelationshipCandidate
    reason: str


class GraphRelationshipValidator:
    """
    Deterministic semantic validation after
    model extraction.

    Validation occurs at two levels:

    1. Ontology-level validation
       Is this entity/relation legal for the
       active ontology profile?

    2. Semantic validation
       Does the relationship have a valid
       direction/type combination and enough
       evidence?
    """

    def __init__(
        self,
        ontology_profile: (
            OntologyProfile | None
        ) = None,
    ):
        self.ontology_profile = (
            ontology_profile
            or RESEARCH_ONTOLOGY
        )

    def validate(
        self,
        relationship: RelationshipCandidate,
    ) -> tuple[
        bool,
        str | None,
    ]:
        evidence = (
            relationship
            .evidence_text
            .strip()
            .casefold()
        )

        relationship_type = (
            relationship
            .relationship_type
        )

        # =================================================
        # Ontology profile boundary
        # =================================================

        if (
            relationship.source_type
            not in
            self.ontology_profile.entity_types
        ):
            return (
                False,
                (
                    "Source entity type "
                    f"{relationship.source_type.value} "
                    "is not allowed by ontology "
                    f"{self.ontology_profile.name}"
                ),
            )

        if (
            relationship.target_type
            not in
            self.ontology_profile.entity_types
        ):
            return (
                False,
                (
                    "Target entity type "
                    f"{relationship.target_type.value} "
                    "is not allowed by ontology "
                    f"{self.ontology_profile.name}"
                ),
            )

        if (
            relationship_type
            not in
            self.ontology_profile
            .extractable_relationship_types
        ):
            return (
                False,
                (
                    "Relationship type "
                    f"{relationship_type.value} "
                    "is not allowed by ontology "
                    f"{self.ontology_profile.name}"
                ),
            )

        # =================================================
        # Global confidence threshold
        # =================================================

        if relationship.confidence < 0.70:
            return (
                False,
                "Relationship confidence "
                "below 0.70",
            )

        # =================================================
        # Research / Technical
        # =================================================

        if (
            relationship_type
            == RelationshipType.TRAINED_ON
        ):
            if (
                relationship.source_type
                != EntityType.MODEL
            ):
                return (
                    False,
                    "TRAINED_ON source "
                    "must be Model",
                )

            if (
                relationship.target_type
                != EntityType.DATASET
            ):
                return (
                    False,
                    "TRAINED_ON target "
                    "must be Dataset",
                )

            training_cues = (
                "trained on",
                "training data",
                "training dataset",
                "training set",
                "used for training",
            )

            if not any(
                cue in evidence
                for cue
                in training_cues
            ):
                return (
                    False,
                    "TRAINED_ON requires "
                    "explicit training evidence",
                )

        if (
            relationship_type
            == RelationshipType.EVALUATED_ON
        ):
            if (
                relationship.target_type
                != EntityType.DATASET
            ):
                return (
                    False,
                    "EVALUATED_ON target "
                    "must be Dataset",
                )

        if (
            relationship_type
            == RelationshipType.EXPLAINED_BY
        ):
            if (
                relationship.source_type
                != EntityType.MODEL
            ):
                return (
                    False,
                    "EXPLAINED_BY source "
                    "must be Model",
                )

            if (
                relationship.target_type
                != EntityType.METHOD
            ):
                return (
                    False,
                    "EXPLAINED_BY target "
                    "must be Method",
                )

        # =================================================
        # Universal relationships
        # =================================================

        if (
            relationship_type
            == RelationshipType.APPLIES_TO
        ):
            allowed_sources = {
                EntityType.METHOD,
                EntityType.CONCEPT,
                EntityType.POLICY,
                EntityType.REGULATION,
                EntityType.PROCEDURE,
                EntityType.REQUIREMENT,
                EntityType.CLAUSE,
            }

            if (
                relationship.source_type
                not in allowed_sources
            ):
                return (
                    False,
                    "APPLIES_TO source has "
                    "an unsupported entity type",
                )

        if (
            relationship_type
            == RelationshipType.DEVELOPED_BY
        ):
            if (
                relationship.source_type
                == EntityType.PERSON
            ):
                return (
                    False,
                    "DEVELOPED_BY source "
                    "cannot be Person",
                )

            if (
                relationship.target_type
                not in {
                    EntityType.PERSON,
                    EntityType.ORGANIZATION,
                    EntityType.TEAM,
                }
            ):
                return (
                    False,
                    "DEVELOPED_BY target must "
                    "be Person, Organization, "
                    "or Team",
                )

        if (
            relationship_type
            == RelationshipType.DEPENDS_ON
        ):
            dependency_cues = (
                "depends on",
                "dependent on",
                "requires",
                "required for",
                "prerequisite",
                "relies on",
                "reliant on",
            )

            if not any(
                cue in evidence
                for cue
                in dependency_cues
            ):
                return (
                    False,
                    "DEPENDS_ON requires "
                    "explicit dependency evidence",
                )

        # =================================================
        # Career / Resume
        # =================================================

        if (
            relationship_type
            == RelationshipType.WORKED_AT
        ):
            if (
                relationship.source_type
                != EntityType.PERSON
                or
                relationship.target_type
                != EntityType.ORGANIZATION
            ):
                return (
                    False,
                    "WORKED_AT must be "
                    "Person -> Organization",
                )

        if (
            relationship_type
            == RelationshipType.HAS_ROLE
        ):
            if (
                relationship.source_type
                != EntityType.PERSON
                or
                relationship.target_type
                != EntityType.ROLE
            ):
                return (
                    False,
                    "HAS_ROLE must be "
                    "Person -> Role",
                )

        if (
            relationship_type
            == RelationshipType.HAS_SKILL
        ):
            if (
                relationship.source_type
                != EntityType.PERSON
                or
                relationship.target_type
                != EntityType.SKILL
            ):
                return (
                    False,
                    "HAS_SKILL must be "
                    "Person -> Skill",
                )

        if (
            relationship_type
            == RelationshipType.EARNED_DEGREE
        ):
            if (
                relationship.source_type
                != EntityType.PERSON
                or
                relationship.target_type
                != EntityType.DEGREE
            ):
                return (
                    False,
                    "EARNED_DEGREE must be "
                    "Person -> Degree",
                )

        if (
            relationship_type
            == RelationshipType.CERTIFIED_IN
        ):
            if (
                relationship.source_type
                != EntityType.PERSON
                or
                relationship.target_type
                != EntityType.CERTIFICATION
            ):
                return (
                    False,
                    "CERTIFIED_IN must be "
                    "Person -> Certification",
                )

        # =================================================
        # Policy / Compliance
        # =================================================

        if (
            relationship_type
            == RelationshipType.GOVERNED_BY
        ):
            if (
                relationship.target_type
                not in {
                    EntityType.POLICY,
                    EntityType.REGULATION,
                }
            ):
                return (
                    False,
                    "GOVERNED_BY target must "
                    "be Policy or Regulation",
                )

        if (
            relationship_type
            == RelationshipType.HAS_EXCEPTION
        ):
            if (
                relationship.target_type
                != EntityType.EXCEPTION
            ):
                return (
                    False,
                    "HAS_EXCEPTION target "
                    "must be Exception",
                )

        # =================================================
        # Contract / Legal
        # =================================================

        if (
            relationship_type
            == RelationshipType.HAS_OBLIGATION
        ):
            if (
                relationship.source_type
                != EntityType.PARTY
                or
                relationship.target_type
                != EntityType.OBLIGATION
            ):
                return (
                    False,
                    "HAS_OBLIGATION must be "
                    "Party -> Obligation",
                )

        if (
            relationship_type
            == RelationshipType.GRANTS_RIGHT
        ):
            if (
                relationship.target_type
                != EntityType.RIGHT
            ):
                return (
                    False,
                    "GRANTS_RIGHT target "
                    "must be Right",
                )

        if (
            relationship_type
            == RelationshipType.APPLIES_TO_PARTY
        ):
            if (
                relationship.target_type
                != EntityType.PARTY
            ):
                return (
                    False,
                    "APPLIES_TO_PARTY target "
                    "must be Party",
                )

        return (
            True,
            None,
        )

    def filter_relationships(
        self,
        relationships: list[
            RelationshipCandidate
        ],
    ) -> tuple[
        list[RelationshipCandidate],
        list[RejectedRelationship],
    ]:
        accepted: list[
            RelationshipCandidate
        ] = []

        rejected: list[
            RejectedRelationship
        ] = []

        for relationship in relationships:
            is_valid, reason = (
                self.validate(
                    relationship
                )
            )

            if is_valid:
                accepted.append(
                    relationship
                )

            else:
                rejected.append(
                    RejectedRelationship(
                        relationship=(
                            relationship
                        ),
                        reason=(
                            reason
                            or
                            "Unknown validation error"
                        ),
                    )
                )

        return (
            accepted,
            rejected,
        )