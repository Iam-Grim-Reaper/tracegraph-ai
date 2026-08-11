from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from google.genai.errors import (
    ClientError,
)

from app.api.chat_models import (
    ChatRequest,
    ChatResponse,
)
from app.services.tracegraph_service import (
    get_tracegraph_service,
)


router = APIRouter(
    prefix="/api",
    tags=["TraceGraph"],
)


@router.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
) -> ChatResponse:
    try:
        service = (
            get_tracegraph_service()
        )

        result = service.ask(
            request.question
        )

        return ChatResponse(
            **result
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except ClientError as exc:
        # Gemini quota / rate-limit failure.
        if exc.code == 429:
            raise HTTPException(
                status_code=(
                    status.HTTP_503_SERVICE_UNAVAILABLE
                ),
                detail=(
                    "The AI provider is "
                    "temporarily rate limited. "
                    "Please try again shortly."
                ),
            ) from exc

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=(
                "The AI provider returned "
                "an error."
            ),
        ) from exc

    except Exception as exc:
        print(
            "TraceGraph chat error:",
            repr(exc),
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "TraceGraph could not process "
                "the request."
            ),
        ) from exc