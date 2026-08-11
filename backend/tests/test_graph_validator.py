from app.graph.models import (
    RelationshipCandidate,
)
from app.graph.schema import (
    EntityType,
    RelationshipType,
)
from app.graph.validator import (
    GraphRelationshipValidator,
)


def test_rejects_unsupported_trained_on():
    validator = GraphRelationshipValidator()

    relationship = RelationshipCandidate(
        source_name="ConvNeXt-Small",
        source_type=EntityType.MODEL,
        target_name="LC25000",
        target_type=EntityType.DATASET,
        relationship_type=(
            RelationshipType.TRAINED_ON
        ),
        confidence=0.80,
        evidence_text=(
            "The model attained 99.98% "
            "validation accuracy on the "
            "LC25000 dataset."
        ),
    )

    valid, reason = validator.validate(
        relationship
    )

    assert valid is False

    assert reason == (
        "TRAINED_ON requires explicit "
        "training evidence"
    )


def test_accepts_explicit_training_evidence():
    validator = GraphRelationshipValidator()

    relationship = RelationshipCandidate(
        source_name="ConvNeXt-Small",
        source_type=EntityType.MODEL,
        target_name="LC25000",
        target_type=EntityType.DATASET,
        relationship_type=(
            RelationshipType.TRAINED_ON
        ),
        confidence=0.95,
        evidence_text=(
            "ConvNeXt-Small was trained on "
            "the LC25000 dataset."
        ),
    )

    valid, reason = validator.validate(
        relationship
    )

    assert valid is True
    assert reason is None


def test_explained_by_requires_model_to_method():
    validator = GraphRelationshipValidator()

    relationship = RelationshipCandidate(
        source_name="ConvNeXt-Small",
        source_type=EntityType.MODEL,
        target_name="Grad-CAM",
        target_type=EntityType.METHOD,
        relationship_type=(
            RelationshipType.EXPLAINED_BY
        ),
        confidence=0.95,
        evidence_text=(
            "Grad-CAM was used to explain "
            "the model predictions."
        ),
    )

    valid, reason = validator.validate(
        relationship
    )

    assert valid is True
    assert reason is None


def test_rejects_low_confidence_relationship():
    validator = GraphRelationshipValidator()

    relationship = RelationshipCandidate(
        source_name="Grad-CAM",
        source_type=EntityType.METHOD,
        target_name="ConvNeXt-Small",
        target_type=EntityType.MODEL,
        relationship_type=(
            RelationshipType.APPLIES_TO
        ),
        confidence=0.45,
        evidence_text=(
            "Grad-CAM was applied to "
            "ConvNeXt-Small."
        ),
    )

    valid, reason = validator.validate(
        relationship
    )

    assert valid is False

    assert reason == (
        "Relationship confidence below 0.70"
    )


def test_filter_separates_valid_and_invalid():
    validator = GraphRelationshipValidator()

    relationships = [
        RelationshipCandidate(
            source_name="ConvNeXt-Small",
            source_type=EntityType.MODEL,
            target_name="LC25000",
            target_type=EntityType.DATASET,
            relationship_type=(
                RelationshipType.TRAINED_ON
            ),
            confidence=0.90,
            evidence_text=(
                "The model achieved validation "
                "accuracy on LC25000."
            ),
        ),
        RelationshipCandidate(
            source_name="ConvNeXt-Small",
            source_type=EntityType.MODEL,
            target_name="Grad-CAM",
            target_type=EntityType.METHOD,
            relationship_type=(
                RelationshipType.EXPLAINED_BY
            ),
            confidence=0.95,
            evidence_text=(
                "Grad-CAM was used to explain "
                "the model predictions."
            ),
        ),
    ]

    accepted, rejected = (
        validator.filter_relationships(
            relationships
        )
    )

    assert len(accepted) == 1
    assert len(rejected) == 1

    assert (
        accepted[0].relationship_type
        == RelationshipType.EXPLAINED_BY
    )

    assert (
        rejected[0]
        .relationship
        .relationship_type
        == RelationshipType.TRAINED_ON
    )