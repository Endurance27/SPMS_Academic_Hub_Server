import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.programme import Programme
from app.models.course import Course, course_cohorts
from app.models.user import User, UserRole
from app.repositories.programme_repository import ProgrammeRepository
from app.schemas.programme import ProgrammeCreate, ProgrammeUpdate


class ProgrammeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.programme_repo = ProgrammeRepository(db)

    async def create_programme(self, data: ProgrammeCreate) -> Programme:
        existing = await self.programme_repo.get_by_code(data.code)
        if existing:
            raise ValueError("Programme code already exists")
        
        programme = Programme(**data.model_dump())
        self.db.add(programme)
        await self.db.commit()
        await self.db.refresh(programme)
        return programme

    async def get_programme(self, programme_id: uuid.UUID) -> Optional[Programme]:
        return await self.programme_repo.get_by_id(programme_id)

    async def list_programmes(
        self,
        department_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Programme]:
        return await self.programme_repo.list_all(department_id, skip, limit)

    async def update_programme(
        self,
        programme_id: uuid.UUID,
        data: ProgrammeUpdate
    ) -> Optional[Programme]:
        programme = await self.programme_repo.get_by_id(programme_id)
        if not programme:
            return None
        
        if data.code and data.code != programme.code:
            existing = await self.programme_repo.get_by_code(data.code)
            if existing:
                raise ValueError("Programme code already exists")
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(programme, field, value)
        
        await self.db.commit()
        await self.db.refresh(programme)
        return programme

    async def delete_programme(self, programme_id: uuid.UUID, force: bool = False) -> bool:
        programme = await self.programme_repo.get_by_id(programme_id)
        if not programme:
            return False
        
        if not force:
            # Check for enrolled students
            from app.models.user import User
            students_result = await self.db.execute(
                select(User).where(User.programme_id == programme_id)
            )
            if students_result.scalar_one_or_none():
                raise ValueError("Cannot delete programme with enrolled students. Use force=true to override.")
        
        # Cascade delete will handle course cohorts
        await self.db.delete(programme)
        await self.db.commit()
        return True
