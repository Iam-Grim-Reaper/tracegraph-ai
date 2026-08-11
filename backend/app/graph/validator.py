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
            relationship.evidence_text
            .strip()
            .casefold()
        )

        relationship_type = (
            relationship.relationship_type
        )

        # Reject low-confidence relationships
        # before they enter the graph.
        if relationship.confidence < 0.70:
            return (
                False,
                "Relationship confidence below 0.70",
            )

        # TRAINED_ON must be:
        # Model -> Dataset
        # with explicit evidence of training.
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
                    "TRAINED_ON source must be Model",
                )

            if (
                relationship.target_type
                != EntityType.DATASET
            ):
                return (
                    False,
                    "TRAINED_ON target must be Dataset",
                )

            training_cues = (
                "trained on",
                "trained using",
                "trained with",
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
                    "TRAINED_ON requires explicit "
                    "training evidence",
                )

        # EVALUATED_ON should point
        # to a Dataset.
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
                    "EVALUATED_ON target must be Dataset",
                )

        # EXPLAINED_BY should be:
        # Model -> Method
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
                    "EXPLAINED_BY source must be Model",
                )

            if (
                relationship.target_type
                != EntityType.METHOD
            ):
                return (
                    False,
                    "EXPLAINED_BY target must be Method",
                )

        # APPLIES_TO should start
        # from a Method.
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
                    "APPLIES_TO source must be Method",
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
            is_valid, reason = self.validate(
                relationship
            )

            if is_valid:
                accepted.append(
                    relationship
                )

            else:
                rejected.append(
                    RejectedRelationship(
                        relationship=relationship,
                        reason=(
                            reason
                            or "Unknown validation error"
                        ),
                    )
                )

        return accepted, rejected