import uuid
from typing import Optional, List

from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.slot_request import SlotRequest, SlotRequestStatus
from app.models.user import UserRole
from app.repositories.base import BaseRepository


class SlotRequestRepository(BaseRepository[SlotRequest]):
    def __init__(self, db: AsyncSession):
        super().__init__(SlotRequest, db)

    def _build_list_query(
        self,
        semester_id: uuid.UUID,
        status: Optional[str],
        department_id: Optional[uuid.UUID],
        user_role: UserRole,
        user_department_id: Optional[uuid.UUID],
    ):
        query = select(SlotRequest).where(SlotRequest.semester_id == semester_id)

        if status:
            try:
                status_enum = SlotRequestStatus(status)
                query = query.where(SlotRequest.status == status_enum)
            except ValueError:
                pass

        if user_role == UserRole.DEPARTMENT:
            query = query.where(SlotRequest.department_id == user_department_id)
        elif user_role == UserRole.LECTURER:
            query = query.where(SlotRequest.requested_by_id == user_department_id)
        elif user_role == UserRole.STUDENT:
            return None

        if department_id:
            query = query.where(SlotRequest.department_id == department_id)

        return query

    async def list_filtered(
        self,
        status: Optional[str],
        semester_id: uuid.UUID,
        department_id: Optional[uuid.UUID],
        user_role: UserRole,
        user_department_id: Optional[uuid.UUID],
        skip: int = 0,
        limit: int = 25,
    ) -> tuple[List[SlotRequest], int]:
        query = self._build_list_query(
            semester_id, status, department_id, user_role, user_department_id
        )
        if query is None:
            return [], 0

        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        query = query.order_by(
            SlotRequest.day, SlotRequest.start_period, SlotRequest.venue_code
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def count_by_status(
        self,
        semester_id: uuid.UUID,
        department_id: Optional[uuid.UUID],
        user_role: UserRole,
        user_department_id: Optional[uuid.UUID],
    ) -> dict:
        query = self._build_list_query(
            semester_id, None, department_id, user_role, user_department_id
        )
        if query is None:
            return {"Pending": 0, "Approved": 0, "Returned": 0, "All": 0}

        result = await self.db.execute(
            select(SlotRequest.status, func.count())
            .where(query.whereclause)
            .group_by(SlotRequest.status)
        )
        counts = {"Pending": 0, "Approved": 0, "Returned": 0, "All": 0}
        for row in result.all():
            key = row[0].value
            if key in counts:
                counts[key] = row[1]
            counts["All"] += row[1]
        return counts

    async def get_by_course(self, course_id: uuid.UUID) -> List[SlotRequest]:
        result = await self.db.execute(
            select(SlotRequest).where(SlotRequest.course_id == course_id)
        )
        return list(result.scalars().all())

    async def get_by_semester_and_level(
        self,
        semester_id: uuid.UUID,
        level: int
    ) -> List[SlotRequest]:
        result = await self.db.execute(
            select(SlotRequest).where(
                and_(
                    SlotRequest.semester_id == semester_id,
                    SlotRequest.level == level
                )
            )
        )
        return list(result.scalars().all())
