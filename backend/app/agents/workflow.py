from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from app.agents.research_agent import (
    ResearchAgent,
)
from app.agents.retrieval_nodes import (
    RetrievalNodes,
)
from app.agents.retrieval_router import (
    RetrievalRouter,
    route_after_router,
)
from app.agents.state import (
    TraceGraphState,
)
from app.agents.verification_agent import (
    VerificationAgent,
    route_after_verification,
)


def build_tracegraph_workflow():
    router = RetrievalRouter()

    retrieval = RetrievalNodes()

    research_agent = (
        ResearchAgent()
    )

    verification_agent = (
        VerificationAgent()
    )

    workflow = StateGraph(
        TraceGraphState
    )

    # ---------------------------------
    # Agent / retrieval nodes
    # ---------------------------------

    workflow.add_node(
        "retrieval_router",
        router,
    )

    workflow.add_node(
        "hybrid_retrieval",
        retrieval.hybrid,
    )

    workflow.add_node(
        "graph_retrieval",
        retrieval.graph,
    )

    workflow.add_node(
        "fused_retrieval",
        retrieval.fused,
    )

    workflow.add_node(
        "research_agent",
        research_agent,
    )

    workflow.add_node(
        "verification_agent",
        verification_agent,
    )

    workflow.add_node(
        "verification_retry",
        verification_agent
        .rewrite_for_retry,
    )

    # ---------------------------------
    # Entry
    # ---------------------------------

    workflow.add_edge(
        START,
        "retrieval_router",
    )

    # ---------------------------------
    # Retrieval Router
    # ---------------------------------

    workflow.add_conditional_edges(
        "retrieval_router",
        route_after_router,
        {
            "hybrid": (
                "hybrid_retrieval"
            ),
            "graph": (
                "graph_retrieval"
            ),
            "fused": (
                "fused_retrieval"
            ),
        },
    )

    # ---------------------------------
    # All retrieval paths converge
    # into research.
    # ---------------------------------

    workflow.add_edge(
        "hybrid_retrieval",
        "research_agent",
    )

    workflow.add_edge(
        "graph_retrieval",
        "research_agent",
    )

    workflow.add_edge(
        "fused_retrieval",
        "research_agent",
    )

    # ---------------------------------
    # Research -> Verification
    # ---------------------------------

    workflow.add_edge(
        "research_agent",
        "verification_agent",
    )

    # ---------------------------------
    # Verification decision
    #
    # pass:
    #   answer is complete
    #
    # retry:
    #   rewrite query and retrieve
    #   exactly one more time
    #
    # stop:
    #   second verification failed;
    #   use conservative final answer
    # ---------------------------------

    workflow.add_conditional_edges(
        "verification_agent",
        route_after_verification,
        {
            "pass": END,

            "retry": (
                "verification_retry"
            ),

            "stop": END,
        },
    )

    # ---------------------------------
    # One controlled retry.
    #
    # The rewritten question is routed
    # again because its optimal retrieval
    # strategy may differ.
    # ---------------------------------

    workflow.add_edge(
        "verification_retry",
        "retrieval_router",
    )

    return workflow.compile()