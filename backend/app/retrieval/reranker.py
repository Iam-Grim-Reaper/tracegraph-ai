from dataclasses import dataclass
import logging

from sentence_transformers import CrossEncoder

from app.core.config import settings
from app.core.observability import log_event


logger = logging.getLogger(__name__)


@dataclass
class RerankedResult:
    point: object
    rerank_score: float


class CrossEncoderReranker:
    def __init__(
        self,
        model_name: str | None = None,
    ):
        self.model_name = (
            model_name
            or settings.reranker_model_name
        )

        log_event(logger, logging.INFO, "reranker_loading", operation="reranker_initialization", status="started", model=self.model_name)

        self.model = CrossEncoder(
            self.model_name
        )

    def rerank(
        self,
        query: str,
        results: list,
        top_k: int = 5,
    ) -> list[RerankedResult]:
        if not query.strip():
            raise ValueError(
                "Query cannot be empty"
            )

        if not results:
            return []

        pairs = []

        for result in results:
            payload = result.payload or {}

            # Use the original source text here.
            # Contextual text was already used during
            # candidate retrieval.
            text = payload.get(
                "text",
                "",
            )

            pairs.append(
                (
                    query,
                    text,
                )
            )

        scores = self.model.predict(
            pairs,
            show_progress_bar=False,
        )

        reranked = [
            RerankedResult(
                point=result,
                rerank_score=float(score),
            )
            for result, score in zip(
                results,
                scores,
                strict=True,
            )
        ]

        reranked.sort(
            key=lambda item: item.rerank_score,
            reverse=True,
        )

        return reranked[:top_k]

    def score_texts(
        self,
        query: str,
        texts: list[str],
    ) -> list[float]:
        """Score arbitrary evidence text in one model call."""
        if not query.strip():
            raise ValueError(
                "Query cannot be empty"
            )

        if not texts:
            return []

        scores = self.model.predict(
            [(query, value) for value in texts],
            show_progress_bar=False,
        )

        return [
            float(score)
            for score in scores
        ]
