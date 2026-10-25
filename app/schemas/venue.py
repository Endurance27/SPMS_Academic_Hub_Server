import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.venue import VenueType, VenueStatus


class VenueBase(BaseModel):
    code: Optional[str] = None
    building: str = Field(..., min_length=1, max_length=100)
    room_number: str = Field(..., min_length=1, max_length=50)
    location: Optional[str] = None
    gps_address: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    capacity: Optional[int] = None
    type: VenueType
    is_shared: bool = False
    status: VenueStatus = VenueStatus.AVAILABLE


class VenueCreate(VenueBase):
    pass


class VenueUpdate(BaseModel):
    building: Optional[str] = None
    room_number: Optional[str] = None
    location: Optional[str] = None
    gps_address: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    capacity: Optional[int] = None
    type: Optional[VenueType] = None
    is_shared: Optional[bool] = None
    status: Optional[VenueStatus] = None


class VenueResponse(VenueBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VenueListResponse(BaseModel):
    data: List[VenueResponse]
    meta: Optional[dict] = None
