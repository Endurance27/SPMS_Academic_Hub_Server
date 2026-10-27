from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User, UserRole
from app.schemas.student import (
    CohortListResponse,
    CohortResponse,
    StudentListResponse,
    StudentResponse,
)
from app.services.student_service import StudentService

router = APIRouter()


@router.get("", response_model=StudentListResponse)
async def list_students(
    department_id: Optional[UUID] = Query(None),
    programme_id: Optional[UUID] = Query(None),
    level: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("students.view")),
    db: AsyncSession = Depends(get_db),
):
    service = StudentService(db)

    dept_id = department_id
    if current_user.role == UserRole.DEPARTMENT:
        dept_id = current_user.department_id

    skip = (page - 1) * page_size
    students, total = await service.list_students(
        department_id=dept_id,
        programme_id=programme_id,
        level=level,
        search=search,
        skip=skip,
        limit=page_size,
    )

    return StudentListResponse(
        data=[StudentResponse(**s) for s in students],
        meta={"page": page, "pageSize": page_size, "total": total},
    )


@router.get("/cohorts", response_model=CohortListResponse)
async def list_cohorts(
    department_id: Optional[UUID] = Query(None),
    current_user: User = Depends(require_permission("students.view")),
    db: AsyncSession = Depends(get_db),
):
    service = StudentService(db)

    dept_id = department_id
    if current_user.role == UserRole.DEPARTMENT:
        dept_id = current_user.department_id

    cohorts = await service.get_cohorts(department_id=dept_id)

    return CohortListResponse(
        data=[CohortResponse(**c) for c in cohorts],
    )
