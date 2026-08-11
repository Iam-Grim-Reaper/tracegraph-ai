from app.graph.postprocessor import (
    GraphPostProcessor,
)


def test_exact_evidence_is_grounded():
    evidence = (
        "Grad-CAM was used for "
        "visual interpretation."
    )

    chunk = (
        "The model was evaluated carefully. "
        "Grad-CAM was used for "
        "visual interpretation."
    )

    assert (
        GraphPostProcessor
        ._evidence_is_grounded(
            evidence,
            chunk,
        )
        is True
    )


def test_pdf_spacing_difference_is_grounded():
    evidence = (
        "ConvNeXt-Small model attained "
        "99.98% validation accuracy."
    )

    chunk = (
        "Our ConvNeXt -Small model attained "
        "99.98% validation accuracy."
    )

    assert (
        GraphPostProcessor
        ._evidence_is_grounded(
            evidence,
            chunk,
        )
        is True
    )


def test_small_extraction_variation_is_grounded():
    evidence = (
        "ConvNeXt-Small attained 99.98% "
        "validation accuracy on LC25000."
    )

    chunk = (
        "Our ConvNeXt -Small model attained "
        "99.98% validation accuracy across "
        "the LC25000 dataset."
    )

    assert (
        GraphPostProcessor
        ._evidence_is_grounded(
            evidence,
            chunk,
        )
        is True
    )


def test_hallucinated_evidence_is_rejected():
    evidence = (
        "The model was trained using "
        "one million private clinical images."
    )

    chunk = (
        "The ConvNeXt-Small model was "
        "evaluated on LC25000 and achieved "
        "high validation accuracy."
    )

    assert (
        GraphPostProcessor
        ._evidence_is_grounded(
            evidence,
            chunk,
        )
        is False
    )