import uuid
from typing import Optional, List

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.master_timetable import MasterTimetable, MasterEntry
from app.repositories.base import BaseRepository


class MasterTimetableRepository(BaseRepository[MasterTimetable]):
    def __init__(self, db: AsyncSession):
        super().__init__(MasterTimetable, db)

    async def get_by_semester_and_level(
        self,
        semester_id: uuid.UUID,
        level: int
    ) -> Optional[MasterTimetable]:
        result = await self.db.execute(
            select(MasterTimetable).where(
                and_(
                    MasterTimetable.semester_id == semester_id,
                    MasterTimetable.level == level
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_by_semester(
        self, semester_id: uuid.UUID, category: Optional[str] = None
    ) -> List[MasterTimetable]:
        query = select(MasterTimetable).where(
            MasterTimetable.semester_id == semester_id
        )
        if category:
            query = query.where(MasterTimetable.category == category)
        result = await self.db.execute(query.order_by(MasterTimetable.level))
        return list(result.scalars().all())

    async def count_entries(self, timetable_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(MasterEntry).where(
                MasterEntry.timetable_id == timetable_id
            )
        )
        return result.scalar_one()

    async def count_free_entries(self, timetable_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(MasterEntry).where(
                and_(
                    MasterEntry.timetable_id == timetable_id,
                    MasterEntry.is_free == True
                )
            )
        )
        return result.scalar_one()

    async def get_entries(
        self,
        semester_id: uuid.UUID,
        level: Optional[int] = None,
        venue_code: Optional[str] = None,
        subjects: Optional[List[str]] = None,
        day: Optional[int] = None,
        source: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        category: Optional[str] = None,
    ) -> List[MasterEntry]:
        query = (
            select(MasterEntry)
            .join(MasterTimetable, MasterEntry.timetable_id == MasterTimetable.id)
            .where(MasterTimetable.semester_id == semester_id)
        )

        if category is not None:
            query = query.where(MasterTimetable.category == category)

        if source == "master":
            query = query.where(MasterEntry.department_id.is_(None))
        elif source == "department":
            query = query.where(MasterEntry.department_id.isnot(None))

        if department_id is not None:
            query = query.where(MasterEntry.department_id == department_id)
        if level is not None:
            query = query.where(MasterEntry.level == level)
        if venue_code is not None:
            query = query.where(MasterEntry.venue_code == venue_code)
        if subjects is not None:
            query = query.where(MasterEntry.subject.in_(subjects))
        if day is not None:
            query = query.where(MasterEntry.day == day)

        query = query.order_by(MasterEntry.day, MasterEntry.period, MasterEntry.venue_code)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # TODO: Implement TimetableUpload model and uncomment this method
    # async def get_upload_history(self, semester_id: uuid.UUID) -> List[TimetableUpload]:
    #     result = await self.db.execute(
    #         select(TimetableUpload).where(
    #             TimetableUpload.semester_id == semester_id
    #         ).order_by(TimetableUpload.uploaded_at.desc())
    #     )
    #     return list(result.scalars().all())
