import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.programme import Programme
from app.repositories.base import BaseRepository


class ProgrammeRepository(BaseRepository[Programme]):
    def __init__(self, db: AsyncSession):
        super().__init__(Programme, db)

    async def get_by_code(self, code: str) -> Optional[Programme]:
        result = await self.db.execute(
            select(Programme).where(Programme.code == code)
        )
        return result.scalar_one_or_none()

    async def list_by_department(
        self,
        department_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Programme]:
        result = await self.db.execute(
            select(Programme)
            .where(Programme.department_id == department_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def list_all(
        self,
        department_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Programme]:
        query = select(Programme)
        if department_id:
            query = query.where(Programme.department_id == department_id)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
