from app.graph.retriever import (
    GraphRetriever,
)
from app.graph.store import (
    Neo4jGraphStore,
)


def print_neighbors(
    retriever: GraphRetriever,
    entity_id: str,
):
    neighbors = retriever.get_neighbors(
        entity_id=entity_id
    )

    print("\n1-HOP RELATIONSHIPS")
    print("=" * 80)

    print(
        f"Neighbor rows returned: "
        f"{len(neighbors)}"
    )

    if not neighbors:
        print(
            "No semantic relationships found."
        )
        return

    for row in neighbors:
        print()

        print(
            f"{row['source_name']} "
            f"-[{row['relationship_type']}]-> "
            f"{row['target_name']}"
        )

        print(
            f"Confidence: "
            f"{row['confidence']}"
        )

        print(
            f"Page: "
            f"{row['page_number']}"
        )

        print(
            f"Chunk ID: "
            f"{row['source_chunk_id']}"
        )

        print(
            f"Evidence: "
            f"{row['evidence_text']}"
        )

        source_text = row.get(
            "source_text"
        )

        if source_text:
            print(
                "Source text: "
                f"{source_text[:300]}..."
            )

        print("-" * 80)


def print_paths(
    retriever: GraphRetriever,
    entity_id: str,
):
    paths = retriever.get_two_hop_paths(
        entity_id=entity_id
    )

    print("\n1-2 HOP PATHS")
    print("=" * 80)

    print(
        f"Path rows returned: "
        f"{len(paths)}"
    )

    if not paths:
        print(
            "No graph paths found."
        )
        return

    for path_number, path in enumerate(
        paths,
        start=1,
    ):
        print()

        print(
            f"PATH {path_number}"
        )

        print(
            f"Hops: "
            f"{path['hops']}"
        )

        relationship_steps = (
            path["relationship_steps"]
        )

        for step in relationship_steps:
            print(
                f"{step['source_name']} "
                f"-[{step['relationship_type']}]-> "
                f"{step['target_name']}"
            )

            print(
                f"Confidence: "
                f"{step['confidence']}"
            )

            print(
                f"Page: "
                f"{step['page_number']}"
            )

            print(
                f"Chunk ID: "
                f"{step['source_chunk_id']}"
            )

            print(
                f"Evidence: "
                f"{step['evidence_text']}"
            )

        print("-" * 80)


def main():
    store = Neo4jGraphStore()

    try:
        store.verify_connectivity()

        retriever = GraphRetriever(
            store=store
        )

        test_entities = [
            "Grad-CAM",
            "ConvNeXt-Small",
            "LC25000",
        ]

        for name in test_entities:
            print("\n")
            print("#" * 80)

            print(
                f"ENTITY SEARCH: {name}"
            )

            print("#" * 80)

            matches = (
                retriever.find_entities(
                    name=name
                )
            )

            print(
                f"Entity matches returned: "
                f"{len(matches)}"
            )

            if not matches:
                print(
                    "No matching entity found."
                )
                continue

            for index, match in enumerate(
                matches,
                start=1,
            ):
                print()

                print(
                    f"MATCH {index}: "
                    f"{match.name} "
                    f"[{match.entity_type}]"
                )

                print(
                    f"Entity ID: "
                    f"{match.entity_id}"
                )

                print(
                    f"Normalized name: "
                    f"{match.normalized_name}"
                )

                print(
                    f"Aliases: "
                    f"{match.aliases}"
                )

                print_neighbors(
                    retriever=retriever,
                    entity_id=(
                        match.entity_id
                    ),
                )

                print_paths(
                    retriever=retriever,
                    entity_id=(
                        match.entity_id
                    ),
                )

    finally:
        store.close()


if __name__ == "__main__":
    main()