import enum
import uuid


from sqlalchemy import Column, DateTime, String, ForeignKey, Integer, Boolean, Enum, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class RegistrationType(str, enum.Enum):
    CORE = "Core"
    ELECTIVE = "Elective"
    RESEARCH_PROJECT = "Research / Project"
    LAB_PRACTICAL = "Lab / Practical"


class RegistrationStatus(str, enum.Enum):
    REGISTERED = "Registered"
    DROPPED = "Dropped"
    PENDING_APPROVAL = "Pending approval"


class CourseRegistration(Base):
    __tablename__ = "course_registrations"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"))
    custom_course_code = Column(String(50))
    custom_course_title = Column(String(255))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"), nullable=False)
    level = Column(Integer, nullable=False)
    registration_type = Column(Enum(RegistrationType), nullable=False)
    credits = Column(Integer, nullable=False)
    status = Column(Enum(RegistrationStatus), default=RegistrationStatus.REGISTERED)
    source = Column(String(50))  # "self" or "roster-import"

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    student = relationship("User")
    course = relationship("Course")
    semester = relationship("Semester")


class StudentImport(Base):
    __tablename__ = "student_imports"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    kind = Column(String(50), nullable=False)  # "student-onboarding" or "course-roster"
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"))
    programme_id = Column(UUID(as_uuid=True), ForeignKey("programmes.id"))
    programme_text = Column(String(255))
    level_text = Column(String(50))
    student_category = Column(String(50))
    academic_year = Column(String(20))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))
    filename = Column(String(255), nullable=False)
    file_url = Column(String(500))
    row_count = Column(Integer)
    created_count = Column(Integer, default=0)
    updated_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    status = Column(String(50), default="Queued")
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    department = relationship("Department")
    course = relationship("Course")
    programme = relationship("Programme")
    semester = relationship("Semester")
    created_by = relationship("User")
    rows = relationship("StudentImportRow", back_populates="import_obj", cascade="all, delete-orphan")


class StudentImportRow(Base):
    __tablename__ = "student_import_rows"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    import_id = Column(UUID(as_uuid=True), ForeignKey("student_imports.id", ondelete="CASCADE"), nullable=False)
    row_number = Column(Integer, nullable=False)
    raw = Column(JSON)
    outcome = Column(String(50))  # "created", "updated", "skipped"
    message = Column(String(500))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    import_obj = relationship("StudentImport", back_populates="rows")
