from app.services import tracegraph_service as module


def test_response_with_source_filenames_skips_catalog(monkeypatch):
    class UnexpectedCatalog:
        def list_documents(self):
            raise AssertionError("No Neo4j query should run for existing filenames")

    monkeypatch.setattr(module, "DocumentCatalogService", UnexpectedCatalog)
    evidence = {
        "label": "Evidence 1",
        "document_id": "doc-1",
        "filename": "resume.txt",
        "text": "Shriyans Denis",
    }
    result = module.TraceGraphService._serialize_result(
        {
            "final_answer": "Shriyans Denis [Evidence 1]",
            "evidence_items": [evidence],
            "used_evidence_labels": ["Evidence 1"],
            "verification_passed": True,
        },
        ["doc-1"],
    )

    assert result["answer_status"] == "verified_answer"
    assert result["evidence_items"][0]["filename"] == "resume.txt"
    assert evidence["filename"] == "resume.txt"


def test_missing_source_filename_is_backfilled(monkeypatch):
    calls = []

    class Catalog:
        def get_ready_filenames(self, document_ids):
            calls.append(set(document_ids))
            return {"doc-1": "resume.txt"}

    monkeypatch.setattr(module, "DocumentCatalogService", Catalog)
    evidence = {"label": "Evidence 1", "document_id": "doc-1"}
    result = module.TraceGraphService._serialize_result(
        {"evidence_items": [evidence]}, ["doc-1"]
    )

    assert calls == [{"doc-1"}]
    assert result["evidence_items"][0]["filename"] == "resume.txt"
    assert "filename" not in evidence


def test_rejected_draft_citations_do_not_turn_uncited_abstention_into_partial_answer():
    response = module.TraceGraphService._serialize_result(
        {
            "final_answer": "The provided evidence was insufficient.",
            "used_evidence_labels": ["Evidence 1"],
            "verification_passed": False,
        }, None,
    )
    assert response["answer_status"] == "grounded_abstention"
    assert response["verified"] is False


def test_degraded_retrieval_cannot_report_fully_verified_answer():
    response = module.TraceGraphService._serialize_result(
        {
            "final_answer": "A supported fact [Evidence 1]",
            "used_evidence_labels": ["Evidence 1"],
            "verification_passed": True,
            "degraded": True,
        }, None,
    )
    assert response["answer_status"] == "degraded_retrieval"
    assert response["verified"] is False
