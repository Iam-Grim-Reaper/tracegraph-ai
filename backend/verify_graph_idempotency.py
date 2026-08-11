from pathlib import Path

from app.graph.postprocessor import (
    ProcessedChunkGraph,
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


SELECTED_INDEXES = {
    11,
    15,
    18,
    22,
    25,
}


def get_counts(
    store: Neo4jGraphStore,
) -> dict:
    documents = store.query(
        """
        MATCH (d:Document)
        RETURN count(d) AS count
        """
    )[0]["count"]

    chunks = store.query(
        """
        MATCH (c:Chunk)
        RETURN count(c) AS count
        """
    )[0]["count"]

    entities = store.query(
        """
        MATCH (e:Entity)
        RETURN count(e) AS count
        """
    )[0]["count"]

    relationships = store.query(
        """
        MATCH ()-[r]->()
        RETURN count(r) AS count
        """
    )[0]["count"]

    return {
        "documents": documents,
        "chunks": chunks,
        "entities": entities,
        "relationships": relationships,
    }


def main():
    pdf_path = Path(
        "../data/sample.pdf"
    )

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

    selected_chunks = [
        chunk
        for chunk in chunks
        if chunk.chunk_index
        in SELECTED_INDEXES
    ]

    store = Neo4jGraphStore()

    writer = Neo4jGraphWriter(
        store=store
    )

    try:
        store.verify_connectivity()

        before = get_counts(
            store
        )

        print("=" * 70)
        print("IDEMPOTENCY CHECK")
        print("=" * 70)

        print("\nBefore identical write:")
        print(before)

        # We only need to rewrite the stable
        # Document and Chunk identities.
        #
        # No Gemini extraction is required.
        empty_graph = ProcessedChunkGraph(
            entities=[],
            relationships=[],
            rejected_relationships=[],
        )

        for chunk in selected_chunks:
            writer.write_chunk_graph(
                document=document,
                chunk=chunk,
                graph=empty_graph,
            )

        after = get_counts(
            store
        )

        print("\nAfter identical write:")
        print(after)

        document_stable = (
            before["documents"]
            == after["documents"]
        )

        chunk_stable = (
            before["chunks"]
            == after["chunks"]
        )

        entity_stable = (
            before["entities"]
            == after["entities"]
        )

        relationship_stable = (
            before["relationships"]
            == after["relationships"]
        )

        print(
            "\nDocument count stable:",
            document_stable,
        )

        print(
            "Chunk count stable:",
            chunk_stable,
        )

        print(
            "Entity count stable:",
            entity_stable,
        )

        print(
            "Relationship count stable:",
            relationship_stable,
        )

        all_stable = all(
            [
                document_stable,
                chunk_stable,
                entity_stable,
                relationship_stable,
            ]
        )

        print(
            "\nIDEMPOTENT:",
            all_stable,
        )

        if not all_stable:
            raise RuntimeError(
                "Graph storage is not "
                "idempotent."
            )

    finally:
        store.close()


if __name__ == "__main__":
    main()