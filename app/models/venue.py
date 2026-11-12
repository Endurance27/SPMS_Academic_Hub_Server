import enum
import uuid


from sqlalchemy import Column, DateTime, String, Integer, Boolean, ForeignKey, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class VenueType(str, enum.Enum):
    LECTURE_HALL = "lecture_hall"
    LABORATORY = "laboratory"
    SEMINAR_ROOM = "seminar_room"
    ONLINE = "online"
    SHARED = "shared"


class VenueStatus(str, enum.Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class Venue(Base):
    __tablename__ = "venues"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    code = Column(String(50), unique=True, nullable=False, index=True)
    building = Column(String(100), nullable=False)
    room_number = Column(String(50), nullable=False)
    location = Column(String(255))
    gps_address = Column(String(255))
    latitude = Column(String(50))
    longitude = Column(String(50))
    capacity = Column(Integer, nullable=True)
    type = Column(Enum(VenueType), nullable=False)
    is_shared = Column(Boolean, default=False)
    status = Column(Enum(VenueStatus), default=VenueStatus.AVAILABLE)
    unavailable_reason = Column(String(255))
    unavailable_until = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
