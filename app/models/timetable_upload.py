import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class TimetableUpload(Base):
    __tablename__ = "timetable_uploads"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"), nullable=False)
    level = Column(Integer, nullable=False)
    filename = Column(String(255), nullable=False)
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    entry_count = Column(Integer, default=0)
    kind = Column(String(20), nullable=False)  # "master" or "department"
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    semester = relationship("Semester")
    uploaded_by = relationship("User")
    department = relationship("Department")
