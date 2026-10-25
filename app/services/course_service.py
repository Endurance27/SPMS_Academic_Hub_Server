import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select

from app.models.course import Course, course_cohorts
from app.models.user import User, UserRole
from app.models.programme import Programme
from app.repositories.course_repository import CourseRepository
from app.schemas.course import CourseCreate, CourseUpdate, CourseCohort


class CourseService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.course_repo = CourseRepository(db)

    async def create_course(self, data: CourseCreate) -> Course:
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

        # Add cohorts using the association table
        for cohort in data.cohorts:
            self.db.execute(
                course_cohorts.insert().values(
                    course_id=course.id,
                    programme_id=cohort.programme_id,
                    level=cohort.level
                )
            )

        await self.db.commit()
        await self.db.refresh(course)
        return course

    async def get_course(self, course_id: uuid.UUID) -> Optional[Course]:
        return await self.course_repo.get_by_id(course_id)

    async def list_courses(
        self,
        department_id: Optional[uuid.UUID] = None,
        lecturer_id: Optional[uuid.UUID] = None,
        programme_id: Optional[uuid.UUID] = None,
        level: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Course], dict]:
        courses = await self.course_repo.list_all(
            department_id, lecturer_id, programme_id, level, search, skip, limit
        )
        
        meta = {}
        if department_id:
            meta["without_lecturer"] = await self.course_repo.count_without_lecturer(department_id)
        
        return courses, meta

    async def update_course(
        self,
        course_id: uuid.UUID,
        data: CourseUpdate
    ) -> Optional[Course]:
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
        
        # Update cohorts if provided
        if data.cohorts is not None:
            # Delete existing cohorts
            delete_stmt = delete(course_cohorts).where(course_cohorts.c.course_id == course_id)
            await self.db.execute(delete_stmt)
            # Add new cohorts
            for cohort in data.cohorts:
                programme = await self.db.get(Programme, cohort.programme_id)
                if not programme or cohort.level not in programme.levels:
                    raise ValueError("Invalid cohort")
                self.db.execute(
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
        return course

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
