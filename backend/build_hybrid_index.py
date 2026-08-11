from qdrant_client import QdrantClient, models

from app.core.config import settings
from app.retrieval.hybrid_store import HybridStore


def main():
    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )

    source_collection = (
        settings.qdrant_contextual_collection
    )

    hybrid_store = HybridStore()
    hybrid_store.ensure_collection()

    print(
        f"Reading contextual points from "
        f"{source_collection}..."
    )

    points, _ = client.scroll(
        collection_name=source_collection,
        limit=1000,
        with_payload=True,
        with_vectors=True,
    )

    if not points:
        raise RuntimeError(
            "No contextual points found"
        )

    print(
        f"Loaded {len(points)} contextual points."
    )

    texts = []

    for point in points:
        payload = point.payload or {}

        contextual_text = payload.get(
            "contextual_text"
        )

        original_text = payload.get(
            "text",
            "",
        )

        texts.append(
            contextual_text or original_text
        )

    average_document_length = (
        sum(
            len(text.split())
            for text in texts
        )
        / len(texts)
    )

    print(
        "Average BM25 document length:",
        round(average_document_length, 2),
    )

    hybrid_points = []

    for point, bm25_text in zip(
        points,
        texts,
        strict=True,
    ):
        dense_vector = point.vector

        if isinstance(
            dense_vector,
            dict,
        ):
            dense_vector = next(
                iter(
                    dense_vector.values()
                )
            )

        if dense_vector is None:
            raise RuntimeError(
                f"Point {point.id} has no dense vector"
            )

        hybrid_points.append(
            models.PointStruct(
                id=point.id,
                vector={
                    HybridStore.DENSE_VECTOR_NAME:
                        dense_vector,

                    HybridStore.BM25_VECTOR_NAME:
                        models.Document(
                            text=bm25_text,
                            model="Qdrant/bm25",
                            options={
                                "avg_len":
                                    average_document_length
                            },
                        ),
                },
                payload=point.payload,
            )
        )

    print(
        f"Uploading {len(hybrid_points)} "
        "hybrid points..."
    )

    client.upsert(
        collection_name=(
            hybrid_store.collection_name
        ),
        points=hybrid_points,
        wait=True,
    )

    info = client.get_collection(
        hybrid_store.collection_name
    )

    print(
        "\nHybrid collection:",
        hybrid_store.collection_name,
    )

    print(
        "Points:",
        info.points_count,
    )


if __name__ == "__main__":
    main()