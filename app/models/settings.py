import uuid


from sqlalchemy import Column, DateTime, String, ForeignKey, Boolean, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class InstitutionSettings(Base):
    __tablename__ = "institution_settings"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    organisation_name = Column(String(255), nullable=False)
    support_email = Column(String(255), nullable=False)
    office_location = Column(String(255))
    timezone = Column(String(50), default="Africa/Accra")
    active_semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))
    teaching_start = Column(String(5), default="08:00")
    teaching_end = Column(String(5), default="18:00")
    default_class_duration = Column(Integer, default=60)
    capacity_tolerance = Column(Integer, default=0)
    allow_weekends = Column(Boolean, default=False)
    require_conflict_approval = Column(Boolean, default=False)
    auto_publish_approved = Column(Boolean, default=False)
    require_graduation_approval = Column(Boolean, default=False)
    require_academic_clearance = Column(Boolean, default=False)
    require_financial_clearance = Column(Boolean, default=False)
    notify_schedule_changes = Column(Boolean, default=True)
    notify_graduation_submissions = Column(Boolean, default=True)
    notify_conflicts = Column(Boolean, default=True)
    email_channel = Column(Boolean, default=True)
    in_app_channel = Column(Boolean, default=True)
    require_admin_two_factor = Column(Boolean, default=False)
    session_timeout = Column(Integer, default=30)
    audit_retention = Column(String(20), default="1 year")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    active_semester = relationship("Semester", foreign_keys=[active_semester_id])


class DepartmentSettings(Base):
    __tablename__ = "department_settings"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False, unique=True)
    department_name = Column(String(255), nullable=False)
    department_code = Column(String(50), nullable=False)
    support_email = Column(String(255))
    office_location = Column(String(255))
    timezone = Column(String(50))
    teaching_start = Column(String(5))
    teaching_end = Column(String(5))
    default_class_duration = Column(Integer)
    capacity_tolerance = Column(Integer)
    allow_weekends = Column(Boolean)
    require_conflict_approval = Column(Boolean)
    auto_publish_approved = Column(Boolean)
    notify_schedule_changes = Column(Boolean)
    notify_graduation_submissions = Column(Boolean)
    notify_conflicts = Column(Boolean)
    email_channel = Column(Boolean)
    in_app_channel = Column(Boolean)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    department = relationship("Department", back_populates="settings")
