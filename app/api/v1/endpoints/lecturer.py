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

router = APIRouter()


@router.get("/lecturer/courses")
async def get_lecturer_courses(
    semester_id: Optional[UUID] = Query(None),
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

    return {"data": course_data}


@router.get("/lecturer/students")
async def get_lecturer_students(
    course_id: UUID = Query(...),
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

    result = await db.execute(
        select(CourseRegistration)
        .options(selectinload(CourseRegistration.student).selectinload(User.programme))
        .where(
            CourseRegistration.course_id == course_id,
            CourseRegistration.status == RegistrationStatus.REGISTERED,
        )
    )
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
        "meta": {
            "course_code": course.code,
            "course_title": course.title,
            "total": len(students),
        },
    }
