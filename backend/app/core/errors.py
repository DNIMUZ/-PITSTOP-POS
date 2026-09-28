"""Domain exceptions and consistent API error responses.

Every handled error is returned as:

    {"error": "CODE", "message": "human message", "request_id": "..."}

Stack traces are logged server-side and never exposed to clients.
"""
from __future__ import annotations


class AppError(Exception):
    status_code: int = 400
    code: str = "APP_ERROR"
    message: str = "Request failed."

    def __init__(self, message: str | None = None, detail: str | None = None) -> None:
        self.message = message or self.message
        self.detail = detail
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "Resource not found."


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"
    message = "Authentication required."


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "The request conflicts with the current state."


class InsufficientStockError(AppError):
    status_code = 409
    code = "INSUFFICIENT_STOCK"
    message = "Insufficient stock for one or more items."

    def __init__(self, message: str | None = None, detail: str | None = None) -> None:
        super().__init__(message)
        self.detail = detail


class TransactionFailedError(AppError):
    status_code = 409
    code = "TRANSACTION_FAILED"
    message = "Unable to complete transaction."

    def __init__(self, message: str | None = None, detail: str | None = None) -> None:
        super().__init__(message)
        self.detail = detail


class RefundFailedError(AppError):
    status_code = 409
    code = "REFUND_FAILED"
    message = "Unable to process refund."

    def __init__(self, message: str | None = None, detail: str | None = None) -> None:
        super().__init__(message)
        self.detail = detail
