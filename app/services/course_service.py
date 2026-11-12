import uuid
from collections import defaultdict
from typing import List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, course_cohorts
from app.models.user import User, UserRole
from app.models.programme import Programme
from app.repositories.course_repository import CourseRepository
from app.schemas.course import CourseCreate, CourseUpdate, CourseCohort


class CourseService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.course_repo = CourseRepository(db)

    async def _load_cohorts(self, course_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[dict]]:
        """Load cohorts for a list of course IDs, keyed by course_id."""
        if not course_ids:
            return {}
        result = await self.db.execute(
            select(
                course_cohorts.c.course_id,
                course_cohorts.c.programme_id,
                course_cohorts.c.level,
            ).where(course_cohorts.c.course_id.in_(course_ids))
        )
        cohorts_map: dict[uuid.UUID, list[dict]] = defaultdict(list)
        for row in result.all():
            cohorts_map[row.course_id].append(
                {"programme_id": row.programme_id, "level": row.level}
            )
        return cohorts_map

    def _course_to_dict(self, course: Course, cohorts: list[dict]) -> dict:
        return {
            "id": course.id,
            "code": course.code,
            "title": course.title,
            "department_id": course.department_id,
            "type": course.type,
            "credit_hours": course.credit_hours,
            "mode": course.mode,
            "student_count": course.student_count,
            "lecturer_id": course.lecturer_id,
            "cohorts": cohorts,
            "created_at": course.created_at,
            "updated_at": course.updated_at,
        }

    async def create_course(self, data: CourseCreate) -> dict:
        existing = await self.course_repo.get_by_code(data.code)
        if existing:
            raise ValueError(f"{data.code} already exists")

        if not data.cohorts:
            raise ValueError("Select at least one programme that takes this course")

        # Validate cohorts
        for cohort in data.cohorts:
            programme = await self.db.get(Programme, cohort.programme_id)
            if not programme:
                raise ValueError(f"Programme {cohort.programme_id} not found")
            if cohort.level not in programme.levels:
                raise ValueError(f"Level {cohort.level} not in programme levels")

        # Validate lecturer
        if data.lecturer_id:
            lecturer = await self.db.get(User, data.lecturer_id)
            if not lecturer or lecturer.role != UserRole.LECTURER:
                raise ValueError("Invalid lecturer")

        course = Course(
            code=data.code.upper(),
            title=data.title,
            department_id=data.department_id,
            type=data.type,
            credit_hours=data.credit_hours,
            mode=data.mode,
            student_count=data.student_count,
            lecturer_id=data.lecturer_id
        )
        self.db.add(course)
        await self.db.flush()

        for cohort in data.cohorts:
            await self.db.execute(
                course_cohorts.insert().values(
                    course_id=course.id,
                    programme_id=cohort.programme_id,
                    level=cohort.level
                )
            )

        await self.db.commit()
        await self.db.refresh(course)

        cohorts_map = await self._load_cohorts([course.id])
        return self._course_to_dict(course, cohorts_map.get(course.id, []))

    async def get_course(self, course_id: uuid.UUID) -> Optional[dict]:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            return None
        cohorts_map = await self._load_cohorts([course.id])
        return self._course_to_dict(course, cohorts_map.get(course.id, []))

    async def list_courses(
        self,
        department_id: Optional[uuid.UUID] = None,
        lecturer_id: Optional[uuid.UUID] = None,
        programme_id: Optional[uuid.UUID] = None,
        level: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list, int, dict]:
        courses, total = await self.course_repo.list_all(
            department_id, lecturer_id, programme_id, level, search, skip, limit
        )

        course_ids = [c.id for c in courses]
        cohorts_map = await self._load_cohorts(course_ids)
        data = [
            self._course_to_dict(c, cohorts_map.get(c.id, []))
            for c in courses
        ]

        extra = {}
        if department_id:
            extra["without_lecturer"] = await self.course_repo.count_without_lecturer(department_id)

        return data, total, extra

    async def update_course(
        self,
        course_id: uuid.UUID,
        data: CourseUpdate
    ) -> Optional[dict]:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            return None

        if data.code and data.code != course.code:
            existing = await self.course_repo.get_by_code(data.code)
            if existing:
                raise ValueError(f"{data.code} already exists")

        if data.lecturer_id:
            lecturer = await self.db.get(User, data.lecturer_id)
            if not lecturer or lecturer.role != UserRole.LECTURER:
                raise ValueError("Invalid lecturer")

        if data.cohorts is not None:
            delete_stmt = delete(course_cohorts).where(course_cohorts.c.course_id == course_id)
            await self.db.execute(delete_stmt)
            for cohort in data.cohorts:
                programme = await self.db.get(Programme, cohort.programme_id)
                if not programme or cohort.level not in programme.levels:
                    raise ValueError("Invalid cohort")
                await self.db.execute(
                    course_cohorts.insert().values(
                        course_id=course.id,
                        programme_id=cohort.programme_id,
                        level=cohort.level
                    )
                )

        update_data = data.model_dump(exclude_unset=True, exclude={"cohorts"})
        if update_data.get("code"):
            update_data["code"] = update_data["code"].upper()

        for field, value in update_data.items():
            setattr(course, field, value)

        await self.db.commit()
        await self.db.refresh(course)

        cohorts_map = await self._load_cohorts([course.id])
        return self._course_to_dict(course, cohorts_map.get(course.id, []))

    async def delete_course(self, course_id: uuid.UUID, force: bool = False) -> bool:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            return False
        
        if not force:
            from app.models.slot_request import SlotRequest, SlotRequestStatus
            from app.models.schedule_item import ScheduleItem
            
            # Check for approved slot requests
            approved = await self.db.execute(
                select(func.count()).select_from(SlotRequest).where(
                    SlotRequest.course_id == course_id,
                    SlotRequest.status == SlotRequestStatus.APPROVED
                )
            )
            if approved.scalar() > 0:
                raise ValueError("Cannot delete course with approved slot requests")
            
            # Check for published schedule items
            published = await self.db.execute(
                select(func.count()).select_from(ScheduleItem).where(
                    ScheduleItem.course_id == course_id,
                    ScheduleItem.status == "published"
                )
            )
            if published.scalar() > 0:
                raise ValueError("Cannot delete course with published schedule items")
        
        await self.db.delete(course)
        await self.db.commit()
        return True
