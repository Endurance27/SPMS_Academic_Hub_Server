import enum
import uuid


from sqlalchemy import Column, DateTime, String, ForeignKey, Integer, Boolean, Table, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class CourseType(str, enum.Enum):
    CORE = "Core"
    ELECTIVE = "Elective"
    PROJECT = "Project / long essay/ thesis"
    LAB = "Lab/practicals"
    INTERNSHIP = "Internship"
    SEMINAR = "Seminar"


class CourseMode(str, enum.Enum):
    ONLINE = "online"
    IN_PERSON = "in-person"
    HYBRID = "hybrid"


# Association table for course cohorts
course_cohorts = Table(
    "course_cohorts",
    Base.metadata,
    Column("course_id", UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
    Column("programme_id", UUID(as_uuid=True), ForeignKey("programmes.id", ondelete="CASCADE"), primary_key=True),
    Column("level", Integer, primary_key=True),
)


class Course(Base):
    __tablename__ = "courses"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    code = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False)
    type = Column(Enum(CourseType), nullable=False)
    credit_hours = Column(Integer, nullable=False)
    mode = Column(Enum(CourseMode), default=CourseMode.IN_PERSON)
    student_count = Column(Integer, nullable=False)
    lecturer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    department = relationship("Department", back_populates="courses")
    lecturer = relationship("User", foreign_keys=[lecturer_id], back_populates="courses")
    programmes = relationship("Programme", secondary=course_cohorts, back_populates="courses")
