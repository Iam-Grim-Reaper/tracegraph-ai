from pathlib import Path

from app.graph.entity_resolver import (
    GlobalEntityResolver,
)
from app.graph.extractor import (
    GraphExtractor,
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
from app.ingestion.chunker import (
    TextChunker,
)
from app.ingestion.loaders.pdf_loader import (
    PDFLoader,
)


def main():
    pdf_path = Path(
        "../data/sample.pdf"
    )

    print("Loading PDF...")

    loader = PDFLoader()

    document, pages = loader.load(
        pdf_path
    )

    chunker = TextChunker(
        max_chars=1000
    )

    chunks = chunker.chunk_pages(
        document=document,
        pages=pages,
    )

    selected_indexes = {
        11,
        15,
        18,
        22,
        25,
    }

    selected_chunks = [
        chunk
        for chunk in chunks
        if chunk.chunk_index
        in selected_indexes
    ]

    print(
        f"Extracting graph from "
        f"{len(selected_chunks)} chunks..."
    )

    extractor = GraphExtractor()

    extracted = extractor.extract_chunks(
        document=document,
        chunks=selected_chunks,
        batch_size=5,
    )

    processor = GraphPostProcessor()

    store = Neo4jGraphStore()

    resolver = GlobalEntityResolver(
        store=store
    )

    writer = Neo4jGraphWriter(
        store=store
    )

    try:
        store.verify_connectivity()

        total_local_entities = 0
        total_resolved_entities = 0
        total_relationships = 0
        total_rejected = 0

        for chunk in selected_chunks:
            raw_graph = extracted[
                chunk.chunk_index
            ]

            # 1. Local post-processing:
            # aliases, normalization,
            # relationship validation,
            # evidence grounding.
            processed = processor.process(
                document=document,
                chunk=chunk,
                extracted_graph=raw_graph,
            )

            # 2. Global entity resolution:
            # compare chunk-local entities
            # against entities that already
            # exist in Neo4j.
            resolved = resolver.resolve(
                processed
            )

            print(
                f"\nChunk "
                f"{chunk.chunk_index}:"
            )

            print(
                "  Local entities: "
                f"{len(processed.entities)}"
            )

            print(
                "  Globally resolved entities: "
                f"{len(resolved.entities)}"
            )

            print(
                "  Accepted relationships: "
                f"{len(resolved.relationships)}"
            )

            print(
                "  Rejected relationships: "
                f"{len(resolved.rejected_relationships)}"
            )

            for rejected in (
                resolved.rejected_relationships
            ):
                relationship = (
                    rejected.relationship
                )

                print(
                    "    REJECTED: "
                    f"{relationship.source_name} "
                    f"{relationship.relationship_type.value} "
                    f"{relationship.target_name}"
                )

                print(
                    "    Reason: "
                    f"{rejected.reason}"
                )

            # Write only the globally resolved
            # graph to Neo4j.
            writer.write_chunk_graph(
                document=document,
                chunk=chunk,
                graph=resolved,
            )

            total_local_entities += len(
                processed.entities
            )

            total_resolved_entities += len(
                resolved.entities
            )

            total_relationships += len(
                resolved.relationships
            )

            total_rejected += len(
                resolved.rejected_relationships
            )

        print("\n" + "=" * 60)
        print("GRAPH INDEXING COMPLETE")
        print("=" * 60)

        print(
            "Local entity occurrences:",
            total_local_entities,
        )

        print(
            "Resolved entity occurrences:",
            total_resolved_entities,
        )

        print(
            "Accepted relationship occurrences:",
            total_relationships,
        )

        print(
            "Rejected relationship occurrences:",
            total_rejected,
        )

        counts = store.query(
            """
            MATCH (d:Document)
            WITH count(d) AS documents

            MATCH (c:Chunk)
            WITH
                documents,
                count(c) AS chunks

            MATCH (e:Entity)

            RETURN
                documents,
                chunks,
                count(e) AS entities
            """
        )

        print("\nNeo4j counts:")
        print(counts)

        relationship_counts = store.query(
            """
            MATCH ()-[r]->()

            RETURN
                type(r)
                    AS relationship_type,
                count(r)
                    AS count

            ORDER BY
                relationship_type
            """
        )

        print(
            "\nRelationship counts:"
        )

        for row in relationship_counts:
            print(row)

    finally:
        store.close()


if __name__ == "__main__":
    main()