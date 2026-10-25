import enum
import uuid


from sqlalchemy import Column, DateTime, String, ForeignKey, Integer, Boolean, JSON, Table, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ScheduleItemStatus(str, enum.Enum):
    PENDING = "pending"
    CONFLICT = "conflict"
    PUBLISHED = "published"


class ScheduleItemSource(str, enum.Enum):
    REQUEST = "request"
    MANUAL = "manual"
    DEPARTMENT_UPLOAD = "department-upload"


schedule_item_groups = Table(
    "schedule_item_groups",
    Base.metadata,
    Column("schedule_item_id", UUID(as_uuid=True), ForeignKey("schedule_items.id", ondelete="CASCADE"), primary_key=True),
    Column("programme_id", UUID(as_uuid=True), ForeignKey("programmes.id", ondelete="CASCADE"), primary_key=True),
    Column("level", Integer, primary_key=True),
    Column("section", String(50)),
)


class ScheduleItem(Base):
    __tablename__ = "schedule_items"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False)
    slot_request_id = Column(UUID(as_uuid=True), ForeignKey("slot_requests.id"))
    day = Column(Integer, nullable=False)
    start_period = Column(Integer)
    period_count = Column(Integer)
    start = Column(String(5))  # "HH:MM"
    end = Column(String(5))
    venue_code = Column(String(50), nullable=False)
    lecturer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    mode = Column(String(20))
    status = Column(Enum(ScheduleItemStatus), default=ScheduleItemStatus.PENDING)
    source = Column(Enum(ScheduleItemSource), default=ScheduleItemSource.MANUAL)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    semester = relationship("Semester")
    course = relationship("Course")
    department = relationship("Department")
    slot_request = relationship("SlotRequest", foreign_keys=[slot_request_id])
    lecturer = relationship("User", foreign_keys=[lecturer_id])
