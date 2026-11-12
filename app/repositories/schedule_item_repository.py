import uuid
from typing import Optional, List

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule_item import ScheduleItem, ScheduleItemStatus
from app.models.user import UserRole
from app.repositories.base import BaseRepository


class ScheduleItemRepository(BaseRepository[ScheduleItem]):
    def __init__(self, db: AsyncSession):
        super().__init__(ScheduleItem, db)

    async def list_filtered(
        self,
        semester_id: uuid.UUID,
        department_id: Optional[uuid.UUID],
        level: Optional[int],
        venue_type: Optional[str],
        search: Optional[str],
        status: Optional[str],
        user_role: UserRole,
        user_department_id: Optional[uuid.UUID],
        skip: int = 0,
        limit: int = 25,
    ) -> tuple[list[ScheduleItem], int]:
        from sqlalchemy.orm import selectinload
        from app.models.course import Course

        query = select(ScheduleItem).where(ScheduleItem.semester_id == semester_id)

        if status:
            try:
                status_enum = ScheduleItemStatus(status)
                query = query.where(ScheduleItem.status == status_enum)
            except ValueError:
                pass

        if department_id:
            query = query.where(ScheduleItem.department_id == department_id)

        if level:
            query = query.where(ScheduleItem.level == level)

        if user_role == UserRole.DEPARTMENT:
            query = query.where(ScheduleItem.department_id == user_department_id)

        if search:
            query = query.join(Course, ScheduleItem.course_id == Course.id).where(
                Course.code.ilike(f"%{search}%") | Course.title.ilike(f"%{search}%")
            )

        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        query = query.order_by(ScheduleItem.day, ScheduleItem.start_period)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def count_by_status(
        self,
        semester_id: uuid.UUID,
        status: ScheduleItemStatus
    ) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(ScheduleItem).where(
                and_(
                    ScheduleItem.semester_id == semester_id,
                    ScheduleItem.status == status
                )
            )
        )
        return result.scalar_one()
