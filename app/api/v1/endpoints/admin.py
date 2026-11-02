import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.pagination import PaginationMeta
from app.schemas.user import UserResponse, UserRoleUpdate, UserStatusUpdate, UsersListResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user_status(
    user_id: uuid.UUID,
    data: UserStatusUpdate,
    current_user: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role == UserRole.SUPER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update super admin status"
        )

    await user_repo.update(user_id, data.dict(exclude_unset=True))
    return user


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: uuid.UUID,
    data: UserRoleUpdate,
    current_user: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role == UserRole.SUPER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update super admin role"
        )

    await user_repo.update(user_id, data.dict(exclude_unset=True))
    return user


@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("audit.view")),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func, select

    from app.models.audit import AuditLog

    total = (await db.execute(select(func.count()).select_from(AuditLog))).scalar()
    skip = (page - 1) * page_size
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(page_size)
    )
    return {
        "data": list(result.scalars().all()),
        "meta": PaginationMeta.build(page, page_size, total),
    }


@router.get("/users", response_model=UsersListResponse)
async def get_all_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    name: Optional[str] = Query(None, description="Filter users by name"),
    role: Optional[UserRole] = Query(None, description="Filter users by role"),
    is_active: Optional[bool] = Query(None, description="Filter users by active status"),
    last_login: Optional[datetime] = Query(None, description="Filter users by last login"),
    phone_number: Optional[str] = Query(None, description="Filter users by phone number"),
    email: Optional[str] = Query(None, description="Filter users by email"),
    current_user: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * per_page
    filters = {}
    if role is not None:
        filters["role"] = role
    if is_active is not None:
        filters["is_active"] = is_active
    if last_login is not None:
        filters["last_login"] = last_login
    if name is not None:
        filters["name"] = name
    if phone_number is not None:
        filters["phone_number"] = phone_number
    if email is not None:
        filters["email"] = email

    user_repo = UserRepository(db)
    items = await user_repo.get_all(skip, per_page, filters=filters or None)
    total_users = await user_repo.count(filters=filters or None)

    return UsersListResponse(
        data=items,
        meta=PaginationMeta.build(page, per_page, total_users),
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user
