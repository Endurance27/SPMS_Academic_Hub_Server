import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_agent = Column(String(500))
    ip_address = Column(String(45))
    location = Column(String(255))
    revoked_at = Column(DateTime(timezone=True))
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
