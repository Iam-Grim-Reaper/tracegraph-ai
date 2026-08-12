import re
from dataclasses import dataclass

from app.agents.state import (
    RetrievalRoute,
    TraceGraphState,
)


@dataclass
class RoutingDecision:
    route: RetrievalRoute
    reason: str


class RetrievalRouter:
    """
    Deterministic retrieval router for TraceGraph.

    Routes:

    hybrid
        Direct semantic/document lookup.

    graph
        Simple entity-relationship questions.

    fused
        Multi-hop, multi-entity, or mixed
        relational + textual questions.

    The router deliberately does not call an LLM.
    Retrieval routing should remain fast,
    deterministic, inexpensive, and resilient
    to external model quotas.
    """

    # -------------------------------------------------
    # Strong signals that the question requires
    # multiple connected facts.
    # -------------------------------------------------
    MULTI_HOP_PATTERNS = (
        r"\band who\b",
        r"\band which\b",
        r"\band what\b",
        r"\band where\b",
        r"\band how\b",
        r"\bwhich one\b",
        r"\bwhich of them\b",
        r"\bwho .* and .* who\b",
        r"\bwhat .* and .* who\b",
        r"\bwhat .* and .* which\b",
        r"\bwhich .* and .* which\b",
        r"\bassociated with\b",
        r"\brelationship between\b",
        r"\bconnections? between\b",
    )

    # -------------------------------------------------
    # Strong graph relationship signals.
    # -------------------------------------------------
    GRAPH_PATTERNS = (
        r"\bwho developed\b",
        r"\bwho created\b",
        r"\bwho authored\b",
        r"\bwho owns\b",
        r"\bwho works on\b",
        r"\bwho manages\b",
        r"\bwho reports to\b",
        r"\bwho belongs to\b",

        r"\bwhat dataset\b",
        r"\bwhich dataset\b",
        r"\bwhat organization\b",
        r"\bwhich organization\b",
        r"\bwhat regulation governs\b",
        r"\bwhich regulation governs\b",
        r"\bwhat obligation\b",
        r"\bwhich obligation\b",
        r"\bwhat department\b",
        r"\bwhich department\b",
        r"\bwhat team\b",
        r"\bwhich team\b",

        r"\bdeveloped by\b",
        r"\bevaluated on\b",
        r"\btrained on\b",
        r"\bpart of\b",
        r"\bbelongs to\b",
        r"\breports to\b",
        r"\bworks on\b",
        r"\bowned by\b",
    )

    # -------------------------------------------------
    # Questions that are particularly well suited
    # to text/semantic retrieval.
    # -------------------------------------------------
    HYBRID_PATTERNS = (
        r"\bsummarize\b",
        r"\bsummary\b",
        r"\bexplain\b",
        r"\bdescribe\b",
        r"\baccuracy\b",
        r"\bperformance\b",
        r"\bmethodology\b",
        r"\bresults?\b",
        r"\bfindings?\b",
        r"\bconclusion\b",
        r"\bpolicy say\b",
        r"\baccording to\b",
        r"\blisted\b",
        r"\bmentioned\b",
        r"\brequirements?\b",
    )

    def route(
        self,
        question: str,
    ) -> RoutingDecision:
        if not question.strip():
            raise ValueError(
                "Question cannot be empty"
            )

        normalized = self._normalize(
            question
        )

        # ---------------------------------------------
        # 1. Multi-hop gets highest priority.
        # ---------------------------------------------
        if self._matches_any(
            normalized,
            self.MULTI_HOP_PATTERNS,
        ):
            return RoutingDecision(
                route="fused",
                reason=(
                    "The question requests multiple "
                    "connected facts or relationships, "
                    "so combined graph and hybrid "
                    "retrieval is appropriate."
                ),
            )

        # ---------------------------------------------
        # 2. Count explicit graph relationship cues.
        # ---------------------------------------------
        graph_matches = (
            self._count_matches(
                normalized,
                self.GRAPH_PATTERNS,
            )
        )

        # Multiple relational signals can indicate
        # a compound graph question even without
        # an obvious 'and who' phrase.
        if graph_matches >= 2:
            return RoutingDecision(
                route="fused",
                reason=(
                    "The question contains multiple "
                    "relationship signals and may "
                    "require multi-hop evidence."
                ),
            )

        # ---------------------------------------------
        # 3. Simple explicit relationship lookup.
        # ---------------------------------------------
        if graph_matches == 1:
            return RoutingDecision(
                route="graph",
                reason=(
                    "The question asks for a direct "
                    "relationship between entities, "
                    "which is well suited to graph "
                    "retrieval."
                ),
            )

        # ---------------------------------------------
        # 4. Strong textual lookup signals.
        # ---------------------------------------------
        if self._matches_any(
            normalized,
            self.HYBRID_PATTERNS,
        ):
            return RoutingDecision(
                route="hybrid",
                reason=(
                    "The question primarily requests "
                    "information contained directly "
                    "in document text."
                ),
            )

        # ---------------------------------------------
        # 5. Default safely to hybrid.
        #
        # Vector + BM25 retrieval has the broadest
        # coverage when no explicit graph structure
        # can be inferred from the question.
        # ---------------------------------------------
        return RoutingDecision(
            route="hybrid",
            reason=(
                "No strong multi-hop or explicit "
                "graph relationship signal was "
                "detected, so hybrid retrieval "
                "provides the broadest coverage."
            ),
        )

    def __call__(
        self,
        state: TraceGraphState,
    ) -> dict:
        question = (
            state.get(
                "rewritten_question"
            )
            or state.get(
                "question",
                "",
            )
        )

        decision = self.route(
            question
        )

        return {
            "retrieval_route": (
                decision.route
            ),
            "routing_reason": (
                decision.reason
            ),
        }

    @staticmethod
    def _normalize(
        question: str,
    ) -> str:
        value = question.casefold()

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    @staticmethod
    def _matches_any(
        question: str,
        patterns: tuple[str, ...],
    ) -> bool:
        return any(
            re.search(
                pattern,
                question,
            )
            is not None
            for pattern in patterns
        )

    @staticmethod
    def _count_matches(
        question: str,
        patterns: tuple[str, ...],
    ) -> int:
        return sum(
            1
            for pattern in patterns
            if re.search(
                pattern,
                question,
            )
            is not None
        )


def route_after_router(
    state: TraceGraphState,
) -> RetrievalRoute:
    route = state.get(
        "retrieval_route"
    )

    if route not in {
        "hybrid",
        "graph",
        "fused",
    }:
        raise ValueError(
            f"Invalid retrieval route: "
            f"{route}"
        )

    return route
