import uuid


from sqlalchemy import Column, DateTime, Index, String, Boolean, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Semester(Base):
    __tablename__ = "semesters"
    __table_args__ = (
        Index("ix_semesters_active_unique", "is_active", unique=True, postgresql_where="is_active = true"),
    )

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    academic_year = Column(String(20), nullable=False)
    number = Column(Integer, nullable=False)
    label = Column(String(50), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    teaching_start = Column(DateTime(timezone=True), nullable=True)
    teaching_end = Column(DateTime(timezone=True), nullable=True)
    registration_deadline = Column(DateTime(timezone=True), nullable=True)
    graduation_deadline = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    master_timetables = relationship("MasterTimetable", back_populates="semester", cascade="all, delete-orphan")
