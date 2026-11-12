import enum
import uuid


from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class NotificationCategory(str, enum.Enum):
    SCHEDULE = "schedule"
    ASSESSMENT = "assessment"
    ATTENDANCE = "attendance"
    GRADUATION = "graduation"
    GENERAL = "general"


class NotificationPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )

    # Recipient (optional - for direct messages)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Notification details
    title = Column(String(255), nullable=False)
    detail = Column(Text, nullable=False)
    page = Column(String(100))  # Portal page label
    category = Column(Enum(NotificationCategory), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.MEDIUM)

    # Audience targeting (for broadcasts)
    audience_role = Column(String(20))  # Role enum value
    audience_department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))

    # Related resources
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=func.now(), index=True)

    # Relationships
    recipient = relationship("User", foreign_keys=[recipient_id])
    audience_department = relationship("Department")
    reads = relationship("NotificationRead", back_populates="notification", cascade="all, delete-orphan")
