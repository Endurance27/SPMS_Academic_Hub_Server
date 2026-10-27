import uuid
from typing import Optional, List

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.slot_request import SlotRequest, SlotRequestStatus
from app.models.user import UserRole
from app.repositories.base import BaseRepository


class SlotRequestRepository(BaseRepository[SlotRequest]):
    def __init__(self, db: AsyncSession):
        super().__init__(SlotRequest, db)

    async def list_filtered(
        self,
        status: Optional[str],
        semester_id: uuid.UUID,
        department_id: Optional[uuid.UUID],
        user_role: UserRole,
        user_department_id: Optional[uuid.UUID]
    ) -> List[SlotRequest]:
        query = select(SlotRequest).where(SlotRequest.semester_id == semester_id)

        if status:
            try:
                status_enum = SlotRequestStatus(status)
                query = query.where(SlotRequest.status == status_enum)
            except ValueError:
                pass

        # Apply scoping based on role
        if user_role == UserRole.DEPARTMENT:
            query = query.where(SlotRequest.department_id == user_department_id)
        elif user_role == UserRole.LECTURER:
            # Lecturers see requests for their courses
            query = query.where(SlotRequest.requested_by_id == user_department_id)  # Actually lecturer_id
        elif user_role == UserRole.STUDENT:
            # Students don't see slot requests
            return []

        if department_id:
            query = query.where(SlotRequest.department_id == department_id)

        query = query.order_by(SlotRequest.day, SlotRequest.start_period, SlotRequest.venue_code)

        result = await self.db.execute(query)
        return list(result.scalars().all())

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
