import uuid
from typing import Optional, List

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceSession, AttendanceRecord, AttendanceStatus
from app.models.user import UserRole
from app.repositories.base import BaseRepository


class AttendanceRepository(BaseRepository[AttendanceSession]):
    def __init__(self, db: AsyncSession):
        super().__init__(AttendanceSession, db)

    async def list_sessions_filtered(
        self,
        status: Optional[str],
        course_id: Optional[uuid.UUID],
        department_id: Optional[uuid.UUID],
        date: Optional[str],
        user_role: UserRole,
        user_department_id: Optional[uuid.UUID],
        user_id: uuid.UUID
    ) -> List[AttendanceSession]:
        query = select(AttendanceSession)

        if status:
            try:
                status_enum = AttendanceStatus(status)
                query = query.where(AttendanceSession.status == status_enum)
            except ValueError:
                pass

        if course_id:
            query = query.where(AttendanceSession.course_id == course_id)

        if date:
            query = query.where(AttendanceSession.date == date)

        # Scoping
        if user_role == UserRole.LECTURER:
            query = query.where(AttendanceSession.lecturer_id == user_id)
        elif user_role == UserRole.DEPARTMENT:
            # Filter by department courses
            pass

        query = query.order_by(AttendanceSession.date.desc(), AttendanceSession.start_time)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_session_by_id(self, session_id: uuid.UUID) -> Optional[AttendanceSession]:
        result = await self.db.execute(
            select(AttendanceSession).where(AttendanceSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_live_sessions_for_student(self, student_id: uuid.UUID) -> List[AttendanceSession]:
        from app.models.registration import CourseRegistration

        # Get student's courses
        courses_result = await self.db.execute(
            select(CourseRegistration.course_id).where(
                CourseRegistration.student_id == student_id
            )
        )
        course_ids = [r[0] for r in courses_result.all()]

        if not course_ids:
            return []

        result = await self.db.execute(
            select(AttendanceSession).where(
                and_(
                    AttendanceSession.course_id.in_(course_ids),
                    AttendanceSession.status == AttendanceStatus.LIVE
                )
            )
        )
        return list(result.scalars().all())

    async def get_record(self, session_id: uuid.UUID, student_id: uuid.UUID) -> Optional[AttendanceRecord]:
        result = await self.db.execute(
            select(AttendanceRecord).where(
                and_(
                    AttendanceRecord.session_id == session_id,
                    AttendanceRecord.student_id == student_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_records_by_session(self, session_id: uuid.UUID) -> List[AttendanceRecord]:
        result = await self.db.execute(
            select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
        )
        return list(result.scalars().all())

    async def list_records_filtered(
        self,
        course_id: Optional[uuid.UUID],
        student_id: Optional[uuid.UUID],
        from_date: Optional[str],
        to_date: Optional[str],
        user_role: UserRole,
        user_id: uuid.UUID
    ) -> List[AttendanceRecord]:
        query = select(AttendanceRecord)

        if course_id:
            query = query.where(AttendanceRecord.course_id == course_id)

        if student_id:
            query = query.where(AttendanceRecord.student_id == student_id)

        if from_date:
            query = query.where(AttendanceRecord.recorded_at >= from_date)

        if to_date:
            query = query.where(AttendanceRecord.recorded_at <= to_date)

        # Scoping
        if user_role == UserRole.LECTURER:
            # Filter by lecturer's courses
            pass
        elif user_role == UserRole.STUDENT:
            query = query.where(AttendanceRecord.student_id == user_id)

        query = query.order_by(AttendanceRecord.recorded_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())
