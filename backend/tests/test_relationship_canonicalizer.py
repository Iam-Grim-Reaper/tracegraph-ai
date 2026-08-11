from app.graph.models import (
    RelationshipCandidate,
)
from app.graph.relationship_canonicalizer import (
    RelationshipCanonicalizer,
)
from app.graph.schema import (
    EntityType,
    RelationshipType,
)


def test_reverses_developed_by_from_person():
    canonicalizer = (
        RelationshipCanonicalizer()
    )

    relationship = RelationshipCandidate(
        source_name=(
            "R. R. Selvaraju et al."
        ),
        source_type=EntityType.PERSON,
        target_name="Grad-CAM",
        target_type=EntityType.METHOD,
        relationship_type=(
            RelationshipType.DEVELOPED_BY
        ),
        confidence=0.90,
        evidence_text=(
            "R. R. Selvaraju et al., "
            "Grad-CAM: Visual Explanations"
        ),
    )

    result = (
        canonicalizer.canonicalize(
            relationship
        )
    )

    assert (
        result.source_name
        == "Grad-CAM"
    )

    assert (
        result.source_type
        == EntityType.METHOD
    )

    assert (
        result.target_name
        == "R. R. Selvaraju et al."
    )

    assert (
        result.target_type
        == EntityType.PERSON
    )


def test_reverses_dataset_evaluated_on_model():
    canonicalizer = (
        RelationshipCanonicalizer()
    )

    relationship = RelationshipCandidate(
        source_name="LC25000",
        source_type=EntityType.DATASET,
        target_name="MobileNet",
        target_type=EntityType.MODEL,
        relationship_type=(
            RelationshipType.EVALUATED_ON
        ),
        confidence=0.90,
        evidence_text=(
            "MobileNet was evaluated "
            "on LC25000."
        ),
    )

    result = (
        canonicalizer.canonicalize(
            relationship
        )
    )

    assert (
        result.source_name
        == "MobileNet"
    )

    assert (
        result.source_type
        == EntityType.MODEL
    )

    assert (
        result.target_name
        == "LC25000"
    )

    assert (
        result.target_type
        == EntityType.DATASET
    )


def test_reverses_explained_by():
    canonicalizer = (
        RelationshipCanonicalizer()
    )

    relationship = RelationshipCandidate(
        source_name="Grad-CAM",
        source_type=EntityType.METHOD,
        target_name="ConvNeXt-Small",
        target_type=EntityType.MODEL,
        relationship_type=(
            RelationshipType.EXPLAINED_BY
        ),
        confidence=0.95,
        evidence_text=(
            "Grad-CAM was used to explain "
            "ConvNeXt-Small predictions."
        ),
    )

    result = (
        canonicalizer.canonicalize(
            relationship
        )
    )

    assert (
        result.source_name
        == "ConvNeXt-Small"
    )

    assert (
        result.target_name
        == "Grad-CAM"
    )


def test_valid_applies_to_is_unchanged():
    canonicalizer = (
        RelationshipCanonicalizer()
    )

    relationship = RelationshipCandidate(
        source_name="Grad-CAM",
        source_type=EntityType.METHOD,
        target_name="ConvNeXt-Small",
        target_type=EntityType.MODEL,
        relationship_type=(
            RelationshipType.APPLIES_TO
        ),
        confidence=0.95,
        evidence_text=(
            "Grad-CAM was applied to "
            "ConvNeXt-Small."
        ),
    )

    result = (
        canonicalizer.canonicalize(
            relationship
        )
    )

    assert (
        result.source_name
        == "Grad-CAM"
    )

    assert (
        result.target_name
        == "ConvNeXt-Small"
    )