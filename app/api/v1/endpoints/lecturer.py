from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.course import Course
from app.models.registration import CourseRegistration, RegistrationStatus
from app.models.schedule_item import ScheduleItem
from app.models.user import User, UserRole
from app.schemas.pagination import PaginationMeta

router = APIRouter()


@router.get("/lecturer/courses")
async def get_lecturer_courses(
    semester_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get courses assigned to the current lecturer"""
    if current_user.role != UserRole.LECTURER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lecturers can access this endpoint",
        )

    query = (
        select(Course)
        .options(selectinload(Course.department))
        .where(Course.lecturer_id == current_user.id)
    )
    if search:
        query = query.where(
            Course.code.ilike(f"%{search}%") | Course.title.ilike(f"%{search}%")
        )

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    query = query.order_by(Course.code)
    skip = (page - 1) * page_size
    query = query.offset(skip).limit(page_size)
    result = await db.execute(query)
    courses = list(result.scalars().all())

    course_data = []
    for course in courses:
        reg_filter = [
            CourseRegistration.course_id == course.id,
            CourseRegistration.status == RegistrationStatus.REGISTERED,
        ]
        if semester_id:
            reg_filter.append(CourseRegistration.semester_id == semester_id)

        enrolled_result = await db.execute(
            select(func.count()).select_from(CourseRegistration).where(*reg_filter)
        )
        enrolled_count = enrolled_result.scalar() or 0

        hours_result = await db.execute(
            select(func.count()).select_from(ScheduleItem).where(
                ScheduleItem.course_id == course.id,
                ScheduleItem.status == "published",
            )
        )
        weekly_slots = hours_result.scalar() or 0

        course_data.append(
            {
                "id": course.id,
                "code": course.code,
                "title": course.title,
                "department": course.department.name if course.department else None,
                "type": course.type,
                "credit_hours": course.credit_hours,
                "enrolled_count": enrolled_count,
                "weekly_contact_hours": weekly_slots,
            }
        )

    return {
        "data": course_data,
        "meta": PaginationMeta.build(page, page_size, total),
    }


@router.get("/lecturer/students")
async def get_lecturer_students(
    course_id: UUID = Query(...),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get students registered for a lecturer's course"""
    if current_user.role != UserRole.LECTURER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lecturers can access this endpoint",
        )

    course_result = await db.execute(select(Course).where(Course.id == course_id))
    course = course_result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if course.lecturer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this course",
        )

    base_query = (
        select(CourseRegistration)
        .options(selectinload(CourseRegistration.student).selectinload(User.programme))
        .where(
            CourseRegistration.course_id == course_id,
            CourseRegistration.status == RegistrationStatus.REGISTERED,
        )
    )
    if search:
        base_query = base_query.join(CourseRegistration.student).where(
            User.name.ilike(f"%{search}%")
            | User.email.ilike(f"%{search}%")
            | User.student_number.ilike(f"%{search}%")
        )

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    skip = (page - 1) * page_size
    result = await db.execute(base_query.offset(skip).limit(page_size))
    registrations = list(result.scalars().all())

    students = [
        {
            "id": r.student.id,
            "name": r.student.name,
            "email": r.student.email,
            "student_number": r.student.student_number,
            "programme": r.student.programme.name if r.student.programme else None,
            "level": r.student.level,
        }
        for r in registrations
        if r.student
    ]

    return {
        "data": students,
        "meta": PaginationMeta.build(
            page, page_size, total,
            course_code=course.code,
            course_title=course.title,
        ),
    }
