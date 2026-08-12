import json

from dataclasses import dataclass
from pathlib import Path

from app.graph.indexer import (
    GraphIndexer,
)
from app.graph.ontology import (
    OntologyProfile,
)
from app.graph.ontology_classifier import (
    OntologyClassification,
    OntologyClassifier,
)
from app.graph.store import (
    Neo4jGraphStore,
)
from app.ingestion.service import (
    IngestionService,
)
from app.retrieval.hybrid_indexer import (
    HybridIndexer,
)


@dataclass
class DocumentIndexingResult:
    document_id: str
    filename: str
    file_type: str
    title: str | None

    # =========================================
    # Ontology metadata
    # =========================================

    ontology_profile: str
    ontology_version: str

    ontology_profiles: list[
        str
    ]

    ontology_confidence: float
    ontology_method: str
    ontology_reason: str

    ontology_scores: dict[
        str,
        float,
    ]

    # =========================================
    # Indexing statistics
    # =========================================

    chunk_count: int

    qdrant_indexed_chunks: int

    graph_entity_count: int

    graph_relationship_count: int

    graph_rejected_relationship_count: (
        int
    )

    graph_cached_chunks: int
    graph_extracted_chunks: int

    status: str = "ready"


class DocumentIndexingService:
    """
    Complete TraceGraph document indexing
    orchestration service.

    Pipeline:

        file
          ↓
        ingestion
          ↓
        stable chunks
          ↓
        automatic ontology classification
          ↓
        optional ontology composition
          ↓
        contextual hybrid indexing
          ↓
        ontology-aware graph indexing
          ↓
        ontology metadata persistence
          ↓
        ready

    An ontology may also be explicitly supplied
    for testing, evaluation, or administrative
    override.
    """

    def __init__(
        self,
        max_chars: int = 1000,
        graph_batch_size: int = 5,
        ontology_profile: (
            OntologyProfile | None
        ) = None,
    ):
        self.ingestion_service = (
            IngestionService(
                max_chars=max_chars
            )
        )

        self.graph_batch_size = (
            graph_batch_size
        )

        # None means automatic classification.
        self.ontology_profile = (
            ontology_profile
        )

        self.ontology_classifier = (
            OntologyClassifier()
        )

    def index_file(
        self,
        file_path: str | Path,
    ) -> DocumentIndexingResult:
        path = Path(
            file_path
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Document not found: "
                f"{path}"
            )

        print("=" * 70)

        print(
            "TRACEGRAPH DOCUMENT INDEX"
        )

        print("=" * 70)

        # =========================================
        # 1. Ingestion
        # =========================================

        print(
            "\n[1/3] Ingesting document..."
        )

        ingestion = (
            self.ingestion_service
            .ingest(
                path
            )
        )

        document = (
            ingestion.document
        )

        chunks = (
            ingestion.chunks
        )

        if not chunks:
            raise RuntimeError(
                "Document ingestion "
                "produced no chunks"
            )

        print(
            "Document ID:",
            document.id,
        )

        print(
            "Filename:",
            document.filename,
        )

        print(
            "Chunks:",
            len(chunks),
        )

        # =========================================
        # Reconstruct document-level text
        # =========================================

        document_text = (
            "\n\n".join(
                chunk.text

                for chunk
                in chunks

                if chunk.text.strip()
            )
        )

        if not document_text.strip():
            raise RuntimeError(
                "Document contains no "
                "usable text"
            )

        # =========================================
        # Ontology selection
        # =========================================

        if (
            self.ontology_profile
            is not None
        ):
            selected_ontology = (
                self.ontology_profile
            )

            selected_profiles = (
                self
                ._profile_components(
                    selected_ontology.name
                )
            )

            ontology_classification = (
                OntologyClassification(
                    profile=(
                        selected_ontology
                    ),

                    confidence=1.0,

                    method="explicit",

                    reason=(
                        "Ontology profile was "
                        "explicitly supplied."
                    ),

                    scores={},

                    selected_profiles=(
                        selected_profiles
                    ),
                )
            )

        else:
            print(
                "\nClassifying document "
                "ontology..."
            )

            ontology_classification = (
                self.ontology_classifier
                .classify(
                    document=document,

                    document_text=(
                        document_text
                    ),
                )
            )

            selected_ontology = (
                ontology_classification
                .profile
            )

        print(
            "Selected ontology:",
            selected_ontology.name,
        )

        print(
            "Selected profiles:",
            ontology_classification
            .selected_profiles,
        )

        print(
            "Ontology version:",
            selected_ontology.version,
        )

        print(
            "Ontology confidence:",
            (
                f"{ontology_classification.confidence:.2f}"
            ),
        )

        print(
            "Ontology selection method:",
            ontology_classification.method,
        )

        print(
            "Ontology reason:",
            ontology_classification.reason,
        )

        if (
            ontology_classification.scores
        ):
            print(
                "Ontology scores:",
                ontology_classification
                .scores,
            )

        # =========================================
        # 2. Qdrant hybrid indexing
        # =========================================

        print(
            "\n[2/3] Building hybrid index..."
        )

        hybrid_indexer = (
            HybridIndexer()
        )

        qdrant_count = (
            hybrid_indexer.index(
                document=document,

                chunks=chunks,

                document_text=(
                    document_text
                ),

                reset_collection=False,
            )
        )

        print(
            "Qdrant chunks indexed:",
            qdrant_count,
        )

        # =========================================
        # 3. Neo4j graph indexing
        # =========================================

        print(
            "\n[3/3] Building "
            "knowledge graph..."
        )

        graph_indexer = (
            GraphIndexer(
                batch_size=(
                    self.graph_batch_size
                ),

                ontology_profile=(
                    selected_ontology
                ),
            )
        )

        graph_stats = (
            graph_indexer.index(
                document=document,
                chunks=chunks,
            )
        )

        # =========================================
        # Persist classification metadata
        #
        # GraphWriter already stores:
        #
        # ontology_profile
        # ontology_version
        #
        # This adds classifier-specific metadata
        # to the Document node.
        # =========================================

        self._persist_ontology_metadata(
            document_id=str(
                document.id
            ),

            classification=(
                ontology_classification
            ),
        )

        # =========================================
        # Complete
        # =========================================

        print(
            "\n" + "=" * 70
        )

        print(
            "DOCUMENT READY"
        )

        print("=" * 70)

        print(
            "Document ID:",
            document.id,
        )

        print(
            "Ontology:",
            selected_ontology.name,
        )

        print(
            "Ontology version:",
            selected_ontology.version,
        )

        print(
            "Chunks:",
            len(chunks),
        )

        print(
            "Entities:",
            graph_stats.entity_count,
        )

        print(
            "Semantic relationships:",
            graph_stats
            .semantic_relationship_count,
        )

        print(
            "Rejected relationships:",
            graph_stats
            .rejected_relationship_count,
        )

        # =========================================
        # Service result
        # =========================================

        return (
            DocumentIndexingResult(
                document_id=str(
                    document.id
                ),

                filename=(
                    document.filename
                ),

                file_type=(
                    document.file_type.value
                ),

                title=(
                    document.metadata.title
                ),

                ontology_profile=(
                    selected_ontology.name
                ),

                ontology_version=(
                    selected_ontology.version
                ),

                ontology_profiles=list(
                    ontology_classification
                    .selected_profiles
                ),

                ontology_confidence=(
                    ontology_classification
                    .confidence
                ),

                ontology_method=(
                    ontology_classification
                    .method
                ),

                ontology_reason=(
                    ontology_classification
                    .reason
                ),

                ontology_scores=dict(
                    ontology_classification
                    .scores
                ),

                chunk_count=(
                    len(chunks)
                ),

                qdrant_indexed_chunks=(
                    qdrant_count
                ),

                graph_entity_count=(
                    graph_stats.entity_count
                ),

                graph_relationship_count=(
                    graph_stats
                    .semantic_relationship_count
                ),

                graph_rejected_relationship_count=(
                    graph_stats
                    .rejected_relationship_count
                ),

                graph_cached_chunks=(
                    graph_stats.cached_chunks
                ),

                graph_extracted_chunks=(
                    graph_stats.extracted_chunks
                ),
            )
        )

    # =====================================================
    # Ontology profile components
    # =====================================================

    @staticmethod
    def _profile_components(
        profile_name: str,
    ) -> tuple[str, ...]:
        normalized = (
            profile_name
            .strip()
            .casefold()
        )

        if not normalized:
            return (
                "general",
            )

        components = tuple(
            component.strip()

            for component
            in normalized.split("+")

            if component.strip()
        )

        return (
            components
            or (
                "general",
            )
        )

    # =====================================================
    # Persist classifier metadata
    # =====================================================

    @staticmethod
    def _persist_ontology_metadata(
        document_id: str,
        classification: (
            OntologyClassification
        ),
    ) -> None:
        """
        Persist ontology-classification metadata
        on the Neo4j Document node.

        Neo4j properties cannot store arbitrary
        nested dictionaries, therefore scores
        are serialized as JSON.
        """

        store = (
            Neo4jGraphStore()
        )

        try:
            store.verify_connectivity()

            store.query(
                """
                MATCH (
                    d:Document {
                        document_id:
                            $document_id
                    }
                )

                SET
                    d.ontology_profile =
                        $ontology_profile,

                    d.ontology_version =
                        $ontology_version,

                    d.ontology_profiles =
                        $ontology_profiles,

                    d.ontology_confidence =
                        $ontology_confidence,

                    d.ontology_method =
                        $ontology_method,

                    d.ontology_reason =
                        $ontology_reason,

                    d.ontology_scores_json =
                        $ontology_scores_json
                """,
                {
                    "document_id": (
                        document_id
                    ),

                    "ontology_profile": (
                        classification
                        .profile
                        .name
                    ),

                    "ontology_version": (
                        classification
                        .profile
                        .version
                    ),

                    "ontology_profiles": list(
                        classification
                        .selected_profiles
                    ),

                    "ontology_confidence": (
                        classification
                        .confidence
                    ),

                    "ontology_method": (
                        classification
                        .method
                    ),

                    "ontology_reason": (
                        classification
                        .reason
                    ),

                    "ontology_scores_json": (
                        json.dumps(
                            classification
                            .scores,

                            sort_keys=True,
                        )
                    ),
                },
            )

        finally:
            store.close()