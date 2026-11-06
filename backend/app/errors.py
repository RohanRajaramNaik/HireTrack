"""Application errors rendered as {"detail": "...", "field": "..."}."""
from __future__ import annotations


class AppError(Exception):
    status_code = 400

    def __init__(self, detail: str, field: str | None = None, status_code: int | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.field = field
        if status_code is not None:
            self.status_code = status_code


class NotFound(AppError):
    status_code = 404


class Unauthorized(AppError):
    status_code = 401
