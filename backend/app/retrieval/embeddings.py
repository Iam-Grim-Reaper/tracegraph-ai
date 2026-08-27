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

        for start in range(0, len(texts), batch_size):
            batch = texts[
                start : start + batch_size
            ]

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
