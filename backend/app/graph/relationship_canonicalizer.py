from app.graph.models import (
    RelationshipCandidate,
)
from app.graph.schema import (
    EntityType,
    RelationshipType,
)


class RelationshipCanonicalizer:
    """
    Canonicalizes the direction of relationships
    when entity types make the intended direction
    deterministic.

    It does not invent new relationships.
    """

    def canonicalize(
        self,
        relationship: RelationshipCandidate,
    ) -> RelationshipCandidate:
        relationship_type = (
            relationship.relationship_type
        )

        # -------------------------------------------------
        # DEVELOPED_BY
        #
        # Wrong:
        # Person -> DEVELOPED_BY -> Dataset/Model/Method
        #
        # Correct:
        # Dataset/Model/Method -> DEVELOPED_BY -> Person
        # -------------------------------------------------
        if (
            relationship_type
            == RelationshipType.DEVELOPED_BY
            and relationship.source_type
            == EntityType.PERSON
            and relationship.target_type
            != EntityType.PERSON
        ):
            return self._reverse(
                relationship
            )

        # -------------------------------------------------
        # EVALUATED_ON / TRAINED_ON
        #
        # Wrong:
        # Dataset -> EVALUATED_ON -> Model
        #
        # Correct:
        # Model -> EVALUATED_ON -> Dataset
        # -------------------------------------------------
        if (
            relationship_type
            in {
                RelationshipType.EVALUATED_ON,
                RelationshipType.TRAINED_ON,
            }
            and relationship.source_type
            == EntityType.DATASET
            and relationship.target_type
            == EntityType.MODEL
        ):
            return self._reverse(
                relationship
            )

        # -------------------------------------------------
        # EXPLAINED_BY
        #
        # Wrong:
        # Method -> EXPLAINED_BY -> Model
        #
        # Correct:
        # Model -> EXPLAINED_BY -> Method
        # -------------------------------------------------
        if (
            relationship_type
            == RelationshipType.EXPLAINED_BY
            and relationship.source_type
            == EntityType.METHOD
            and relationship.target_type
            == EntityType.MODEL
        ):
            return self._reverse(
                relationship
            )

        # -------------------------------------------------
        # APPLIES_TO
        #
        # Method should be the source.
        # -------------------------------------------------
        if (
            relationship_type
            == RelationshipType.APPLIES_TO
            and relationship.source_type
            != EntityType.METHOD
            and relationship.target_type
            == EntityType.METHOD
        ):
            return self._reverse(
                relationship
            )

        return relationship

    @staticmethod
    def _reverse(
        relationship: RelationshipCandidate,
    ) -> RelationshipCandidate:
        return RelationshipCandidate(
            source_name=(
                relationship.target_name
            ),
            source_type=(
                relationship.target_type
            ),
            target_name=(
                relationship.source_name
            ),
            target_type=(
                relationship.source_type
            ),
            relationship_type=(
                relationship.relationship_type
            ),
            confidence=(
                relationship.confidence
            ),
            evidence_text=(
                relationship.evidence_text
            ),
        )