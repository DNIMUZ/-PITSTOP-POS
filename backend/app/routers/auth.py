"""Authentication routes."""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbDep
from app.core.rate_limit import limiter
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserOut
from app.services.auth_service import authenticate_user, issue_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive a JWT access token",
    responses={401: {"description": "Invalid credentials"}, 429: {"description": "Rate limited"}},
)
@limiter.limit(get_settings().LOGIN_RATE_LIMIT)
async def login(request: Request, body: LoginRequest, db: DbDep) -> TokenResponse:
    user = await authenticate_user(
        db, body.username, body.password, ip_address=_client_ip(request)
    )
    return TokenResponse(access_token=issue_token(user))


@router.get("/me", response_model=UserOut, summary="Current authenticated user")
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
