import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class NotificationPreferences(Base):
    __tablename__ = "notification_preferences"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Notification categories
    schedule_notifications = Column(Boolean, default=True)
    assessment_notifications = Column(Boolean, default=True)
    attendance_notifications = Column(Boolean, default=True)
    graduation_notifications = Column(Boolean, default=True)

    # Channels
    email_notifications = Column(Boolean, default=True)
    in_app_notifications = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationship
    user = relationship("User", back_populates="notification_preferences")
