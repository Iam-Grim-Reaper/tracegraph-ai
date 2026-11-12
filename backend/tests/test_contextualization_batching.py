"""Bounded contextualization prevents oversized Gemini JSON responses."""

import json
import re
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.document import Document, DocumentChunk, FileType
from app.retrieval.contextualizer import Contextualizer


def build_chunks(count):
    document = Document(id=uuid4(), filename="test.docx", file_type=FileType.DOCX)
    chunks = [
        DocumentChunk(
            document_id=document.id,
            chunk_index=index,
            text=f"Section {index} describes a concrete research finding.",
        )
        for index in range(count)
    ]
    return document, chunks


def test_large_document_is_contextualized_in_bounded_batches(monkeypatch):
    prompts = []

    def generate_content(**kwargs):
        prompt = kwargs["contents"]
        prompts.append(prompt)
        indices = re.findall(r'<chunk index="(\d+)">', prompt)
        assert 1 <= len(indices) <= 16
        return SimpleNamespace(text=json.dumps({
            "contexts": [{"chunk_index": int(index), "context": f"Summary for {index}"} for index in indices]
        }))

    # Call the actual batching function without provider tokens.
    contextualizer = Contextualizer.__new__(Contextualizer)
    contextualizer.model = "unit-test-model"
    contextualizer.client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)
    )
    document, chunks = build_chunks(35)
    document_text = "Overview: useful context. " + "x" * 150000
    result = contextualizer.contextualize_chunks(document, chunks, document_text)
    assert len(prompts) == 3
    assert len(result) == 35
    assert all(result[i].contextual_text.startswith(f"Summary for {i}\n\nSection") for i in range(35))
    # Huge documents do not get repeated verbatim in every provider request.
    assert all(len(prompt) < 25000 for prompt in prompts)
    assert all("Additional document content omitted" in prompt for prompt in prompts)


def test_mismatched_batch_rejected_before_inserting_corrupted_context():
    def wrong_response(**kwargs):
        return SimpleNamespace(text=json.dumps({
            "contexts": [{"chunk_index": 99, "context": "A hallucinated index"}]
        }))

    contextualizer = Contextualizer.__new__(Contextualizer)
    contextualizer.model = "unit-test-model"
    contextualizer.client = SimpleNamespace(
        models=SimpleNamespace(generate_content=wrong_response)
    )
    doc, chunks = build_chunks(2)
    with pytest.raises(RuntimeError, match="indices or text"):
        contextualizer.contextualize_chunks(doc, chunks, "Short document.")
    assert all(chunk.contextual_text is None for chunk in chunks)
