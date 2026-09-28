"""User management (admin only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import DbDep, RequireAdmin
from app.core.errors import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.enums import AuditAction
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.audit_service import record_audit

router = APIRouter(prefix="/api/v1/users", tags=["users"], dependencies=[Depends(RequireAdmin)])


@router.get("", response_model=list[UserOut], summary="List users (admin)")
async def list_users(
    db: DbDep, search: str | None = Query(default=None, max_length=100)
) -> list[UserOut]:
    users = await UserRepository(db).get_all(search=search)
    return [UserOut.model_validate(u) for u in users]


@router.post("", response_model=UserOut, status_code=201, summary="Create user (admin)")
async def create_user(body: UserCreate, db: DbDep, admin: User = Depends(RequireAdmin)) -> UserOut:
    repo = UserRepository(db)
    if await repo.get_by_username(body.username):
        raise ConflictError(detail=f"username '{body.username}' already exists")
    user = await repo.create(
        User(
            username=body.username,
            full_name=body.full_name,
            email=body.email,
            hashed_password=hash_password(body.password),
            role=body.role.value,
        )
    )
    await record_audit(
        db,
        user_id=admin.id,
        action=AuditAction.USER_CREATED.value,
        entity_type="user",
        entity_id=user.id,
        details={"username": user.username, "role": user.role},
    )
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut, summary="Update user (admin)")
async def update_user(
    user_id: int, body: UserUpdate, db: DbDep, admin: User = Depends(RequireAdmin)
) -> UserOut:
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise NotFoundError(detail=f"user id={user_id} not found")

    changes = body.model_dump(exclude_unset=True)
    if "password" in changes:
        changes["hashed_password"] = hash_password(changes.pop("password"))
    if "role" in changes:
        changes["role"] = changes["role"].value
    for field, value in changes.items():
        setattr(user, field, value)

    await record_audit(
        db,
        user_id=admin.id,
        action=AuditAction.USER_UPDATED.value,
        entity_type="user",
        entity_id=user.id,
        details={k: v for k, v in changes.items() if k != "hashed_password"},
    )
    return UserOut.model_validate(user)
