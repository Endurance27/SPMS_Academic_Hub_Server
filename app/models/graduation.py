import enum
import uuid


from sqlalchemy import Column, DateTime, String, ForeignKey, Integer, Text, Boolean, JSON, Enum, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base


class GraduationStatus(str, enum.Enum):
    SUBMITTED = "Submitted"
    VALIDATED = "Validated"
    RETURNED = "Returned"


class GraduationSubmission(Base):
    __tablename__ = "graduation_submissions"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False)
    programme_id = Column(UUID(as_uuid=True), ForeignKey("programmes.id"))
    programme_text = Column(String(255))
    student_category = Column(String(50), nullable=False)
    academic_year = Column(String(20), nullable=False)
    declared_count = Column(Integer, nullable=False)
    filename = Column(String(255), nullable=False)
    file_url = Column(String(500))
    row_count = Column(Integer)
    status = Column(Enum(GraduationStatus), default=GraduationStatus.SUBMITTED)
    review_comment = Column(Text)
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at = Column(DateTime(timezone=True))
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    department = relationship("Department")
    programme = relationship("Programme")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    candidates = relationship("GraduationCandidate", back_populates="submission", cascade="all, delete-orphan")


class GraduationCandidate(Base):
    __tablename__ = "graduation_candidates"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    submission_id = Column(UUID(as_uuid=True), ForeignKey("graduation_submissions.id", ondelete="CASCADE"), nullable=False)
    student_number = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    programme = Column(String(255))
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    academic_clearance = Column(Boolean)
    financial_clearance = Column(Boolean)
    issues = Column(ARRAY(String), default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    submission = relationship("GraduationSubmission", back_populates="candidates")
    student = relationship("User")
