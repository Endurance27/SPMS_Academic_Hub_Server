from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User, UserRole
from app.schemas.faculty import (
    FacultyCreate,
    FacultyListResponse,
    FacultyResponse,
    FacultyUpdate,
)
from app.services.faculty_service import FacultyService

router = APIRouter()


@router.get("", response_model=FacultyListResponse)
async def list_faculty(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    department_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("staff.view")),
    db: AsyncSession = Depends(get_db),
):
    service = FacultyService(db)

    dept_id = department_id
    if current_user.role == UserRole.DEPARTMENT:
        dept_id = current_user.department_id

    skip = (page - 1) * page_size
    faculty_list, total = await service.list_faculty(
        department_id=dept_id,
        status=status_filter,
        search=search,
        skip=skip,
        limit=page_size,
    )

    return FacultyListResponse(
        data=[FacultyResponse(**f) for f in faculty_list],
        meta={"page": page, "pageSize": page_size, "total": total},
    )


@router.post("", response_model=FacultyResponse, status_code=status.HTTP_201_CREATED)
async def create_faculty(
    data: FacultyCreate,
    current_user: User = Depends(require_permission("staff.manage")),
    db: AsyncSession = Depends(get_db),
):
    service = FacultyService(db)
    dept_id = data.department_id or current_user.department_id

    if not dept_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department ID is required.",
        )

    try:
        user = await service.create_faculty(data, dept_id)
        return FacultyResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            rank=user.rank,
            staff_id=user.staff_id,
            department_id=user.department_id,
            status=user.status,
            course_count=0,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch("/{faculty_id}", response_model=FacultyResponse)
async def update_faculty(
    faculty_id: UUID,
    data: FacultyUpdate,
    current_user: User = Depends(require_permission("staff.manage")),
    db: AsyncSession = Depends(get_db),
):
    service = FacultyService(db)
    user = await service.update_faculty(faculty_id, data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Faculty member not found"
        )

    return FacultyResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        rank=user.rank,
        staff_id=user.staff_id,
        department_id=user.department_id,
        status=user.status,
        course_count=0,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.post("/{faculty_id}/disable", response_model=dict)
async def disable_faculty(
    faculty_id: UUID,
    current_user: User = Depends(require_permission("staff.manage")),
    db: AsyncSession = Depends(get_db),
):
    service = FacultyService(db)
    user = await service.disable_faculty(faculty_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Faculty member not found"
        )
    return {"message": f"{user.name} has been disabled."}


@router.post("/{faculty_id}/resend-invitation", response_model=dict)
async def resend_faculty_invitation(
    faculty_id: UUID,
    current_user: User = Depends(require_permission("staff.manage")),
    db: AsyncSession = Depends(get_db),
):
    service = FacultyService(db)
    user = await service.resend_invitation(faculty_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Faculty member not found"
        )
    return {"message": "Invitation resent successfully.", "email": user.email}
