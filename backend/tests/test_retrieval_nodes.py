from types import SimpleNamespace

from app.agents.retrieval_nodes import (
    RetrievalNodes,
)


class FakeGraphRetriever:
    def __init__(self):
        self.requested_max_facts = None
        self.formatted_max_facts = None

    def retrieve(
        self,
        query,
        max_seed_entities,
        max_facts,
        document_ids,
    ):
        self.requested_max_facts = (
            max_facts
        )

        facts = [
            SimpleNamespace(
                source_chunk_id=(
                    f"chunk-{index}"
                ),
                relationship_type=(
                    "DEVELOPED_BY"
                    if index == 14
                    else "RELATED_TO"
                ),
            )
            for index in range(1, 15)
        ]

        return SimpleNamespace(
            facts=facts
        )

    def format_context(
        self,
        result,
        max_facts,
    ):
        self.formatted_max_facts = (
            max_facts
        )

        return "\n".join(
            fact.relationship_type
            for fact in result.facts[
                :max_facts
            ]
        )


def test_graph_node_does_not_drop_retrieved_facts():
    retriever = FakeGraphRetriever()

    node = RetrievalNodes.__new__(
        RetrievalNodes
    )

    node.graph_retriever = (
        retriever
    )

    result = node.graph(
        {
            "question": (
                "Who developed Grad-CAM?"
            ),
            "document_ids": [
                (
                    "1290eef8-11ec-5161-"
                    "8f6f-ac5782b76b18"
                )
            ],
        }
    )

    assert (
        retriever.requested_max_facts
        == 20
    )

    assert (
        retriever.formatted_max_facts
        == retriever.requested_max_facts
    )

    assert "DEVELOPED_BY" in (
        result["research_context"]
    )

    assert result[
        "graph_fact_count"
    ] == 14
