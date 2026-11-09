import uuid
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, course_cohorts
from app.models.user import UserRole
from app.repositories.base import BaseRepository


class CourseRepository(BaseRepository[Course]):
    def __init__(self, db: AsyncSession):
        super().__init__(Course, db)

    async def get_by_code(self, code: str) -> Optional[Course]:
        result = await self.db.execute(
            select(Course).where(Course.code == code)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        department_id: Optional[uuid.UUID] = None,
        lecturer_id: Optional[uuid.UUID] = None,
        programme_id: Optional[uuid.UUID] = None,
        level: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list, int]:
        query = select(Course)

        if department_id:
            query = query.where(Course.department_id == department_id)
        if lecturer_id:
            query = query.where(Course.lecturer_id == lecturer_id)

        if programme_id or level:
            cohort_filter = select(course_cohorts.c.course_id)
            if programme_id:
                cohort_filter = cohort_filter.where(
                    course_cohorts.c.programme_id == programme_id
                )
            if level:
                cohort_filter = cohort_filter.where(
                    course_cohorts.c.level == level
                )
            query = query.where(Course.id.in_(cohort_filter))

        if search:
            query = query.where(
                (Course.code.ilike(f"%{search}%")) |
                (Course.title.ilike(f"%{search}%"))
            )

        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()

        query = query.order_by(Course.code).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def count_without_lecturer(self, department_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Course).where(
                Course.department_id == department_id,
                Course.lecturer_id.is_(None)
            )
        )
        return result.scalar() or 0
