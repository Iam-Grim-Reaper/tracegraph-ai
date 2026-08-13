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


@pytest.mark.parametrize(
    "creator_verb",
    [
        "made",
        "created",
        "developed",
        "invented",
        "designed",
        "authored",
        "built",
    ],
)
def test_creator_relationship_synonyms_use_graph(
    creator_verb,
):
    decision = RetrievalRouter().route(
        f"Who {creator_verb} the method?"
    )

    assert decision.route == "graph"
