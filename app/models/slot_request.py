import enum
import uuid


from sqlalchemy import Column, DateTime, String, ForeignKey, Integer, Text, Enum, func
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class SlotRequestStatus(str, enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    RETURNED = "Returned"
    WITHDRAWN = "Withdrawn"


class SlotRequest(Base):
    __tablename__ = "slot_requests"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False)
    requested_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"), nullable=False)
    level = Column(Integer, nullable=False)
    day = Column(Integer, nullable=False)
    venue_code = Column(String(50), nullable=False)
    start_period = Column(Integer, nullable=False)
    period_count = Column(Integer, nullable=False)
    status = Column(Enum(SlotRequestStatus), default=SlotRequestStatus.PENDING)
    review_comment = Column(Text)
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at = Column(DateTime(timezone=True))
    schedule_item_id = Column(UUID(as_uuid=True), ForeignKey("schedule_items.id"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    course = relationship("Course")
    department = relationship("Department")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    semester = relationship("Semester")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    schedule_item = relationship("ScheduleItem", foreign_keys=[schedule_item_id])
