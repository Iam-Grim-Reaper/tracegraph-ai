import tempfile
import traceback
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
    status,
)
from google.genai.errors import (
    ClientError,
)

from app.api.document_models import (
    DocumentListResponse,
    DocumentSummary,
    DocumentUploadResponse,
)
from app.services.document_catalog_service import (
    DocumentCatalogService,
)
from app.services.document_indexing_service import (
    DocumentIndexingService,
)


router = APIRouter(
    prefix="/api/documents",
    tags=["Documents"],
)


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".markdown",
}


# Development safeguard.
#
# This can move into settings when
# deployment configuration is finalized.
MAX_UPLOAD_BYTES = (
    25 * 1024 * 1024
)


def _validate_filename(
    filename: str | None,
) -> tuple[str, str]:
    if not filename:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=(
                "Uploaded file must "
                "have a filename."
            ),
        )

    # -----------------------------------------
    # Remove any client-supplied path.
    # -----------------------------------------

    safe_name = (
        Path(
            filename
        ).name
    )

    suffix = (
        Path(
            safe_name
        )
        .suffix
        .lower()
    )

    if (
        suffix
        not in SUPPORTED_EXTENSIONS
    ):
        supported = ", ".join(
            sorted(
                SUPPORTED_EXTENSIONS
            )
        )

        raise HTTPException(
            status_code=(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            ),

            detail=(
                "Unsupported document type. "
                f"Supported extensions: "
                f"{supported}"
            ),
        )

    return (
        safe_name,
        suffix,
    )


def _save_upload(
    upload: UploadFile,
    destination: Path,
) -> int:
    """
    Stream the uploaded file to temporary
    storage while enforcing the development
    upload-size limit.

    Returns the total bytes written.
    """

    total_bytes = 0

    chunk_size = (
        1024 * 1024
    )

    with destination.open(
        "wb"
    ) as output:
        while True:
            data = (
                upload.file.read(
                    chunk_size
                )
            )

            if not data:
                break

            total_bytes += (
                len(
                    data
                )
            )

            if (
                total_bytes
                > MAX_UPLOAD_BYTES
            ):
                raise HTTPException(
                    status_code=(
                        status
                        .HTTP_413_CONTENT_TOO_LARGE
                    ),

                    detail=(
                        "Uploaded document exceeds "
                        "the 25 MB development "
                        "limit."
                    ),
                )

            output.write(
                data
            )

    if total_bytes == 0:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=(
                "Uploaded file is empty."
            ),
        )

    return total_bytes


# =========================================================
# POST /api/documents
# =========================================================


@router.post(
    "",
    response_model=(
        DocumentUploadResponse
    ),
    status_code=(
        status.HTTP_201_CREATED
    ),
)
def upload_document(
    file: Annotated[
        UploadFile,

        File(
            description=(
                "PDF, TXT, or Markdown "
                "document to index"
            )
        ),
    ],
) -> DocumentUploadResponse:
    safe_name, _ = (
        _validate_filename(
            file.filename
        )
    )

    try:
        # -----------------------------------------
        # Every request receives an isolated
        # temporary directory.
        #
        # It is removed automatically after
        # indexing completes.
        # -----------------------------------------

        with tempfile.TemporaryDirectory(
            prefix=(
                "tracegraph-upload-"
            )
        ) as temp_directory:
            temp_path = (
                Path(
                    temp_directory
                )
                / safe_name
            )

            _save_upload(
                upload=file,
                destination=temp_path,
            )

            service = (
                DocumentIndexingService()
            )

            result = (
                service.index_file(
                    temp_path
                )
            )

        return (
            DocumentUploadResponse(
                document_id=(
                    result.document_id
                ),

                filename=(
                    result.filename
                ),

                file_type=(
                    result.file_type
                ),

                title=(
                    result.title
                ),

                # =================================
                # Ontology metadata
                # =================================

                ontology_profile=(
                    result
                    .ontology_profile
                ),

                ontology_version=(
                    result
                    .ontology_version
                ),

                ontology_profiles=(
                    result
                    .ontology_profiles
                ),

                ontology_confidence=(
                    result
                    .ontology_confidence
                ),

                ontology_method=(
                    result
                    .ontology_method
                ),

                ontology_reason=(
                    result
                    .ontology_reason
                ),

                ontology_scores=(
                    result
                    .ontology_scores
                ),

                # =================================
                # Graph/index statistics
                # =================================

                chunk_count=(
                    result.chunk_count
                ),

                entity_count=(
                    result
                    .graph_entity_count
                ),

                graph_relationship_count=(
                    result
                    .graph_relationship_count
                ),

                qdrant_indexed_chunks=(
                    result
                    .qdrant_indexed_chunks
                ),

                graph_rejected_relationship_count=(
                    result
                    .graph_rejected_relationship_count
                ),

                graph_cached_chunks=(
                    result
                    .graph_cached_chunks
                ),

                graph_extracted_chunks=(
                    result
                    .graph_extracted_chunks
                ),
            )
        )

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                exc
            ),
        ) from exc

    except ClientError as exc:
        if getattr(
            exc,
            "code",
            None,
        ) == 429:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_503_SERVICE_UNAVAILABLE
                ),

                detail=(
                    "The AI provider is "
                    "temporarily rate limited "
                    "during document indexing."
                ),
            ) from exc

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),

            detail=(
                "The AI provider returned "
                "an error during document "
                "indexing."
            ),
        ) from exc

    except Exception as exc:
        traceback.print_exception(
            type(exc),
            exc,
            exc.__traceback__,
        )

        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),

            detail=(
                "TraceGraph could not "
                "index the document."
            ),
        ) from exc


# =========================================================
# GET /api/documents
# =========================================================


@router.get(
    "",
    response_model=(
        DocumentListResponse
    ),
)
def list_documents(
) -> DocumentListResponse:
    service = (
        DocumentCatalogService()
    )

    documents = (
        service.list_documents()
    )

    return (
        DocumentListResponse(
            documents=(
                documents
            ),

            total=len(
                documents
            ),
        )
    )


# =========================================================
# GET /api/documents/{document_id}
# =========================================================


@router.get(
    "/{document_id}",
    response_model=(
        DocumentSummary
    ),
)
def get_document(
    document_id: str,
) -> DocumentSummary:
    service = (
        DocumentCatalogService()
    )

    document = (
        service.get_document(
            document_id
        )
    )

    if document is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),

            detail=(
                "Document not found."
            ),
        )

    return document
