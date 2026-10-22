import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    action = Column(String(100), nullable=False)  # e.g., "login", "create_application"
    resource_type = Column(String(50))  # e.g., "application", "user"
    resource_id = Column(UUID(as_uuid=True), nullable=True)

    ip_address = Column(String(45))
    user_agent = Column(String(500))

    details = Column(JSON)  # Additional context
    changes = Column(JSON)  # Before/after for updates

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])
