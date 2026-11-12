import enum
import uuid

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditCategory(str, enum.Enum):
    SCHEDULING = "Scheduling"
    APPROVALS = "Approvals"
    OVERRIDES = "Overrides"
    ACADEMICS = "Academics"
    PEOPLE = "People"
    ASSESSMENTS = "Assessments"
    ATTENDANCE = "Attendance"
    GRADUATION = "Graduation"
    SETTINGS = "Settings"
    AUTH = "Auth"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    actor_name = Column(String(255), nullable=False)
    actor_role = Column(String(20), nullable=False)
    action = Column(String(100), nullable=False)
    category = Column(Enum(AuditCategory), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    summary = Column(Text, nullable=False)
    before = Column(JSON)
    after = Column(JSON)
    reason = Column(Text)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    revision = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])
    department = relationship("Department")
