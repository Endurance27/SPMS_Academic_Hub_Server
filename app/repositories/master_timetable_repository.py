import uuid
from typing import Optional, List

from sqlalchemy import select, and_, func, or_
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

    # Default PG cohort days: evening weekdays and weekends include Friday.
    COHORT_DAYS = {
        "evening": [0, 1, 2, 3, 4],     # Monday-Friday
        "weekend_saturday": [4, 5],     # Friday + Saturday
        "weekend_sunday": [4, 6],       # Friday + Sunday
    }
    PER_DAY_COURSE_DAYS = {
        "CSMD601": {"weekend_saturday": [5], "weekend_sunday": [6]},
        "CSMD609": {"weekend_saturday": [5], "weekend_sunday": [6]},
        "CSMD610": {"weekend_saturday": [5], "weekend_sunday": [6]},
    }

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
        programme: Optional[str] = None,
        cohort: Optional[str] = None,
        course_kind: Optional[str] = None,
        lecturer_name: Optional[str] = None,
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
        if programme is not None:
            query = query.where(MasterEntry.programme == programme)
        if cohort is not None:
            cohort_days = self.COHORT_DAYS.get(cohort)
            if cohort_days:
                per_day_filters = [
                    and_(
                        func.replace(
                            func.upper(func.trim(func.coalesce(MasterEntry.subject, ""))),
                            " ",
                            "",
                        )
                        == course_code,
                        MasterEntry.day.in_(course_days[cohort]),
                    )
                    for course_code, course_days in self.PER_DAY_COURSE_DAYS.items()
                    if cohort in course_days
                ]
                if per_day_filters:
                    normalized_subject = func.replace(
                        func.upper(func.trim(func.coalesce(MasterEntry.subject, ""))),
                        " ",
                        "",
                    )
                    query = query.where(
                        or_(
                            *per_day_filters,
                            and_(
                                ~normalized_subject.in_(self.PER_DAY_COURSE_DAYS),
                                MasterEntry.day.in_(cohort_days),
                            ),
                        )
                    )
                else:
                    query = query.where(MasterEntry.day.in_(cohort_days))
        if course_kind is not None:
            query = query.where(MasterEntry.course_kind == course_kind)
        if lecturer_name is not None:
            query = query.where(MasterEntry.lecturer_name.ilike(f"%{lecturer_name}%"))

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
