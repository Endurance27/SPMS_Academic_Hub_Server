import enum
import uuid


from sqlalchemy import Column, DateTime, String, ForeignKey, Integer, Text, Boolean, Enum, func
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class AttendanceStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    COMPLETED = "completed"
    MISSED = "missed"


class AttendanceRecordStatus(str, enum.Enum):
    PRESENT = "Present"
    LATE = "Late"
    ABSENT = "Absent"
    EXCUSED = "Excused"


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    schedule_item_id = Column(UUID(as_uuid=True), ForeignKey("schedule_items.id"))
    lecturer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)
    venue_code = Column(String(50))
    status = Column(Enum(AttendanceStatus), default=AttendanceStatus.SCHEDULED)
    opened_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    qr_secret = Column(String(100))
    qr_rotation_seconds = Column(Integer, default=30)
    expected_count = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    course = relationship("Course")
    schedule_item = relationship("ScheduleItem")
    lecturer = relationship("User")
    records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    session_id = Column(UUID(as_uuid=True), ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(Enum(AttendanceRecordStatus), nullable=False)
    source = Column(String(50))  # "Manual entry" or "QR scan"
    recorded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    note = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    session = relationship("AttendanceSession", back_populates="records")
    course = relationship("Course")
    student = relationship("User", foreign_keys=[student_id])
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])
