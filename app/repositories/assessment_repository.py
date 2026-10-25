import uuid
from typing import Optional, List

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.user import UserRole
from app.repositories.base import BaseRepository


class AssessmentRepository(BaseRepository[Assessment]):
    def __init__(self, db: AsyncSession):
        super().__init__(Assessment, db)

    async def list_filtered(
        self,
        status: Optional[str],
        scope: Optional[str],
        course_id: Optional[uuid.UUID],
        search: Optional[str],
        user_role: UserRole,
        user_department_id: Optional[uuid.UUID],
        user_id: uuid.UUID
    ) -> List[Assessment]:
        query = select(Assessment)

        if status:
            try:
                status_enum = AssessmentStatus(status)
                query = query.where(Assessment.status == status_enum)
            except ValueError:
                pass

        if course_id:
            query = query.where(Assessment.course_id == course_id)

        if scope:
            try:
                query = query.where(Assessment.scope == scope)
            except ValueError:
                pass

        # Scoping
        if user_role == UserRole.DEPARTMENT:
            query = query.where(Assessment.department_id == user_department_id)
        elif user_role == UserRole.LECTURER:
            query = query.where(Assessment.created_by_id == user_id)
        elif user_role == UserRole.STUDENT:
            # Students only see Upcoming/Shared for their courses
            query = query.where(
                and_(
                    Assessment.status.in_([AssessmentStatus.UPCOMING, AssessmentStatus.SHARED]),
                    Assessment.scope == "central"
                )
            )

        if search:
            query = query.where(
                or_(
                    Assessment.course_code.ilike(f"%{search}%"),
                    Assessment.course_title.ilike(f"%{search}%")
                )
            )

        query = query.order_by(Assessment.date, Assessment.start_time)

        result = await self.db.execute(query)
        return list(result.scalars().all())
