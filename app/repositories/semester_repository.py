import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.semester import Semester
from app.repositories.base import BaseRepository


class SemesterRepository(BaseRepository[Semester]):
    def __init__(self, db: AsyncSession):
        super().__init__(Semester, db)

    async def get_active(self) -> Optional[Semester]:
        result = await self.db.execute(
            select(Semester).where(Semester.is_active == True)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Semester]:
        result = await self.db.execute(select(Semester))
        return result.scalars().all()
