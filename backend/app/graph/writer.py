from app.graph.normalizer import (
    EntityNormalizer,
)
from app.graph.ontology import (
    OntologyProfile,
    RESEARCH_ONTOLOGY,
)
from app.graph.postprocessor import (
    ProcessedChunkGraph,
)
from app.graph.store import (
    Neo4jGraphStore,
)
from app.models.document import (
    Document,
    DocumentChunk,
)


class Neo4jGraphWriter:
    """
    Writes ontology-aware document graph data
    into the global Neo4j knowledge graph.

    Important invariant:

    Each chunk owns the graph evidence that was
    extracted from that chunk.

    When the same chunk is re-indexed, its old:

        MENTIONS relationships
        semantic relationships

    are removed before the new extraction is
    written.

    Global Entity nodes are NOT deleted because
    they may be shared by other documents and
    chunks.
    """

    def __init__(
        self,
        store: Neo4jGraphStore,
        ontology_profile: (
            OntologyProfile | None
        ) = None,
    ):
        self.store = store

        self.normalizer = (
            EntityNormalizer()
        )

        self.ontology_profile = (
            ontology_profile
            or RESEARCH_ONTOLOGY
        )

    def write_chunk_graph(
        self,
        document: Document,
        chunk: DocumentChunk,
        graph: ProcessedChunkGraph,
    ) -> None:
        # -------------------------------------------------
        # 1. Ensure the Document and Chunk exist.
        # -------------------------------------------------

        self._write_document_and_chunk(
            document=document,
            chunk=chunk,
        )

        # -------------------------------------------------
        # 2. Remove graph evidence previously owned by
        #    THIS chunk.
        #
        # This is critical for:
        #
        # - ontology upgrades
        # - changed extraction results
        # - re-indexing
        #
        # Other documents/chunks remain untouched.
        # -------------------------------------------------

        self._clear_chunk_graph(
            chunk=chunk
        )

        # -------------------------------------------------
        # 3. Merge globally reusable entities.
        # -------------------------------------------------

        self._write_entities(
            entities=graph.entities
        )

        # -------------------------------------------------
        # 4. Write current chunk/entity mentions.
        # -------------------------------------------------

        self._write_mentions(
            chunk=chunk,
            graph=graph,
        )

        # -------------------------------------------------
        # 5. Write current semantic relationships.
        # -------------------------------------------------

        self._write_relationships(
            relationships=(
                graph.relationships
            )
        )

    # =====================================================
    # Document + Chunk
    # =====================================================

    def _write_document_and_chunk(
        self,
        document: Document,
        chunk: DocumentChunk,
    ) -> None:
        self.store.query(
            """
            MERGE (
                d:Document {
                    document_id:
                        $document_id
                }
            )

            ON CREATE SET
                d.indexing_status =
                    'indexing'

            SET
                d.filename =
                    $filename,

                d.file_type =
                    $file_type,

                d.title =
                    $title,

                d.author =
                    $author,

                d.ontology_profile =
                    $ontology_profile,

                d.ontology_version =
                    $ontology_version

            MERGE (
                c:Chunk {
                    chunk_id:
                        $chunk_id
                }
            )

            SET
                c.document_id =
                    $document_id,

                c.chunk_index =
                    $chunk_index,

                c.page_number =
                    $page_number,

                c.source_locator_type =
                    $source_locator_type,

                c.source_locator_label =
                    $source_locator_label,

                c.text =
                    $text,

                c.ontology_profile =
                    $ontology_profile,

                c.ontology_version =
                    $ontology_version

            MERGE (
                d
            )-[:CONTAINS]->(
                c
            )
            """,
            {
                "document_id": str(
                    document.id
                ),

                "filename": (
                    document.filename
                ),

                "file_type": (
                    document.file_type.value
                ),

                "title": (
                    document.metadata.title
                ),

                "author": (
                    document.metadata.author
                ),

                "chunk_id": str(
                    chunk.id
                ),

                "chunk_index": (
                    chunk.chunk_index
                ),

                "page_number": (
                    chunk.metadata.page_number
                ),

                "source_locator_type": (
                    chunk.metadata.source_locator.type
                    if chunk.metadata.source_locator else None
                ),

                "source_locator_label": (
                    chunk.metadata.source_locator.label
                    if chunk.metadata.source_locator else None
                ),

                "text": (
                    chunk.text
                ),

                "ontology_profile": (
                    self.ontology_profile.name
                ),

                "ontology_version": (
                    self.ontology_profile.version
                ),
            },
        )

    # =====================================================
    # Replace old chunk-owned graph evidence
    # =====================================================

    def _clear_chunk_graph(
        self,
        chunk: DocumentChunk,
    ) -> None:
        """
        Remove graph evidence previously derived
        from this specific chunk.

        We intentionally DO NOT delete:

        - the Chunk node
        - the Document node
        - Entity nodes
        - evidence from other chunks/documents
        - CONTAINS

        Only chunk-owned evidence is replaced.
        """

        chunk_id = str(
            chunk.id
        )

        # -------------------------------------------------
        # Remove old semantic relationships produced
        # from this chunk.
        #
        # Every extracted semantic relationship stores
        # source_chunk_id provenance.
        # -------------------------------------------------

        self.store.query(
            """
            MATCH ()-[r]->()

            WHERE
                r.source_chunk_id =
                    $chunk_id

                AND NOT type(r) IN [
                    'CONTAINS',
                    'MENTIONS'
                ]

            DELETE r
            """,
            {
                "chunk_id": (
                    chunk_id
                )
            },
        )

        # -------------------------------------------------
        # Remove old mention edges for this chunk.
        #
        # They will be reconstructed from the current
        # ontology/extraction output immediately after.
        # -------------------------------------------------

        self.store.query(
            """
            MATCH (
                c:Chunk {
                    chunk_id:
                        $chunk_id
                }
            )-[r:MENTIONS]->(
                :Entity
            )

            DELETE r
            """,
            {
                "chunk_id": (
                    chunk_id
                )
            },
        )

    # =====================================================
    # Entities
    # =====================================================

    def _write_entities(
        self,
        entities,
    ) -> None:
        for entity in entities:
            # Store normalized aliases so that
            # global entity resolution can
            # efficiently match aliases across
            # different chunks/documents.

            normalized_aliases = sorted(
                {
                    self.normalizer
                    .normalize_name(
                        alias
                    )

                    for alias
                    in entity.aliases

                    if alias.strip()
                }
            )

            self.store.query(
                """
                MERGE (
                    e:Entity {
                        entity_id:
                            $entity_id
                    }
                )

                ON CREATE SET
                    e.name =
                        $name,

                    e.normalized_name =
                        $normalized_name

                SET
                    e.entity_type =
                        $entity_type,

                    e.original_entity_type =
                        coalesce($original_entity_type, e.original_entity_type),

                    e.aliases =
                        reduce(
                            acc =
                                coalesce(
                                    e.aliases,
                                    []
                                ),

                            alias
                            IN $aliases |

                            CASE
                                WHEN
                                    alias
                                    IN acc

                                THEN acc

                                ELSE
                                    acc + alias
                            END
                        ),

                    e.normalized_aliases =
                        reduce(
                            acc =
                                coalesce(
                                    e.normalized_aliases,
                                    []
                                ),

                            alias
                            IN $normalized_aliases |

                            CASE
                                WHEN
                                    alias
                                    IN acc

                                THEN acc

                                ELSE
                                    acc + alias
                            END
                        )

                SET e:$($entity_label)
                """,
                {
                    "entity_id": (
                        entity.entity_id
                    ),

                    "name": (
                        entity.name
                    ),

                    "normalized_name": (
                        entity.normalized_name
                    ),

                    "entity_type": (
                        entity
                        .entity_type
                        .value
                    ),

                    "original_entity_type": entity.original_entity_type,

                    "entity_label": (
                        entity
                        .entity_type
                        .value
                    ),

                    "aliases": (
                        entity.aliases
                    ),

                    "normalized_aliases": (
                        normalized_aliases
                    ),
                },
            )

    # =====================================================
    # Mentions
    # =====================================================

    def _write_mentions(
        self,
        chunk: DocumentChunk,
        graph: ProcessedChunkGraph,
    ) -> None:
        for entity in graph.entities:
            self.store.query(
                """
                MATCH (
                    c:Chunk {
                        chunk_id:
                            $chunk_id
                    }
                )

                MATCH (
                    e:Entity {
                        entity_id:
                            $entity_id
                    }
                )

                MERGE (
                    c
                )-[
                    r:MENTIONS
                ]->(
                    e
                )

                SET
                    r.ontology_profile =
                        $ontology_profile,

                    r.ontology_version =
                        $ontology_version
                """,
                {
                    "chunk_id": str(
                        chunk.id
                    ),

                    "entity_id": (
                        entity.entity_id
                    ),

                    "ontology_profile": (
                        self
                        .ontology_profile
                        .name
                    ),

                    "ontology_version": (
                        self
                        .ontology_profile
                        .version
                    ),
                },
            )

    # =====================================================
    # Semantic relationships
    # =====================================================

    def _write_relationships(
        self,
        relationships,
    ) -> None:
        for relationship in relationships:
            self.store.query(
                """
                MATCH (
                    source:Entity {
                        entity_id:
                            $source_entity_id
                    }
                )

                MATCH (
                    target:Entity {
                        entity_id:
                            $target_entity_id
                    }
                )

                MERGE (
                    source
                )-[
                    r:$($relationship_type) {
                        source_chunk_id:
                            $source_chunk_id
                    }
                ]->(
                    target
                )

                SET
                    r.confidence =
                        $confidence,

                    r.evidence_text =
                        $evidence_text,

                    r.source_document_id =
                        $source_document_id,

                    r.page_number =
                        $page_number,

                    r.ontology_profile =
                        $ontology_profile,

                    r.ontology_version =
                        $ontology_version
                """,
                {
                    "source_entity_id": (
                        relationship
                        .source_entity_id
                    ),

                    "target_entity_id": (
                        relationship
                        .target_entity_id
                    ),

                    "relationship_type": (
                        relationship
                        .relationship_type
                        .value
                    ),

                    "confidence": (
                        relationship.confidence
                    ),

                    "evidence_text": (
                        relationship
                        .evidence_text
                    ),

                    "source_document_id": (
                        relationship
                        .source_document_id
                    ),

                    "source_chunk_id": (
                        relationship
                        .source_chunk_id
                    ),

                    "page_number": (
                        relationship.page_number
                    ),

                    "ontology_profile": (
                        self
                        .ontology_profile
                        .name
                    ),

                    "ontology_version": (
                        self
                        .ontology_profile
                        .version
                    ),
                },
            )
