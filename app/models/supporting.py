import uuid


from sqlalchemy import Column, DateTime, String, ForeignKey, ARRAY, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Section(Base):
    __tablename__ = "sections"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    programme_id = Column(UUID(as_uuid=True), ForeignKey("programmes.id"), nullable=False)
    level = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"))
    student_ids = Column(ARRAY(UUID), default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    programme = relationship("Programme")
    course = relationship("Course")


class ReportJob(Base):
    __tablename__ = "report_jobs"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    report_type = Column(String(100), nullable=False)
    academic_year = Column(String(20))
    semester = Column(String(50))
    programme_id = Column(UUID(as_uuid=True), ForeignKey("programmes.id"))
    student_category = Column(String(50))
    date_from = Column(DateTime(timezone=True))
    date_to = Column(DateTime(timezone=True))
    format = Column(String(20), default="csv")
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    status = Column(String(50), default="Ready")
    file_url = Column(String(500))
    row_count = Column(Integer)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    programme = relationship("Programme")
    department = relationship("Department")
    created_by = relationship("User")


class NotificationRead(Base):
    __tablename__ = "notification_reads"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    notification_id = Column(UUID(as_uuid=True), ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    read_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    notification = relationship("Notification")
    user = relationship("User")
