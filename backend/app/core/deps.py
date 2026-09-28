"""FastAPI dependencies: DB session, current user, RBAC guards."""
from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.database.session import AsyncSessionLocal
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository


async def get_db() -> AsyncSession:
    """Yield a session that always commits on success and rolls back on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()


DbDep = Annotated[AsyncSession, Depends(get_db)]


def _extract_bearer(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise UnauthorizedError("Missing bearer token.")
    return auth.removeprefix("Bearer ").strip()


async def get_current_user(request: Request, db: DbDep) -> User:
    settings = get_settings()
    token = _extract_bearer(request)
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token.") from exc

    user_id = int(payload.get("sub", 0))
    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or deactivated.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


class RequireRoles:
    def __init__(self, *roles: UserRole) -> None:
        self.roles = set(roles)

    async def __call__(self, user: CurrentUser) -> User:
        if user.role not in self.roles:
            from app.core.errors import ForbiddenError

            raise ForbiddenError(
                detail=f"requires role(s): {', '.join(r.value for r in self.roles)}"
            )
        return user

    @property
    def dependency(self):
        return self


RequireCashier = RequireRoles(UserRole.CASHIER, UserRole.MANAGER, UserRole.ADMIN).dependency
RequireManager = RequireRoles(UserRole.MANAGER, UserRole.ADMIN).dependency
RequireAdmin = RequireRoles(UserRole.ADMIN).dependency
