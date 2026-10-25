from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.models.user import User, UserRole
from app.schemas.course import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseListResponse
)
from app.services.course_service import CourseService

router = APIRouter()


async def check_course_access(
    course_id: UUID,
    user: User,
    db: AsyncSession
) -> None:
    """Check if user can access the specified course"""
    from app.repositories.course_repository import CourseRepository

    course_repo = CourseRepository(db)
    course = await course_repo.get_by_id(course_id)

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    if user.role == UserRole.SUPER:
        return
    if user.role == UserRole.DEPARTMENT:
        if user.department_id != course.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this course"
            )
        return
    if user.role == UserRole.LECTURER:
        if course.lecturer_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this course"
            )
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied"
    )


@router.get("", response_model=CourseListResponse)
async def list_courses(
    department_id: Optional[UUID] = Query(None),
    lecturer_id: Optional[UUID] = Query(None),
    programme_id: Optional[UUID] = Query(None),
    level: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("courses.view")),
    db: AsyncSession = Depends(get_db)
):
    """List courses (scoped by role)"""
    # Apply scoping based on role
    if current_user.role == UserRole.DEPARTMENT:
        department_id = current_user.department_id
    elif current_user.role == UserRole.LECTURER:
        lecturer_id = current_user.id
    # SUPER can see all

    service = CourseService(db)
    skip = (page - 1) * page_size
    courses, meta = await service.list_courses(
        department_id, lecturer_id, programme_id, level, search, skip, page_size
    )

    return CourseListResponse(
        data=courses,
        meta={**meta, "page": page, "page_size": page_size}
    )


@router.post("", response_model=CourseResponse, status_code=201)
async def create_course(
    data: CourseCreate,
    current_user: User = Depends(require_permission("courses.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Create course"""
    # Department admins can only create courses for their department
    if current_user.role == UserRole.DEPARTMENT:
        if data.department_id != current_user.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only create courses for own department"
            )

    service = CourseService(db)
    try:
        return await service.create_course(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get course by ID"""
    await check_course_access(course_id, current_user, db)

    service = CourseService(db)
    course = await service.get_course(course_id)

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    return course


@router.patch("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: UUID,
    data: CourseUpdate,
    current_user: User = Depends(require_permission("courses.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Update course"""
    service = CourseService(db)
    course = await service.get_course(course_id)

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Scope check
    if current_user.role == UserRole.DEPARTMENT:
        if course.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Access denied")

    try:
        return await service.update_course(course_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{course_id}", status_code=204)
async def delete_course(
    course_id: UUID,
    force: bool = Query(False),
    current_user: User = Depends(require_permission("courses.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Delete course"""
    service = CourseService(db)
    course = await service.get_course(course_id)

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Scope check
    if current_user.role == UserRole.DEPARTMENT:
        if course.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Access denied")

    try:
        await service.delete_course(course_id, force)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
