from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User, UserRole
from app.schemas.pagination import PaginationMeta
from app.schemas.student import (
    CohortListResponse,
    CohortResponse,
    StudentCreate,
    StudentListResponse,
    StudentResponse,
)
from app.services.student_service import StudentService

router = APIRouter()


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def onboard_student(
    data: StudentCreate,
    current_user: User = Depends(require_permission("students.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Onboard a single student with an invitation email."""
    dept_id = current_user.department_id
    if not dept_id and current_user.role != UserRole.SUPER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department context required.",
        )

    service = StudentService(db)
    try:
        student, _ = await service.onboard_student(
            name=data.name,
            email=data.email,
            student_number=data.student_number,
            programme_id=data.programme_id,
            level=data.level,
            student_category=data.student_category.value if data.student_category else None,
            department_id=dept_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )

    return StudentResponse(
        id=student.id,
        name=student.name,
        email=student.email,
        student_number=student.student_number,
        programme_id=student.programme_id,
        level=student.level,
        student_category=student.student_category,
        status=student.status,
        created_at=student.created_at,
    )


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
        meta=PaginationMeta.build(page, page_size, total),
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
