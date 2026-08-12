from dataclasses import dataclass

from app.graph.entity_resolver import (
    GlobalEntityResolver,
)
from app.graph.extraction_cache import (
    GraphExtractionCache,
)
from app.graph.extractor import (
    GraphExtractor,
)
from app.graph.ontology import (
    OntologyProfile,
    RESEARCH_ONTOLOGY,
)
from app.graph.postprocessor import (
    GraphPostProcessor,
)
from app.graph.store import (
    Neo4jGraphStore,
)
from app.graph.writer import (
    Neo4jGraphWriter,
)
from app.models.document import (
    Document,
    DocumentChunk,
)


@dataclass
class GraphIndexStats:
    chunk_count: int
    cached_chunks: int
    extracted_chunks: int
    entity_count: int
    semantic_relationship_count: int
    rejected_relationship_count: int


class GraphIndexer:
    """
    Reusable ontology-aware production
    graph indexing pipeline.

    Pipeline:

        chunks
          ↓
        ontology-aware cache
          ↓
        ontology-aware extraction
          ↓
        ontology-aware post-processing
          ↓
        global entity resolution
          ↓
        Neo4j writing

    One ontology profile is used consistently
    across the complete indexing operation.
    """

    def __init__(
        self,
        batch_size: int = 5,
        ontology_profile: (
            OntologyProfile | None
        ) = None,
    ):
        if batch_size < 1:
            raise ValueError(
                "batch_size must be at least 1"
            )

        self.batch_size = (
            batch_size
        )

        # -------------------------------------------------
        # Backward-compatible default.
        #
        # Existing TraceGraph development data is
        # research/technical content.
        #
        # Automatic document ontology classification
        # will replace this default selection later.
        # -------------------------------------------------

        self.ontology_profile = (
            ontology_profile
            or RESEARCH_ONTOLOGY
        )

    def index(
        self,
        document: Document,
        chunks: list[DocumentChunk],
    ) -> GraphIndexStats:
        if not chunks:
            raise ValueError(
                "Cannot graph-index a "
                "document with no chunks"
            )

        print(
            "Active ontology:",
            self.ontology_profile.name,
        )

        print(
            "Ontology version:",
            self.ontology_profile.version,
        )

        # =================================================
        # CRITICAL ONTOLOGY INVARIANT
        #
        # Cache
        # Extractor
        # PostProcessor
        # Validator
        #
        # must all operate under the SAME ontology.
        # =================================================

        cache = (
            GraphExtractionCache(
                ontology_profile=(
                    self.ontology_profile
                )
            )
        )

        extracted_graphs: dict = {}

        cached_count = 0

        missing_chunks: list[
            DocumentChunk
        ] = []

        # -------------------------------------------------
        # 1. Reuse ontology-compatible cache
        # -------------------------------------------------

        for chunk in chunks:
            cached = (
                cache.get(
                    chunk
                )
            )

            if cached is not None:
                extracted_graphs[
                    chunk.chunk_index
                ] = cached

                cached_count += 1

            else:
                missing_chunks.append(
                    chunk
                )

        print(
            "Graph cache hits:",
            cached_count,
        )

        print(
            "Graph chunks requiring extraction:",
            len(
                missing_chunks
            ),
        )

        # -------------------------------------------------
        # 2. Extract only chunks missing from
        #    the active ontology cache.
        # -------------------------------------------------

        if missing_chunks:
            extractor = (
                GraphExtractor(
                    ontology_profile=(
                        self.ontology_profile
                    )
                )
            )

            total_batches = (
                len(missing_chunks)
                + self.batch_size
                - 1
            ) // self.batch_size

            for start in range(
                0,
                len(missing_chunks),
                self.batch_size,
            ):
                batch = (
                    missing_chunks[
                        start:
                        start
                        + self.batch_size
                    ]
                )

                batch_number = (
                    start
                    // self.batch_size
                ) + 1

                print(
                    "Graph extraction batch "
                    f"{batch_number}/"
                    f"{total_batches}"
                )

                batch_results = (
                    extractor.extract_chunks(
                        document=document,
                        chunks=batch,
                        batch_size=(
                            len(batch)
                        ),
                    )
                )

                for chunk in batch:
                    graph = (
                        batch_results[
                            chunk.chunk_index
                        ]
                    )

                    extracted_graphs[
                        chunk.chunk_index
                    ] = graph

                    # -------------------------------------
                    # Persist immediately.
                    #
                    # The v2 cache identity includes:
                    #
                    # - cache version
                    # - ontology profile
                    # - ontology version
                    # - document ID
                    # - chunk ID
                    # -------------------------------------

                    cache.set(
                        chunk=chunk,
                        graph=graph,
                    )

        # -------------------------------------------------
        # Safety check:
        #
        # Every supplied chunk must have either
        # cached or newly extracted graph data.
        # -------------------------------------------------

        if (
            len(extracted_graphs)
            != len(chunks)
        ):
            raise RuntimeError(
                "Graph extraction incomplete: "
                f"{len(extracted_graphs)}/"
                f"{len(chunks)}"
            )

        # -------------------------------------------------
        # 3. Post-process + globally resolve +
        #    write to Neo4j
        # -------------------------------------------------

        processor = (
            GraphPostProcessor(
                ontology_profile=(
                    self.ontology_profile
                )
            )
        )

        store = (
            Neo4jGraphStore()
        )

        resolver = (
            GlobalEntityResolver(
                store=store
            )
        )

        writer = (
             Neo4jGraphWriter(
                store=store,
                ontology_profile=(
                    self.ontology_profile
                ),
            )
        )

        rejected_count = 0

        try:
            store.verify_connectivity()

            for number, chunk in enumerate(
                chunks,
                start=1,
            ):
                raw_graph = (
                    extracted_graphs[
                        chunk.chunk_index
                    ]
                )

                # -----------------------------------------
                # Deterministic normalization,
                # canonicalization and validation.
                #
                # GraphPostProcessor uses the SAME
                # ontology profile.
                # -----------------------------------------

                processed = (
                    processor.process(
                        document=document,
                        chunk=chunk,
                        extracted_graph=(
                            raw_graph
                        ),
                    )
                )

                # -----------------------------------------
                # Resolve chunk-local entities against
                # the existing global knowledge graph.
                # -----------------------------------------

                resolved = (
                    resolver.resolve(
                        processed
                    )
                )

                # -----------------------------------------
                # Stable MERGE-based Neo4j write.
                # -----------------------------------------

                writer.write_chunk_graph(
                    document=document,
                    chunk=chunk,
                    graph=resolved,
                )

                rejected_count += len(
                    resolved
                    .rejected_relationships
                )

                print(
                    "Graph indexed chunk "
                    f"{number}/"
                    f"{len(chunks)}"
                )

            # -------------------------------------------------
            # 4. Stored-document statistics
            # -------------------------------------------------

            document_rows = (
                store.query(
                    """
                    MATCH (
                        d:Document {
                            document_id:
                                $document_id
                        }
                    )

                    OPTIONAL MATCH (
                        d
                    )-[:CONTAINS]->(
                        c:Chunk
                    )

                    WITH
                        d,
                        count(
                            DISTINCT c
                        ) AS chunk_count

                    OPTIONAL MATCH (
                        d
                    )-[:CONTAINS]->(
                        source_chunk:Chunk
                    )-[:MENTIONS]->(
                        e:Entity
                    )

                    RETURN
                        chunk_count,
                        count(
                            DISTINCT e
                        ) AS entity_count
                    """,
                    {
                        "document_id": str(
                            document.id
                        )
                    },
                )
            )

            relationship_rows = (
                store.query(
                    """
                    MATCH ()-[r]->()

                    WHERE
                        r.source_document_id
                            = $document_id

                        AND NOT type(r) IN [
                            'CONTAINS',
                            'MENTIONS'
                        ]

                    RETURN
                        count(r)
                        AS relationship_count
                    """,
                    {
                        "document_id": str(
                            document.id
                        )
                    },
                )
            )

            document_stats = (
                document_rows[0]
                if document_rows
                else {}
            )

            relationship_stats = (
                relationship_rows[0]
                if relationship_rows
                else {}
            )

            return (
                GraphIndexStats(
                    chunk_count=(
                        document_stats.get(
                            "chunk_count",
                            len(chunks),
                        )
                    ),

                    cached_chunks=(
                        cached_count
                    ),

                    extracted_chunks=(
                        len(
                            missing_chunks
                        )
                    ),

                    entity_count=(
                        document_stats.get(
                            "entity_count",
                            0,
                        )
                    ),

                    semantic_relationship_count=(
                        relationship_stats.get(
                            "relationship_count",
                            0,
                        )
                    ),

                    rejected_relationship_count=(
                        rejected_count
                    ),
                )
            )

        finally:
            store.close()