"""Custom exception handlers for FastAPI.

Registers global exception handlers that convert all errors into
a predictable ErrorResponse JSON structure. This ensures the React
frontend never receives raw stack traces or inconsistent error formats.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.schemas.common import ErrorResponse


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI application.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Handle Pydantic validation errors from malformed request payloads."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error="validation_error",
                detail=str(exc.errors()),
                status_code=422,
            ).model_dump(),
        )

    @app.exception_handler(404)
    async def not_found_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle 404 Not Found errors."""
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                error="not_found",
                detail="The requested resource was not found.",
                status_code=404,
            ).model_dump(),
        )

    @app.exception_handler(500)
    async def internal_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected internal server errors."""
        # TODO: Log the full traceback via structlog before returning a sanitized response
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="internal_error",
                detail="An unexpected error occurred. Please try again later.",
                status_code=500,
            ).model_dump(),
        )
