"""Product categories."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import DbDep, RequireCashier, RequireManager
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.services import product_service

router = APIRouter(
    prefix="/api/v1/categories",
    tags=["categories"],
    dependencies=[Depends(RequireCashier)],
)


@router.get("", response_model=list[CategoryOut], summary="List categories")
async def list_categories(db: DbDep) -> list[CategoryOut]:
    cats = await product_service.list_categories(db)
    return [CategoryOut.model_validate(c) for c in cats]


@router.post(
    "",
    response_model=CategoryOut,
    status_code=201,
    summary="Create category",
    dependencies=[Depends(RequireManager)],
)
async def create_category(
    body: CategoryCreate, db: DbDep, actor: User = Depends(RequireManager)
) -> CategoryOut:
    category = await product_service.create_category(db, body.name, body.description, actor)
    return CategoryOut.model_validate(category)


@router.patch(
    "/{category_id}",
    response_model=CategoryOut,
    summary="Update category",
    dependencies=[Depends(RequireManager)],
)
async def update_category(
    category_id: int,
    body: CategoryUpdate,
    db: DbDep,
    actor: User = Depends(RequireManager),
) -> CategoryOut:
    from app.core.errors import NotFoundError
    from app.repositories.product_repository import ProductRepository
    from app.services.audit_service import record_audit

    repo = ProductRepository(db)
    category = await repo.get_category(category_id)
    if category is None:
        raise NotFoundError(detail=f"category id={category_id} not found")
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(category, field, value)
    await record_audit(
        db,
        user_id=actor.id,
        action=AuditAction.CATEGORY_UPDATED.value,
        entity_type="category",
        entity_id=category.id,
        details=changes,
    )
    return CategoryOut.model_validate(category)
