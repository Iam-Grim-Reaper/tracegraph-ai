from app.graph.postprocessor import (
    ProcessedChunkGraph,
)
from app.graph.store import Neo4jGraphStore
from app.models.document import (
    Document,
    DocumentChunk,
)


class Neo4jGraphWriter:
    def __init__(
        self,
        store: Neo4jGraphStore,
    ):
        self.store = store

    def write_chunk_graph(
        self,
        document: Document,
        chunk: DocumentChunk,
        graph: ProcessedChunkGraph,
    ) -> None:
        self._write_document_and_chunk(
            document=document,
            chunk=chunk,
        )

        self._write_entities(
            entities=graph.entities
        )

        self._write_mentions(
            chunk=chunk,
            graph=graph,
        )

        self._write_relationships(
            relationships=(
                graph.relationships
            )
        )

    def _write_document_and_chunk(
        self,
        document: Document,
        chunk: DocumentChunk,
    ) -> None:
        self.store.query(
            """
            MERGE (
                d:Document {
                    document_id: $document_id
                }
            )
            SET
                d.filename = $filename,
                d.file_type = $file_type,
                d.title = $title,
                d.author = $author

            MERGE (
                c:Chunk {
                    chunk_id: $chunk_id
                }
            )
            SET
                c.document_id = $document_id,
                c.chunk_index = $chunk_index,
                c.page_number = $page_number,
                c.text = $text

            MERGE (d)-[:CONTAINS]->(c)
            """,
            {
                "document_id": str(
                    document.id
                ),
                "filename": document.filename,
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
                "text": chunk.text,
            },
        )

    def _write_entities(
        self,
        entities,
    ) -> None:
        for entity in entities:
            self.store.query(
                """
                MERGE (
                    e:Entity {
                        entity_id: $entity_id
                    }
                )

                ON CREATE SET
                    e.name = $name,
                    e.normalized_name =
                        $normalized_name

                SET
                    e.entity_type =
                        $entity_type,
                    e.aliases =
                        reduce(
                            acc =
                                coalesce(
                                    e.aliases,
                                    []
                                ),
                            alias IN $aliases |
                            CASE
                                WHEN alias IN acc
                                THEN acc
                                ELSE acc + alias
                            END
                        )

                SET e:$($entity_label)
                """,
                {
                    "entity_id": (
                        entity.entity_id
                    ),
                    "name": entity.name,
                    "normalized_name": (
                        entity.normalized_name
                    ),
                    "entity_type": (
                        entity.entity_type.value
                    ),
                    "entity_label": (
                        entity.entity_type.value
                    ),
                    "aliases": entity.aliases,
                },
            )

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
                        chunk_id: $chunk_id
                    }
                )

                MATCH (
                    e:Entity {
                        entity_id: $entity_id
                    }
                )

                MERGE (c)-[:MENTIONS]->(e)
                """,
                {
                    "chunk_id": str(
                        chunk.id
                    ),
                    "entity_id": (
                        entity.entity_id
                    ),
                },
            )

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
                        $page_number
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
                },
            )