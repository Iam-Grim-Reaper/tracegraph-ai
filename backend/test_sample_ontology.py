from pathlib import Path

from app.graph.ontology_classifier import (
    OntologyClassifier,
)
from app.ingestion.service import (
    IngestionService,
)


SAMPLE_PATH = Path(
    "../data/sample.pdf"
)


def main():
    print("=" * 70)

    print(
        "TRACEGRAPH SAMPLE PDF "
        "ONTOLOGY TEST"
    )

    print("=" * 70)

    if not SAMPLE_PATH.exists():
        raise FileNotFoundError(
            f"Sample PDF not found: "
            f"{SAMPLE_PATH.resolve()}"
        )

    # -----------------------------------------
    # 1. Parse the document.
    #
    # This does NOT index anything.
    # -----------------------------------------

    print(
        "\n[1/2] Parsing sample.pdf..."
    )

    ingestion_service = (
        IngestionService(
            max_chars=1000
        )
    )

    ingestion = (
        ingestion_service.ingest(
            SAMPLE_PATH
        )
    )

    document = (
        ingestion.document
    )

    chunks = (
        ingestion.chunks
    )

    if not chunks:
        raise RuntimeError(
            "sample.pdf produced "
            "no chunks."
        )

    document_text = (
        "\n\n".join(
            chunk.text
            for chunk in chunks
            if chunk.text.strip()
        )
    )

    if not document_text.strip():
        raise RuntimeError(
            "sample.pdf contained "
            "no usable text."
        )

    print(
        "Document ID:",
        document.id,
    )

    print(
        "Filename:",
        document.filename,
    )

    print(
        "Chunks:",
        len(chunks),
    )

    # -----------------------------------------
    # 2. Classify ontology.
    #
    # Disable LLM fallback deliberately.
    #
    # If this succeeds as "research",
    # then the deterministic classifier alone
    # is strong enough for sample.pdf.
    # -----------------------------------------

    print(
        "\n[2/2] Classifying ontology..."
    )

    classifier = (
        OntologyClassifier(
            enable_llm_fallback=False
        )
    )

    classification = (
        classifier.classify(
            document=document,
            document_text=document_text,
        )
    )

    print(
        "\nSelected ontology:",
        classification.profile.name,
    )

    print(
        "Ontology version:",
        classification.profile.version,
    )

    print(
        "Confidence:",
        f"{classification.confidence:.2f}",
    )

    print(
        "Method:",
        classification.method,
    )

    print(
        "Reason:",
        classification.reason,
    )

    print(
        "Scores:",
        classification.scores,
    )

    # -----------------------------------------
    # Required regression condition.
    # -----------------------------------------

    if (
        classification.profile.name
        != "research"
    ):
        raise RuntimeError(
            "Expected sample.pdf to classify "
            "as research, but received "
            f"'{classification.profile.name}'."
        )

    print(
        "\n" + "=" * 70
    )

    print(
        "SAMPLE PDF ONTOLOGY "
        "CLASSIFICATION VALID"
    )

    print("=" * 70)

    print(
        "sample.pdf -> research: PASS"
    )


if __name__ == "__main__":
    main()