"""Administrator-only, idempotent indexing of TraceGraph's fixed demo corpus.

This is a CLI, not a public API route. Running it requires trusted Gemini,
Qdrant and Neo4j credentials in its environment. No document contents are
printed. The three approved files must match the SHA256-verified manifest.

Examples (from backend/):
  uv run python tools/seed_public_demo.py --mode preflight
  uv run python tools/seed_public_demo.py --mode index
  uv run python tools/seed_public_demo.py --mode verify

Do not use development/test credentials for the production index.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from app.demo.public_corpus import PUBLIC_DEMO_DOCUMENTS, validate_demo_file


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def verified_paths(root: Path) -> list[tuple[object, Path]]:
    """Check every approved source BEFORE performing any external writes."""
    return [(entry, validate_demo_file(entry, root)) for entry in PUBLIC_DEMO_DOCUMENTS]


def preflight(root: Path) -> list[dict]:
    from app.ingestion.service import IngestionService

    service = IngestionService()
    summary = []
    for entry, path in verified_paths(root):
        ingestion = service.ingest(path)
        chunks = ingestion.chunks
        if str(ingestion.document.id) != entry.document_id:
            raise RuntimeError(f"Unexpected parsed document identity: {entry.filename}")
        if not chunks:
            raise RuntimeError(f"Document contains no usable text: {entry.filename}")
        summary.append({
            "file": entry.filename,
            "document_id": entry.document_id,
            "file_size_bytes": path.stat().st_size,
            "chunks": len(chunks),
            "text_characters": sum(len(chunk.text) for chunk in chunks),
            "status": "preflight_passed",
        })
    return summary


def verify(indexed_expected=None) -> list[dict]:
    from app.services.document_catalog_service import DocumentCatalogService

    docs = list(indexed_expected or PUBLIC_DEMO_DOCUMENTS)
    by_id = DocumentCatalogService().get_ready_filenames(
        {item.document_id for item in docs}
    )
    rows = [
        {
            "file": item.filename,
            "document_id": item.document_id,
            "status": (
                "ready"
                if by_id.get(item.document_id) == item.filename
                else "not_ready"
            ),
        }
        for item in docs
    ]
    if any(row["status"] != "ready" for row in rows):
        raise RuntimeError(
            "Public demo verification failed: one or more approved "
            "documents are not marked ready in the catalog."
        )
    return rows


def index(root: Path) -> list[dict]:
    # Verify *every* source before creating clients or writing any records.
    sources = verified_paths(root)
    from app.services.document_indexing_service import DocumentIndexingService

    service = DocumentIndexingService()
    summary: list[dict] = []
    for entry, path in sources:
        started = perf_counter()
        print(f"Indexing {entry.filename} (approved document)", flush=True)
        result = service.index_file(path)
        if str(result.document_id) != entry.document_id:
            raise RuntimeError(f"Index result does not match manifest: {entry.filename}")
        summary.append({
            "file": entry.filename,
            "document_id": entry.document_id,
            "status": "indexed_or_already_ready",
            "chunks": result.chunk_count,
            "qdrant_indexed_chunks": result.qdrant_indexed_chunks,
            "graph_entities": result.graph_entity_count,
            "graph_relationships": result.graph_relationship_count,
            "elapsed_seconds": round(perf_counter() - started, 2),
        })
    # No success claim until all three are visible as ready in the catalog.
    verify()
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "index", "verify"), default="preflight")
    parser.add_argument("--root", type=Path, default=repository_root())
    args = parser.parse_args()
    root = args.root.resolve()

    if args.mode == "preflight":
        summary = preflight(root)
    elif args.mode == "index":
        summary = index(root)
    else:
        summary = verify()

    print(json.dumps({
        "operation": args.mode,
        "approved_document_count": len(PUBLIC_DEMO_DOCUMENTS),
        "results": summary,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
