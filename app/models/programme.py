import enum
import uuid


from sqlalchemy import Column, DateTime, String, ForeignKey, ARRAY, Integer, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProgrammeCategory(str, enum.Enum):
    UNDERGRADUATE = "Undergraduate"
    POSTGRADUATE = "Postgraduate"


class Programme(Base):
    __tablename__ = "programmes"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False)
    levels = Column(ARRAY(Integer), default=list)  # [100, 200, 300, 400]
    category = Column(Enum(ProgrammeCategory), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    department = relationship("Department", back_populates="programmes")
    students = relationship("User", foreign_keys="[User.programme_id]", back_populates="programme")
    courses = relationship("Course", secondary="course_cohorts", back_populates="programmes")
