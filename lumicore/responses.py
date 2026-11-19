from typing import Any
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

HTTP_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMIT_EXCEEDED",
    500: "INTERNAL_SERVER_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


class ErrorDetail(BaseModel):
    code: str
    message: str

class APIResponse(BaseModel):
    data: Any = None
    error: ErrorDetail | None = None


async def http_exception_handler(
    request: Any,
    exception: Any,
) -> JSONResponse:
    detail = exception.detail

    if isinstance(detail, dict):
        code = detail.get(
            "code",
            HTTP_ERROR_CODES.get(exception.status_code, "HTTP_ERROR"),
        )
        message = detail.get(
            "message",
            "The request could not be completed.",
        )
    else:
        code = HTTP_ERROR_CODES.get(
            exception.status_code,
            "HTTP_ERROR",
        )
        message = str(detail)

    response = APIResponse(
        error=ErrorDetail(
            code=code,
            message=message,
        )
    )

    return JSONResponse(
        status_code=exception.status_code,
        content=response.model_dump(),
    )

async def validation_exception_handler(
    _request: Any,
    _exception: Any,
) -> JSONResponse:
    response = APIResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="The request contains invalid data.",
        )
    )
    return JSONResponse(
        status_code=422,
        content=response.model_dump(),
    )
async def unexpected_exception_handler(
    _request: Any,
    _exception: Any,
) -> JSONResponse:
    response = APIResponse(
        error=ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred.",
        )
    )
    return JSONResponse(
        status_code=500,
        content=response.model_dump(),
    )
