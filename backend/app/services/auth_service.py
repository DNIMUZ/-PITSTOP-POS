"""Authentication service: verify credentials and issue JWTs."""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import UnauthorizedError
from app.core.security import create_access_token, verify_password
from app.models.enums import AuditAction
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.audit_service import record_audit

logger = logging.getLogger(__name__)


async def authenticate_user(
    session: AsyncSession,
    username: str,
    password: str,
    ip_address: str | None,
    settings: Settings | None = None,
) -> User:
    settings = settings or get_settings()
    repo = UserRepository(session)
    user = await repo.get_by_username(username)
    if user is None or not verify_password(password, user.hashed_password):
        # Log a failed attempt WITHOUT the password.
        logger.warning("failed login attempt", extra={"username": username, "ip": ip_address})
        raise UnauthorizedError("Invalid username or password.")
    if not user.is_active:
        logger.warning("login blocked for inactive user", extra={"username": username})
        raise UnauthorizedError("Account is deactivated.")
    await record_audit(
        session,
        user_id=user.id,
        action=AuditAction.LOGIN,
        ip_address=ip_address,
    )
    logger.info(
        "user login",
        extra={"user_id": user.id, "username": user.username, "role": user.role, "ip": ip_address},
    )
    await session.commit()
    return user


def issue_token(user: User, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return create_access_token(str(user.id), user.role, settings)
