import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings

logger = logging.getLogger("smart_postal.limiter")


def get_client_ip(request: Request) -> str:
    """
    Extract client IP for rate limiting.
    Checks X-Forwarded-For first (for reverse proxy/testing support), falling back to remote client host.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client and client.host else "127.0.0.1"


# Initialize central Limiter instance
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[settings.RATE_LIMIT_GENERAL] if settings.RATE_LIMIT_GENERAL else [],
    enabled=settings.RATE_LIMIT_ENABLED,
    storage_uri=settings.RATE_LIMIT_STORAGE_URL,
)


def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Standardized application JSON envelope for HTTP 429 Too Many Requests.
    Adheres to OWASP API4:2023 without leaking internal credentials.
    """
    retry_after = getattr(exc, "retry_after", 60)
    logger.warning(
        f"Rate limit exceeded on {request.method} {request.url.path} from IP {get_client_ip(request)}: {exc.detail}"
    )

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={"Retry-After": str(retry_after)},
        content={
            "success": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": f"Too many requests. {exc.detail}. Please retry in {retry_after} seconds.",
                "retry_after": retry_after
            }
        }
    )
