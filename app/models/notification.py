import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class NotificationType(str, enum.Enum):
    APPLICATION_SUBMITTED = "application_submitted"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    REPORT_GENERATED = "report_generated"
    INVITATION_SENT = "invitation_sent"
    COMMENT_ADDED = "comment_added"
    STATUS_CHANGED = "status_changed"
    SYSTEM_ALERT = "system_alert"


class NotificationPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )

    # Recipient
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Notification details
    type = Column(Enum(NotificationType), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.MEDIUM)

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Related resources
    resource_type = Column(String(50))  # e.g., "application", "task"
    resource_id = Column(UUID(as_uuid=True))

    # Action URL
    action_url = Column(String(500))

    # Metadata
    data = Column(JSON)  # Additional notification data

    # Status
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime, nullable=True)

    # Delivery channels
    sent_email = Column(Boolean, default=False)
    sent_sms = Column(Boolean, default=False)
    sent_push = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User")
