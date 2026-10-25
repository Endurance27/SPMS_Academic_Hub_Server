import enum
import uuid


from sqlalchemy import Column, DateTime, String, ForeignKey, Integer, Text, Boolean, Table, Enum, func
from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base


class AssessmentType(str, enum.Enum):
    INTERIM_ASSESSMENT = "Interim Assessment (IA)"
    QUIZ = "Quiz"
    MID_SEMESTER_EXAMINATION = "Mid-semester examination"
    FINAL_EXAMINATION = "Final examination"
    PRACTICAL_ASSESSMENT = "Practical assessment"
    PROJECT_PRESENTATION = "Project presentation"


class DeliveryMode(str, enum.Enum):
    IN_PERSON = "In-person"
    ONLINE = "Online"
    HYBRID = "Hybrid"


class AssessmentStatus(str, enum.Enum):
    DRAFT = "Draft"
    SUBMITTED = "Submitted"
    UPCOMING = "Upcoming"
    SHARED = "Shared"
    RETURNED = "Returned"
    CANCELLED = "Cancelled"


class AssessmentScope(str, enum.Enum):
    CENTRAL = "central"
    DEPARTMENT = "department"
    FACULTY = "faculty"


assessment_invigilators = Table(
    "assessment_invigilators",
    Base.metadata,
    Column("assessment_id", UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role", String(20)),  # "chief" or "assistant"
)


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"))
    course_code = Column(String(50), nullable=False)
    course_title = Column(String(255), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False)
    assessment_type = Column(Enum(AssessmentType), nullable=False)
    delivery_mode = Column(Enum(DeliveryMode), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)
    location = Column(String(255), nullable=False)
    venue_code = Column(String(50))
    cohorts = Column(ARRAY(JSON), default=list)  # [{"programmeId", "level"}]
    status = Column(Enum(AssessmentStatus), default=AssessmentStatus.DRAFT)
    scope = Column(Enum(AssessmentScope), nullable=False)
    is_shared = Column(Boolean, default=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_by_role = Column(String(20))
    review_comment = Column(Text)
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    course = relationship("Course")
    department = relationship("Department")
    created_by = relationship("User", foreign_keys=[created_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    invigilators = relationship("User", secondary=assessment_invigilators)
