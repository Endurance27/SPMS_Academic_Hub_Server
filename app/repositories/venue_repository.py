import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.venue import Venue
from app.repositories.base import BaseRepository


class VenueRepository(BaseRepository[Venue]):
    def __init__(self, db: AsyncSession):
        super().__init__(Venue, db)

    async def get_by_code(self, code: str) -> Optional[Venue]:
        result = await self.db.execute(
            select(Venue).where(Venue.code == code)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        venue_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Venue], int]:
        query = select(Venue)

        if venue_type:
            query = query.where(Venue.type == venue_type)
        if status:
            query = query.where(Venue.status == status)
        if search:
            query = query.where(
                (Venue.code.ilike(f"%{search}%")) |
                (Venue.building.ilike(f"%{search}%")) |
                (Venue.room_number.ilike(f"%{search}%"))
            )

        total = (await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar()

        query = query.order_by(Venue.code).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total
