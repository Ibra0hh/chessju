from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.common.request_context import REQUEST_ID_HEADER, get_request_id


def _status_code_to_error_code(status_code: int) -> str:
    if status_code == status.HTTP_400_BAD_REQUEST:
        return "request.bad_request"
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return "auth.unauthorized"
    if status_code == status.HTTP_403_FORBIDDEN:
        return "auth.forbidden"
    if status_code == status.HTTP_404_NOT_FOUND:
        return "resource.not_found"
    if status_code == status.HTTP_409_CONFLICT:
        return "resource.conflict"
    if status_code == status.HTTP_413_CONTENT_TOO_LARGE:
        return "request.too_large"
    if status_code == status.HTTP_422_UNPROCESSABLE_CONTENT:
        return "validation.invalid_input"
    if status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return "rate_limit.exceeded"
    if status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        return "service.unavailable"
    if status_code >= 500:
        return "server.internal_error"
    return "request.error"


def _default_message(status_code: int) -> str:
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return "Authentication required"
    if status_code == status.HTTP_403_FORBIDDEN:
        return "Forbidden"
    if status_code == status.HTTP_404_NOT_FOUND:
        return "Resource not found"
    if status_code == status.HTTP_409_CONFLICT:
        return "Resource conflict"
    if status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return "Rate limit exceeded"
    if status_code >= 500:
        return "Internal server error"
    return "Request failed"


def _safe_http_detail(detail: Any, status_code: int) -> tuple[str, dict[str, Any]]:
    if isinstance(detail, str):
        if status_code >= 500:
            return _default_message(status_code), {}
        return detail, {}
    if isinstance(detail, dict):
        message = detail.get("message")
        safe_message = str(message) if message else _default_message(status_code)
        return safe_message, {"detail": detail}
    return _default_message(status_code), {}


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = get_request_id(request)
    response = JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "request_id": request_id,
            }
        },
        headers=headers,
    )
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    message, details = _safe_http_detail(exc.detail, exc.status_code)
    return _error_response(
        request,
        status_code=exc.status_code,
        code=_status_code_to_error_code(exc.status_code),
        message=message,
        details=details,
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    validation_errors = [
        {
            "loc": [str(item) for item in error.get("loc", [])],
            "message": str(error.get("msg", "Invalid input")),
            "type": str(error.get("type", "validation_error")),
        }
        for error in exc.errors()
    ]
    return _error_response(
        request,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="validation.invalid_input",
        message="Invalid request input",
        details={"errors": validation_errors},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    _ = exc
    return _error_response(
        request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="server.internal_error",
        message="Internal server error",
    )
