from collections.abc import Callable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import random
import time
import logging
from typing import TypeVar

import httpx
from google import genai
from google.genai import errors, types

from app.core.config import settings
from app.core.observability import log_event


T = TypeVar("T")
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
logger = logging.getLogger(__name__)


def create_gemini_client(timeout_seconds: float) -> genai.Client:
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(
            timeout=int(timeout_seconds * 1000),
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


def call_with_provider_resilience(
    operation: Callable[[], T],
    *,
    sleep: Callable[[float], None] = time.sleep,
    random_value: Callable[[], float] = random.random,
) -> T:
    for attempt in range(1, settings.provider_max_attempts + 1):
        try:
            return operation()
        except Exception as exc:
            if (
                attempt >= settings.provider_max_attempts
                or not _is_retryable(exc)
            ):
                raise
            delay = _retry_delay(exc, attempt, random_value())
            log_event(
                logger,
                logging.WARNING,
                "provider_retry",
                operation="provider_call",
                provider="gemini",
                attempt=attempt + 1,
                status="retrying",
                status_code=getattr(exc, "code", None),
                error_type=type(exc).__name__,
                delay_ms=round(delay * 1000, 3),
            )
            sleep(delay)
    raise AssertionError("provider attempt loop did not terminate")


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, errors.APIError):
        return exc.code in RETRYABLE_STATUS_CODES
    return isinstance(exc, httpx.TransportError)


def _retry_delay(
    exc: Exception,
    attempt: int,
    jitter_value: float,
) -> float:
    retry_after = _retry_after_seconds(exc)
    if retry_after is not None:
        return min(retry_after, settings.provider_retry_max_delay_seconds)
    exponential = settings.provider_retry_base_delay_seconds * (3 ** (attempt - 1))
    jitter = settings.provider_retry_base_delay_seconds * max(
        0.0,
        min(jitter_value, 1.0),
    )
    return min(exponential + jitter, settings.provider_retry_max_delay_seconds)


def _retry_after_seconds(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    value = headers.get("retry-after")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None
