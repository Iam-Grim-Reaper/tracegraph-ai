import json
from pathlib import Path

from app.graph.models import ExtractedGraph
from app.models.document import DocumentChunk


class GraphExtractionCache:
    CACHE_VERSION = "graph-extraction-v1"

    def __init__(
        self,
        cache_dir: str | Path = ".cache/graph_extractions",
    ):
        self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def get(
        self,
        chunk: DocumentChunk,
    ) -> ExtractedGraph | None:
        path = self._cache_path(
            chunk
        )

        if not path.exists():
            return None

        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            return ExtractedGraph.model_validate(
                payload["graph"]
            )

        except (
            json.JSONDecodeError,
            KeyError,
            ValueError,
        ):
            return None

    def set(
        self,
        chunk: DocumentChunk,
        graph: ExtractedGraph,
    ) -> None:
        path = self._cache_path(
            chunk
        )

        payload = {
            "cache_version": (
                self.CACHE_VERSION
            ),
            "chunk_id": str(
                chunk.id
            ),
            "document_id": str(
                chunk.document_id
            ),
            "chunk_index": (
                chunk.chunk_index
            ),
            "graph": graph.model_dump(
                mode="json"
            ),
        }

        path.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def has(
        self,
        chunk: DocumentChunk,
    ) -> bool:
        return (
            self._cache_path(
                chunk
            ).exists()
        )

    def _cache_path(
        self,
        chunk: DocumentChunk,
    ) -> Path:
        filename = (
            f"{self.CACHE_VERSION}_"
            f"{chunk.document_id}_"
            f"{chunk.id}.json"
        )

        return (
            self.cache_dir
            / filename
        )