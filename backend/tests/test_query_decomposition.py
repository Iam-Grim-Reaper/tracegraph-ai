from types import SimpleNamespace

from app.agents.query_decomposition import (
    ConditionalDecompositionRetriever,
    DecompositionPlan,
    SubQuestion,
)


class FakeDecomposer:
    def __init__(self, plan=None, error=None):
        self.plan = plan
        self.error = error
        self.calls = 0

    def decompose(self, question):
        self.calls += 1
        if self.error:
            raise self.error
        return self.plan


class FakeAdaptive:
    _requires_decomposition = staticmethod(
        lambda question: " and " in question.casefold() and "which" in question.casefold()
    )

    def __init__(self, missing_parent=False):
        self.calls = []
        self.missing_parent = missing_parent

    def __call__(self, state):
        self.calls.append(state)
        index = len(self.calls)
        entities = [] if self.missing_parent and index == 1 else ["Grad-CAM"]
        return {
            "retrieval_route": "hybrid" if index == 1 else "graph",
            "research_context": (
                f"[Evidence 1]\nSource: sample.pdf\nPage: 1\n"
                f"Chunk ID: chunk-{index}\ntext"
            ),
            "retrieved_chunk_ids": [f"chunk-{index}"],
            "graph_fact_count": index - 1,
            "grounded_entities": entities,
            "query_embedding_call_count": 1,
            "qdrant_call_count": 1,
            "neo4j_call_count": 1,
            "crossencoder_call_count": 1,
            "evidence_items": [{
                "label": "Evidence 1",
                "kind": "text",
                "text": "text",
                "document_id": "doc-1",
                "filename": "sample.pdf",
                "chunk_id": f"chunk-{index}",
                "chunk_index": index - 1,
                "page_number": 1,
                "retrieval_route": "hybrid" if index == 1 else "graph",
                "relevance": 4.0,
            }],
        }


def plan():
    return DecompositionPlan(subquestions=[
        SubQuestion(id="q1", question="Which method is discussed?"),
        SubQuestion(id="q2", question="Who developed the identified method?", depends_on=["q1"]),
    ])


def test_simple_questions_do_not_decompose():
    for question in ("tell me about skills", "who was behind grad cam"):
        adaptive = FakeAdaptive()
        decomposer = FakeDecomposer(plan())
        result = ConditionalDecompositionRetriever(adaptive, decomposer)({"question": question})
        assert result["decomposition_used"] is False
        assert decomposer.calls == 0
        assert len(adaptive.calls) == 1


def test_complex_question_decomposes_once_and_resolves_dependency():
    adaptive = FakeAdaptive()
    decomposer = FakeDecomposer(plan())
    result = ConditionalDecompositionRetriever(adaptive, decomposer)({
        "question": "Which method is discussed and which person developed it?",
        "document_ids": ["doc-1"],
    })
    assert decomposer.calls == 1
    assert len(adaptive.calls) == 2
    assert adaptive.calls[1]["question"].endswith("Grounded entity: Grad-CAM.")
    assert all(call["document_ids"] == ["doc-1"] for call in adaptive.calls)
    assert result["decomposition_used"] is True
    assert result["subquestion_count"] == 2
    assert result["qdrant_call_count"] == 2
    assert result["neo4j_call_count"] == 2
    assert result["crossencoder_call_count"] == 2
    assert "Evidence q1-1" in result["research_context"]
    assert "Evidence q2-1" in result["research_context"]
    assert result["subquestions"][1]["depends_on"] == ["q1"]
    assert [item["label"] for item in result["evidence_items"]] == [
        "Evidence q1-1",
        "Evidence q2-1",
    ]
    assert result["evidence_items"][1]["subquestion_id"] == "q2"


def test_missing_grounded_dependency_is_not_invented():
    adaptive = FakeAdaptive(missing_parent=True)
    result = ConditionalDecompositionRetriever(adaptive, FakeDecomposer(plan()))({
        "question": "Which method is discussed and which person developed it?"
    })
    assert len(adaptive.calls) == 1
    assert result["decomposition_degraded"] is True
    assert result["subquestions"][1]["route"] is None


def test_decomposition_failure_falls_back_to_adaptive():
    adaptive = FakeAdaptive()
    result = ConditionalDecompositionRetriever(
        adaptive, FakeDecomposer(error=RuntimeError("provider"))
    )({"question": "Which method is discussed and which person developed it?"})
    assert result["decomposition_used"] is False
    assert result["decomposition_degraded"] is True
    assert len(adaptive.calls) == 1


def test_retry_never_recursively_decomposes():
    adaptive = FakeAdaptive()
    decomposer = FakeDecomposer(plan())
    result = ConditionalDecompositionRetriever(adaptive, decomposer)({
        "question": "Which method is discussed and which person developed it?",
        "retry_count": 1,
    })
    assert result["decomposition_used"] is False
    assert decomposer.calls == 0


def test_schema_enforces_maximum_three_subquestions():
    try:
        DecompositionPlan(subquestions=[
            SubQuestion(id=f"q{i}", question="question") for i in range(1, 5)
        ])
    except Exception:
        pass
    else:
        raise AssertionError("four subquestions must be rejected")
