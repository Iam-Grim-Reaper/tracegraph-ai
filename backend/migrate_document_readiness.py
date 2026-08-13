"""Bounded, idempotent migration for catalog-confirmed legacy documents."""

import argparse

from app.services.document_readiness_service import DocumentReadinessService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    service = DocumentReadinessService()
    try:
        result = service.migrate_legacy_ready_documents(limit=args.limit)
    finally:
        service.close()
    print(f"documents_migrated={result.documents_migrated}")
    print(f"points_updated={result.points_updated}")
    print(f"documents_skipped={result.documents_skipped}")
    print(f"errors={result.errors}")


if __name__ == "__main__":
    main()
