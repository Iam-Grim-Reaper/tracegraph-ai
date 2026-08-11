from dataclasses import dataclass

from sentence_transformers import CrossEncoder


@dataclass
class RerankedResult:
    point: object
    rerank_score: float


class CrossEncoderReranker:
    def __init__(
        self,
        model_name: str = (
            "cross-encoder/"
            "ms-marco-MiniLM-L6-v2"
        ),
    ):
        self.model_name = model_name

        print(
            f"Loading reranker: {self.model_name}"
        )

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