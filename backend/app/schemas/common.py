"""Shared API schemas: pagination and request-id error envelope."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int


class ErrorOut(BaseModel):
    error: str
    message: str
    request_id: str = Field(default="-")


class MessageOut(BaseModel):
    message: str
