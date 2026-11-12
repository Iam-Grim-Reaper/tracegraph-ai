"""Fail-closed final citation validation without paid provider calls."""

import json
from types import SimpleNamespace

import pytest

from app.agents.verification_agent import VerificationAgent


def fake_verifier(*, passed=True, final_answer="Grounded [Evidence 1]"):
    """Bypass the SDK transport while using the actual verifier implementation."""
    agent = VerificationAgent.__new__(VerificationAgent)
    payload = {
        "passed": passed,
        "reason": "Supported by supplied excerpts.",
        "unsupported_claims": [],
        "final_answer": final_answer,
    }
    agent.model = "test-model"
    agent.client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **kwargs: SimpleNamespace(text=json.dumps(payload))
        )
    )
    return agent


@pytest.mark.parametrize(
    "answer",
    [
        "Grounded [Evidence 1]",
        "Grounded [Graph Evidence q1-2]",
        "Grounded [Evidence 1] and [Graph Evidence q1-2]",
    ],
)
def test_verification_accepts_final_citations_present_in_evidence(answer):
    agent = fake_verifier(final_answer=answer)
    result = agent.verify(
        question="What happened?",
        draft_answer="Grounded [Evidence 1]",
        research_context="[Evidence 1]\nSource text\n[Graph Evidence q1-2]\nLinked fact",
    )
    assert result.passed
    assert result.final_answer == answer


def test_final_hallucinated_citation_is_rejected():
    agent = fake_verifier(final_answer="Invented [Evidence 99]")
    result = agent.verify(
        question="What happened?",
        draft_answer="Real claim [Evidence 1]",
        research_context="[Evidence 1]\nActual source text",
    )
    assert result.passed is False
    assert "Evidence 99" not in result.final_answer
    assert "unavailable evidence label" in result.reason


def test_verified_final_answer_must_preserve_draft_citation():
    agent = fake_verifier(final_answer="Factual assertion without citation")
    result = agent.verify(
        question="What happened?",
        draft_answer="Real claim [Evidence 1]",
        research_context="[Evidence 1]\nActual source text",
    )
    assert result.passed is False
    assert "dropped" in result.reason


def test_failed_verifier_still_never_exposes_fabricated_final_citation():
    agent = fake_verifier(passed=False, final_answer="Speculative [Evidence 123]")
    result = agent.verify(
        question="What happened?",
        draft_answer="Original [Evidence 1]",
        research_context="[Evidence 1]\nSource",
    )
    assert result.passed is False
    assert "Evidence 123" not in result.final_answer
