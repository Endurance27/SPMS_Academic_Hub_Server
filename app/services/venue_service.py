import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.venue import Venue
from app.repositories.venue_repository import VenueRepository
from app.schemas.venue import VenueCreate, VenueUpdate


class VenueService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.venue_repo = VenueRepository(db)

    async def create_venue(self, data: VenueCreate) -> Venue:
        # Auto-generate code if not provided
        if not data.code:
            data.code = self._generate_code(data.building, data.room_number)
        else:
            data.code = self._normalize_code(data.code)
        
        existing = await self.venue_repo.get_by_code(data.code)
        if existing:
            raise ValueError("Venue code already exists")
        
        venue = Venue(**data.model_dump())
        self.db.add(venue)
        await self.db.commit()
        await self.db.refresh(venue)
        return venue

    def _generate_code(self, building: str, room_number: str) -> str:
        """Generate venue code from building and room number"""
        return f"{building[:3].upper()}{room_number}".replace(" ", "")

    def _normalize_code(self, code: str) -> str:
        """Normalize venue code"""
        return code.upper().replace(" ", "")

    async def get_venue(self, venue_id: uuid.UUID) -> Optional[Venue]:
        return await self.venue_repo.get_by_id(venue_id)

    async def list_venues(
        self,
        venue_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Venue]:
        return await self.venue_repo.list_all(venue_type, status, search, skip, limit)

    async def update_venue(
        self,
        venue_id: uuid.UUID,
        data: VenueUpdate
    ) -> Optional[Venue]:
        venue = await self.venue_repo.get_by_id(venue_id)
        if not venue:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(venue, field, value)
        
        await self.db.commit()
        await self.db.refresh(venue)
        return venue

    async def set_unavailable(
        self,
        venue_id: uuid.UUID,
        reason: str,
        until: Optional[datetime] = None
    ) -> Optional[Venue]:
        venue = await self.venue_repo.get_by_id(venue_id)
        if not venue:
            return None
        
        venue.status = "unavailable"
        venue.unavailable_reason = reason
        venue.unavailable_until = until
        
        await self.db.commit()
        await self.db.refresh(venue)
        return venue

    async def set_available(self, venue_id: uuid.UUID) -> Optional[Venue]:
        venue = await self.venue_repo.get_by_id(venue_id)
        if not venue:
            return None
        
        venue.status = "available"
        venue.unavailable_reason = None
        venue.unavailable_until = None
        
        await self.db.commit()
        await self.db.refresh(venue)
        return venue

    async def delete_venue(self, venue_id: uuid.UUID) -> bool:
        venue = await self.venue_repo.get_by_id(venue_id)
        if not venue:
            return False
        
        # Check if used in active semester (simplified)
        await self.db.delete(venue)
        await self.db.commit()
        return True
