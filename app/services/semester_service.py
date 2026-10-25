import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.semester import Semester
from app.repositories.semester_repository import SemesterRepository
from app.schemas.semester import SemesterCreate, SemesterUpdate


class SemesterService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.semester_repo = SemesterRepository(db)

    async def create_semester(self, data: SemesterCreate) -> Semester:
        semester = Semester(**data.model_dump())
        self.db.add(semester)
        await self.db.commit()
        await self.db.refresh(semester)
        return semester

    async def get_semester(self, semester_id: uuid.UUID) -> Semester:
        return await self.semester_repo.get_by_id(semester_id)

    async def list_semesters(self) -> list[Semester]:
        return await self.semester_repo.list_all()

    async def update_semester(self, semester_id: uuid.UUID, data: SemesterUpdate) -> Semester:
        semester = await self.semester_repo.get_by_id(semester_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(semester, field, value)
        await self.db.commit()
        await self.db.refresh(semester)
        return semester

    async def activate_semester(self, semester_id: uuid.UUID) -> Semester:
        # Deactivate all semesters
        all_semesters = await self.semester_repo.list_all()
        for sem in all_semesters:
            sem.is_active = False
        
        # Activate requested semester
        semester = await self.semester_repo.get_by_id(semester_id)
        semester.is_active = True
        
        await self.db.commit()
        await self.db.refresh(semester)
        return semester
