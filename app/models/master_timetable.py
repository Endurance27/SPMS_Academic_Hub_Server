import uuid


from sqlalchemy import Column, DateTime, String, ForeignKey, Integer, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class MasterTimetable(Base):
    __tablename__ = "master_timetables"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"), nullable=False)
    level = Column(Integer, nullable=False)
    filename = Column(String(255), nullable=False)
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    version = Column(Integer, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    semester = relationship("Semester", back_populates="master_timetables")
    uploaded_by = relationship("User")
    entries = relationship("MasterEntry", back_populates="timetable", cascade="all, delete-orphan")


class MasterEntry(Base):
    __tablename__ = "master_entries"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    timetable_id = Column(UUID(as_uuid=True), ForeignKey("master_timetables.id", ondelete="CASCADE"), nullable=False)
    level = Column(Integer, nullable=False)
    day = Column(Integer, nullable=False)  # 0-4 (Mon-Fri)
    period = Column(Integer, nullable=False)  # 0-11
    subject = Column(String(50), nullable=False)
    venue_code = Column(String(50), nullable=False)
    is_free = Column(Boolean, default=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    course_kind = Column(String(1))  # "C" or "E" or null

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    timetable = relationship("MasterTimetable", back_populates="entries")
    department = relationship("Department")
