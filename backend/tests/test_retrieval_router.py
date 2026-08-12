import pytest

from app.agents.retrieval_router import (
    RetrievalRouter,
)


@pytest.mark.parametrize(
    "question",
    [
        (
            "What regulation governs the "
            "ACME Data Protection Policy?"
        ),
        (
            "What obligation does Northstar "
            "Analytics LLC have?"
        ),
    ],
)
def test_domain_relationship_questions_use_graph(
    question,
):
    decision = RetrievalRouter().route(
        question
    )

    assert decision.route == "graph"
