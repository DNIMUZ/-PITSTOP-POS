"""Database layer: base declarative class, session, naming conventions."""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase

from app.database.session import make_metadata


class Base(DeclarativeBase):
    metadata = make_metadata()
