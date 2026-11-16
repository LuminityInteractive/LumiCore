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

class APIResponce(BaseModel):
    data: Any = None
    error: ErrorDetail | None = None


async def http_exception_handler(
    request: Any,
    exception: Any,
) -> JSONResponse:
    code = HTTP_ERROR_CODES.get(exception.status_code, "HTTP_ERROR")
    responce = APIResponce(
        error=ErrorDetail(
            code=code,
            message=str(exception.detail),
        )
    )

    return JSONResponse(
        status_code=exception.status_code,
        content=responce.model_dump(),
    )

async def validation_exception_handler(
    _request: Any,
    _exception: Any,
) -> JSONResponse:
    responce = APIResponce(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="The request contains invalid data.",
        )
    )
    return JSONResponse(
        status_code=422,
        content=responce.model_dump(),
    )
