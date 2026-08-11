from dataclasses import dataclass

from app.graph.models import (
    RelationshipCandidate,
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
    def validate(
        self,
        relationship: RelationshipCandidate,
    ) -> tuple[bool, str | None]:
        evidence = (
            relationship
            .evidence_text
            .strip()
            .casefold()
        )

        relationship_type = (
            relationship.relationship_type
        )

        # -------------------------------------------------
        # Global confidence threshold
        # -------------------------------------------------
        if relationship.confidence < 0.70:
            return (
                False,
                "Relationship confidence "
                "below 0.70",
            )

        # -------------------------------------------------
        # TRAINED_ON
        #
        # Must be:
        #
        # Model -> Dataset
        #
        # and the evidence must explicitly
        # establish use as training data.
        # -------------------------------------------------
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

            # Deliberately conservative.
            #
            # Do NOT include generic:
            #
            # "trained using"
            # "trained with"
            #
            # because:
            #
            # "trained using transfer learning
            # with ImageNet weights"
            #
            # does not establish that this model
            # was trained on ImageNet.
            training_cues = (
                "trained on",
                "training data",
                "training dataset",
                "training set",
                "used for training",
            )

            if not any(
                cue in evidence
                for cue in training_cues
            ):
                return (
                    False,
                    "TRAINED_ON requires "
                    "explicit training evidence",
                )

        # -------------------------------------------------
        # EVALUATED_ON
        #
        # Target must be a Dataset.
        # -------------------------------------------------
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

        # -------------------------------------------------
        # EXPLAINED_BY
        #
        # Model -> Method
        # -------------------------------------------------
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

        # -------------------------------------------------
        # APPLIES_TO
        #
        # Source must be a Method.
        # -------------------------------------------------
        if (
            relationship_type
            == RelationshipType.APPLIES_TO
        ):
            if (
                relationship.source_type
                != EntityType.METHOD
            ):
                return (
                    False,
                    "APPLIES_TO source "
                    "must be Method",
                )

        # -------------------------------------------------
        # DEVELOPED_BY
        #
        # Expected:
        #
        # Model / Dataset / Method / Product
        # ->
        # Person / Organization
        #
        # The canonicalizer repairs obvious
        # Person -> thing reversals first.
        # -------------------------------------------------
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

        # -------------------------------------------------
        # DEPENDS_ON
        #
        # Mere use, benchmarking, latency,
        # deployment or execution on a
        # technology does not prove dependency.
        # -------------------------------------------------
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
                for cue in dependency_cues
            ):
                return (
                    False,
                    "DEPENDS_ON requires "
                    "explicit dependency evidence",
                )

        return True, None

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