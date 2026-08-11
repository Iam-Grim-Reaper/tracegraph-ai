from app.graph.models import EntityCandidate
from app.graph.normalizer import EntityNormalizer
from app.graph.schema import EntityType


def test_normalize_name():
    normalizer = EntityNormalizer()

    assert (
        normalizer.normalize_name(
            "Grad-CAM"
        )
        == "grad cam"
    )

    assert (
        normalizer.normalize_name(
            "Grad_CAM"
        )
        == "grad cam"
    )

    assert (
        normalizer.normalize_name(
            "  Grad   CAM  "
        )
        == "grad cam"
    )


def test_equivalent_names_get_same_id():
    normalizer = EntityNormalizer()

    first = EntityCandidate(
        name="Grad-CAM",
        entity_type=EntityType.TECHNOLOGY,
    )

    second = EntityCandidate(
        name="Grad CAM",
        entity_type=EntityType.TECHNOLOGY,
    )

    first_entity = normalizer.normalize_entity(
        first
    )

    second_entity = normalizer.normalize_entity(
        second
    )

    assert (
        first_entity.entity_id
        == second_entity.entity_id
    )


def test_different_entity_types_get_different_ids():
    normalizer = EntityNormalizer()

    technology = EntityCandidate(
        name="TraceGraph",
        entity_type=EntityType.TECHNOLOGY,
    )

    project = EntityCandidate(
        name="TraceGraph",
        entity_type=EntityType.PROJECT,
    )

    technology_entity = (
        normalizer.normalize_entity(
            technology
        )
    )

    project_entity = (
        normalizer.normalize_entity(
            project
        )
    )

    assert (
        technology_entity.entity_id
        != project_entity.entity_id
    )


def test_duplicate_entities_are_merged():
    normalizer = EntityNormalizer()

    candidates = [
        EntityCandidate(
            name="Grad-CAM",
            entity_type=EntityType.TECHNOLOGY,
        ),
        EntityCandidate(
            name="Grad CAM",
            entity_type=EntityType.TECHNOLOGY,
            aliases=[
                "Gradient CAM",
            ],
        ),
    ]

    entities = normalizer.normalize_entities(
        candidates
    )

    assert len(entities) == 1

    assert (
        entities[0].normalized_name
        == "grad cam"
    )


def test_aliases_are_deduplicated():
    normalizer = EntityNormalizer()

    candidate = EntityCandidate(
        name="ConvNeXt-Small",
        entity_type=EntityType.TECHNOLOGY,
        aliases=[
            "ConvNeXt Small",
            "convnext-small",
            "ConvNeXt",
        ],
    )

    entity = normalizer.normalize_entity(
        candidate
    )

    assert entity.aliases == [
        "ConvNeXt"
    ]


def test_semantic_alias_entities_are_merged():
    normalizer = EntityNormalizer()

    candidates = [
        EntityCandidate(
            name=(
                "Gradient-weighted Class "
                "Activation Mapping"
            ),
            entity_type=EntityType.METHOD,
            aliases=[
                "Grad-CAM",
            ],
        ),
        EntityCandidate(
            name="Grad-CAM",
            entity_type=EntityType.METHOD,
            aliases=[
                (
                    "Gradient-weighted Class "
                    "Activation Mapping"
                ),
            ],
        ),
    ]

    resolved = (
        normalizer.resolve_alias_entities(
            candidates
        )
    )

    assert len(resolved) == 1

    assert resolved[0].name == "Grad-CAM"

    assert (
        "Gradient-weighted Class Activation Mapping"
        in resolved[0].aliases
    )