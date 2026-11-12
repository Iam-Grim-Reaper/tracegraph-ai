from collections import deque
from time import monotonic, sleep

from google.genai import types

from app.core.config import settings
from app.core.provider_resilience import (
    call_with_provider_resilience,
    create_gemini_client,
)


class GeminiEmbeddingService:
    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured"
            )

        self.client = create_gemini_client(
            settings.provider_default_timeout_seconds
        )

        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions

    def embed_document(
        self,
        text: str,
        title: str | None = None,
    ) -> list[float]:
        if not text.strip():
            raise ValueError(
                "Cannot embed empty document text"
            )

        prepared_text = self._prepare_document(
            text=text,
            title=title,
        )

        return self._embed(prepared_text)

    def embed_documents(
        self,
        texts: list[str],
        title: str | None = None,
        batch_size: int = 16,
    ) -> list[list[float]]:
        if not texts:
            raise ValueError(
                "Cannot embed an empty document list"
            )

        if batch_size < 1:
            raise ValueError(
                "batch_size must be at least 1"
            )

        all_embeddings: list[list[float]] = []

        # Google's free-tier per-minute quota is counted per embedded text,
        # not per Python batch. Limit ingestion throughput before provider
        # calls; interactive query embeddings are deliberately unaffected.
        per_minute = settings.embedding_ingest_texts_per_minute
        effective_batch_size = min(batch_size, per_minute) if per_minute else batch_size
        for start in range(0, len(texts), effective_batch_size):
            batch = texts[start : start + effective_batch_size]
            self._reserve_ingestion_embedding_budget(len(batch))

            contents = [
                types.Content(
                    parts=[
                        types.Part.from_text(
                            text=self._prepare_document(
                                text=text,
                                title=title,
                            )
                        )
                    ]
                )
                for text in batch
            ]

            response = call_with_provider_resilience(lambda: self.client.models.embed_content(
                model=self.model,
                contents=contents,
                config=types.EmbedContentConfig(
                    output_dimensionality=self.dimensions,
                ),
            ))

            if not response.embeddings:
                raise RuntimeError(
                    "Gemini returned no embeddings"
                )

            if len(response.embeddings) != len(batch):
                raise RuntimeError(
                    "Gemini returned an unexpected "
                    "number of embeddings"
                )

            for embedding_object in response.embeddings:
                values = embedding_object.values

                if values is None:
                    raise RuntimeError(
                        "Gemini returned an empty embedding"
                    )

                embedding = list(values)

                if len(embedding) != self.dimensions:
                    raise RuntimeError(
                        f"Expected {self.dimensions} dimensions, "
                        f"received {len(embedding)}"
                    )

                all_embeddings.append(embedding)

        return all_embeddings

    def _reserve_ingestion_embedding_budget(self, count: int) -> None:
        limit = settings.embedding_ingest_texts_per_minute
        if not limit:
            return
        if count > limit:
            raise ValueError("Embedding batch exceeds ingestion quota limit")

        # One meter per indexing service invocation. The queue contains
        # timestamps for individual embedded texts rather than API requests.
        meter = getattr(self, "_ingest_embedding_times", None)
        if meter is None:
            meter = deque()
            self._ingest_embedding_times = meter
        while True:
            now = monotonic()
            while meter and now - meter[0] >= 60.0:
                meter.popleft()
            if len(meter) + count <= limit:
                meter.extend([now] * count)
                return
            sleep(max(0.05, 60.2 - (now - meter[0])))

    def embed_query(
        self,
        query: str,
    ) -> list[float]:
        if not query.strip():
            raise ValueError(
                "Cannot embed empty query"
            )

        prepared_query = (
            f"task: search result | query: {query}"
        )

        return self._embed(prepared_query)

    def _embed(
        self,
        text: str,
    ) -> list[float]:
        response = call_with_provider_resilience(lambda: self.client.models.embed_content(
            model=self.model,
            contents=text,
            config=types.EmbedContentConfig(
                output_dimensionality=self.dimensions,
            ),
        ))

        if not response.embeddings:
            raise RuntimeError(
                "Gemini returned no embeddings"
            )

        values = response.embeddings[0].values

        if values is None:
            raise RuntimeError(
                "Gemini returned an empty embedding"
            )

        embedding = list(values)

        if len(embedding) != self.dimensions:
            raise RuntimeError(
                f"Expected {self.dimensions} dimensions, "
                f"received {len(embedding)}"
            )

        return embedding

    @staticmethod
    def _prepare_document(
        text: str,
        title: str | None = None,
    ) -> str:
        document_title = title or "none"

        return (
            f"title: {document_title} | "
            f"text: {text}"
        )
