from pathlib import Path

from app.graph.entity_resolver import (
    GlobalEntityResolver,
)
from app.graph.extraction_cache import (
    GraphExtractionCache,
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


BATCH_SIZE = 5


def main():
    pdf_path = Path(
        "../data/sample.pdf"
    )

    print("=" * 70)
    print("TRACEGRAPH FULL GRAPH INDEX")
    print("=" * 70)

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

    print(
        f"\nDocument ID: "
        f"{document.id}"
    )

    print(
        f"Total chunks: "
        f"{len(chunks)}"
    )

    cache = GraphExtractionCache()

    extractor = GraphExtractor()

    extracted_graphs = {}

    cached_count = 0

    missing_chunks = []

    # -----------------------------------
    # 1. Load everything already cached.
    # -----------------------------------
    for chunk in chunks:
        cached = cache.get(
            chunk
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
        f"Cached extractions: "
        f"{cached_count}"
    )

    print(
        f"Chunks requiring Gemini: "
        f"{len(missing_chunks)}"
    )

    # -----------------------------------
    # 2. Extract missing chunks in
    #    controlled batches.
    # -----------------------------------
    for start in range(
        0,
        len(missing_chunks),
        BATCH_SIZE,
    ):
        batch = missing_chunks[
            start:start + BATCH_SIZE
        ]

        batch_number = (
            start // BATCH_SIZE
        ) + 1

        total_batches = (
            len(missing_chunks)
            + BATCH_SIZE
            - 1
        ) // BATCH_SIZE

        print(
            f"\nExtracting missing batch "
            f"{batch_number}/"
            f"{total_batches} "
            f"({len(batch)} chunks)..."
        )

        batch_results = (
            extractor.extract_chunks(
                document=document,
                chunks=batch,
                batch_size=len(batch),
            )
        )

        for chunk in batch:
            graph = batch_results[
                chunk.chunk_index
            ]

            extracted_graphs[
                chunk.chunk_index
            ] = graph

            # Save immediately.
            #
            # If a later Gemini batch fails,
            # this successful batch survives.
            cache.set(
                chunk=chunk,
                graph=graph,
            )

    if len(extracted_graphs) != len(
        chunks
    ):
        raise RuntimeError(
            "Graph extraction incomplete: "
            f"{len(extracted_graphs)}/"
            f"{len(chunks)} chunks available"
        )

    print(
        "\nAll chunk graph extractions "
        "are available."
    )

    # -----------------------------------
    # 3. Post-process + resolve + write.
    # -----------------------------------
    processor = GraphPostProcessor()

    store = Neo4jGraphStore()

    resolver = GlobalEntityResolver(
        store=store
    )

    writer = Neo4jGraphWriter(
        store=store
    )

    total_entities = 0
    total_relationships = 0
    total_rejected = 0

    try:
        store.verify_connectivity()

        for number, chunk in enumerate(
            chunks,
            start=1,
        ):
            raw_graph = extracted_graphs[
                chunk.chunk_index
            ]

            processed = processor.process(
                document=document,
                chunk=chunk,
                extracted_graph=raw_graph,
            )

            resolved = resolver.resolve(
                processed
            )

            writer.write_chunk_graph(
                document=document,
                chunk=chunk,
                graph=resolved,
            )

            total_entities += len(
                resolved.entities
            )

            total_relationships += len(
                resolved.relationships
            )

            total_rejected += len(
                resolved.rejected_relationships
            )

            print(
                f"Chunk "
                f"{number}/{len(chunks)} "
                f"(index "
                f"{chunk.chunk_index})"
            )

            print(
                f"  Entities: "
                f"{len(resolved.entities)}"
            )

            print(
                f"  Relationships: "
                f"{len(resolved.relationships)}"
            )

            print(
                f"  Rejected: "
                f"{len(resolved.rejected_relationships)}"
            )

            for rejected in (
                resolved.rejected_relationships
            ):
                relation = (
                    rejected.relationship
                )

                print(
                    "    REJECTED: "
                    f"{relation.source_name} "
                    f"{relation.relationship_type.value} "
                    f"{relation.target_name}"
                )

                print(
                    "    Reason: "
                    f"{rejected.reason}"
                )

        print("\n" + "=" * 70)
        print("FULL GRAPH INDEX COMPLETE")
        print("=" * 70)

        print(
            "Entity occurrences processed:",
            total_entities,
        )

        print(
            "Accepted semantic relationships:",
            total_relationships,
        )

        print(
            "Rejected relationships:",
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
            WITH
                documents,
                chunks,
                count(e) AS entities

            MATCH ()-[r]->()

            RETURN
                documents,
                chunks,
                entities,
                count(r) AS relationships
            """
        )

        print(
            "\nNeo4j graph counts:"
        )

        print(
            counts
        )

        semantic_counts = store.query(
            """
            MATCH ()-[r]->()

            WHERE NOT type(r) IN [
                'MENTIONS',
                'CONTAINS'
            ]

            RETURN
                type(r)
                    AS relationship_type,
                count(r)
                    AS count

            ORDER BY
                count DESC,
                relationship_type
            """
        )

        print(
            "\nSemantic relationship types:"
        )

        for row in semantic_counts:
            print(
                row
            )

    finally:
        store.close()


if __name__ == "__main__":
    main()