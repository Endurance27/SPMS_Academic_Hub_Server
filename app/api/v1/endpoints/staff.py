from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.staff import StaffCreate, StaffListResponse, StaffResponse, StaffUpdate
from app.services.staff_service import StaffService

router = APIRouter()


@router.get("", response_model=StaffListResponse)
async def list_staff(
    role: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    service = StaffService(db)
    skip = (page - 1) * page_size

    staff_list, counts = await service.list_staff(
        role=role,
        status=status_filter,
        search=search,
        skip=skip,
        limit=page_size,
    )

    return StaffListResponse(
        data=[StaffResponse(**s) for s in staff_list],
        meta={"page": page, "pageSize": page_size, "counts": counts},
    )


@router.post("", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    data: StaffCreate,
    current_user: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    service = StaffService(db)

    try:
        user = await service.create_staff(data)
        return StaffResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            rank=user.rank,
            staff_id=user.staff_id,
            department_id=user.department_id,
            department_name=None,
            status=user.status,
            course_count=0,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch("/{staff_id}", response_model=StaffResponse)
async def update_staff(
    staff_id: UUID,
    data: StaffUpdate,
    current_user: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    service = StaffService(db)
    user = await service.update_staff(staff_id, data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found"
        )

    return StaffResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        rank=user.rank,
        staff_id=user.staff_id,
        department_id=user.department_id,
        department_name=None,
        status=user.status,
        course_count=0,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )
