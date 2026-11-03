import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.models.programme import Programme
from app.models.user import User, UserRole
from app.repositories.programme_repository import ProgrammeRepository
from app.schemas.programme import ProgrammeCreate, ProgrammeUpdate


class ProgrammeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.programme_repo = ProgrammeRepository(db)

    async def _resolve_departments(self, department_ids: List[uuid.UUID]) -> List[Department]:
        result = await self.db.execute(
            select(Department).where(Department.id.in_(department_ids))
        )
        departments = list(result.scalars().all())
        found_ids = {d.id for d in departments}
        missing = set(department_ids) - found_ids
        if missing:
            raise ValueError(f"Departments not found: {', '.join(str(m) for m in missing)}")
        return departments

    async def create_programme(self, data: ProgrammeCreate) -> Programme:
        existing = await self.programme_repo.get_by_code(data.code)
        if existing:
            raise ValueError("Programme code already exists")

        departments = await self._resolve_departments(data.department_ids)

        programme = Programme(
            code=data.code,
            name=data.name,
            levels=data.levels,
            category=data.category,
        )
        programme.departments = departments
        self.db.add(programme)
        await self.db.commit()
        await self.db.refresh(programme)
        return await self.programme_repo.get_by_id(programme.id)

    async def get_programme(self, programme_id: uuid.UUID) -> Optional[Programme]:
        return await self.programme_repo.get_by_id(programme_id)

    async def list_programmes(
        self,
        department_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list, int]:
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

        if "department_ids" in update_data:
            departments = await self._resolve_departments(update_data.pop("department_ids"))
            programme.departments = departments

        for field, value in update_data.items():
            setattr(programme, field, value)

        await self.db.commit()
        return await self.programme_repo.get_by_id(programme_id)

    async def delete_programme(self, programme_id: uuid.UUID, force: bool = False) -> bool:
        programme = await self.programme_repo.get_by_id(programme_id)
        if not programme:
            return False

        if not force:
            students_result = await self.db.execute(
                select(User).where(User.programme_id == programme_id)
            )
            if students_result.scalar_one_or_none():
                raise ValueError("Cannot delete programme with enrolled students. Use force=true to override.")

        await self.db.delete(programme)
        await self.db.commit()
        return True
