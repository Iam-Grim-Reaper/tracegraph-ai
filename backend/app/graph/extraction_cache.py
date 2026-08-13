import json
from pathlib import Path

from app.core.config import settings
from app.graph.models import (
    ExtractedGraph,
)
from app.graph.ontology import (
    OntologyProfile,
    RESEARCH_ONTOLOGY,
)
from app.models.document import (
    DocumentChunk,
)


class GraphExtractionCache:
    """
    Ontology-aware graph extraction cache.

    Cache identity includes:

    - cache format version
    - ontology profile
    - ontology version
    - document ID
    - chunk ID

    Therefore the same chunk extracted under
    different ontologies can never accidentally
    share cached graph output.
    """

    CACHE_VERSION = (
        "graph-extraction-v2.2"
    )

    def __init__(
        self,
        cache_dir: (
            str | Path | None
        ) = None,
        ontology_profile: (
            OntologyProfile | None
        ) = None,
    ):
        self.cache_dir = Path(
            cache_dir
            or settings.graph_extraction_cache_dir
        )

        self.ontology_profile = (
            ontology_profile
            or RESEARCH_ONTOLOGY
        )

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

            # -----------------------------------------
            # Defensive metadata validation
            # -----------------------------------------

            if (
                payload.get(
                    "cache_version"
                )
                != self.CACHE_VERSION
            ):
                return None

            if (
                payload.get(
                    "ontology_profile"
                )
                != self.ontology_profile.name
            ):
                return None

            if (
                payload.get(
                    "ontology_version"
                )
                != self.ontology_profile.version
            ):
                return None

            if (
                payload.get(
                    "chunk_id"
                )
                != str(
                    chunk.id
                )
            ):
                return None

            if (
                payload.get(
                    "document_id"
                )
                != str(
                    chunk.document_id
                )
            ):
                return None

            return (
                ExtractedGraph
                .model_validate(
                    payload["graph"]
                )
            )

        except (
            json.JSONDecodeError,
            KeyError,
            TypeError,
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

            "ontology_profile": (
                self.ontology_profile.name
            ),

            "ontology_version": (
                self.ontology_profile.version
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

            "graph": (
                graph.model_dump(
                    mode="json"
                )
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
            self.get(
                chunk
            )
            is not None
        )

    def _cache_path(
        self,
        chunk: DocumentChunk,
    ) -> Path:
        filename = (
            f"{self.CACHE_VERSION}_"
            f"{self.ontology_profile.name}_"
            f"ontology-{self.ontology_profile.version}_"
            f"{chunk.document_id}_"
            f"{chunk.id}.json"
        )

        return (
            self.cache_dir
            / filename
        )
