from dataclasses import dataclass
import logging
import os
from time import perf_counter

from sentence_transformers import CrossEncoder
import torch

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

        texts = [
            (result.payload or {}).get("text", "")
            for result in results
        ]

        scores = self._score(query, texts)

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

        scores = self._score(query, texts)

        return [
            float(score)
            for score in scores
        ]

    def _score(
        self,
        query: str,
        texts: list[str],
    ):
        total_started = perf_counter()

        pair_started = perf_counter()
        pairs = [(query, text) for text in texts]
        pair_construction_latency_ms = (
            perf_counter() - pair_started
        ) * 1000

        predict_started = perf_counter()
        scores = self.model.predict(
            pairs,
            show_progress_bar=False,
        )
        model_predict_latency_ms = (
            perf_counter() - predict_started
        ) * 1000
        total_latency_ms = (
            perf_counter() - total_started
        ) * 1000

        log_event(
            logger,
            logging.INFO,
            "reranker_scored",
            operation="reranker_scoring",
            status="complete",
            reranker_input_count=len(texts),
            reranker_total_chars=sum(len(text) for text in texts),
            reranker_max_chars=max((len(text) for text in texts), default=0),
            pair_construction_latency_ms=round(pair_construction_latency_ms, 3),
            # CrossEncoder.predict performs tokenization and model inference
            # in one public call. Keeping that call intact avoids duplicate
            # tokenization or global monkey-patching in concurrent requests.
            model_predict_latency_ms=round(model_predict_latency_ms, 3),
            total_latency_ms=round(total_latency_ms, 3),
            model_max_length=getattr(self.model, "max_length", None),
            model_device=str(getattr(self.model, "device", "unknown")),
            cpu_count=os.cpu_count(),
            torch_num_threads=torch.get_num_threads(),
            torch_num_interop_threads=torch.get_num_interop_threads(),
        )

        return scores
