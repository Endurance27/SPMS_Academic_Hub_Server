import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, select
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
        limit: int = 100,
    ) -> Tuple[List[Programme], int]:
        query = select(Programme).where(Programme.department_id == department_id)

        total = (await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar()

        query = query.order_by(Programme.name).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def list_all(
        self,
        department_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Programme], int]:
        query = select(Programme)
        if department_id:
            query = query.where(Programme.department_id == department_id)

        total = (await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar()

        query = query.order_by(Programme.name).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total
