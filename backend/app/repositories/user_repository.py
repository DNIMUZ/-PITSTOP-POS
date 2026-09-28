"""User repository."""
from __future__ import annotations

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    async def get_by_username(self, username: str) -> User | None:
        return await self.session.scalar(select(User).where(User.username == username))

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.scalar(select(User).where(User.id == user_id))

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_all(self, search: str | None = None) -> list[User]:
        stmt = select(User).order_by(User.id)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(User.username.ilike(like) | User.full_name.ilike(like))
        return list((await self.session.execute(stmt)).scalars().all())
