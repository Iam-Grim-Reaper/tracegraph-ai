from pathlib import Path

from app.graph.extractor import GraphExtractor
from app.graph.postprocessor import (
    GraphPostProcessor,
)
from app.graph.store import Neo4jGraphStore
from app.graph.writer import Neo4jGraphWriter
from app.ingestion.chunker import TextChunker
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

    writer = Neo4jGraphWriter(
        store=store
    )

    try:
        store.verify_connectivity()

        total_entities = 0
        total_relationships = 0
        total_rejected = 0

        for chunk in selected_chunks:
            raw_graph = extracted[
                chunk.chunk_index
            ]

            processed = processor.process(
                document=document,
                chunk=chunk,
                extracted_graph=raw_graph,
            )

            print(
                f"\nChunk "
                f"{chunk.chunk_index}:"
            )

            print(
                f"  Entities: "
                f"{len(processed.entities)}"
            )

            print(
                f"  Accepted relationships: "
                f"{len(processed.relationships)}"
            )

            print(
                f"  Rejected relationships: "
                f"{len(processed.rejected_relationships)}"
            )

            for rejected in (
                processed
                .rejected_relationships
            ):
                print(
                    "    REJECTED: "
                    f"{rejected.relationship.source_name} "
                    f"{rejected.relationship.relationship_type.value} "
                    f"{rejected.relationship.target_name}"
                )

                print(
                    f"    Reason: "
                    f"{rejected.reason}"
                )

            writer.write_chunk_graph(
                document=document,
                chunk=chunk,
                graph=processed,
            )

            total_entities += len(
                processed.entities
            )

            total_relationships += len(
                processed.relationships
            )

            total_rejected += len(
                processed.rejected_relationships
            )

        print("\n" + "=" * 60)
        print("GRAPH INDEXING COMPLETE")
        print("=" * 60)

        print(
            "Processed entity occurrences:",
            total_entities,
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
                type(r) AS relationship_type,
                count(r) AS count
            ORDER BY relationship_type
            """
        )

        print("\nRelationship counts:")

        for row in relationship_counts:
            print(row)

    finally:
        store.close()


if __name__ == "__main__":
    main()