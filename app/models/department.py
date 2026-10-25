import enum
import uuid
from sqlalchemy import Boolean, Column, DateTime, String, ARRAY, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class DepartmentTone(str, enum.Enum):
    BLUE = "blue"
    VIOLET = "violet"
    AMBER = "amber"
    GREEN = "green"
    ROSE = "rose"


class Department(Base):
    __tablename__ = "departments"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    name = Column(String(255), unique=True, nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    school = Column(String(255), default="SPMS")
    email = Column(String(255), nullable=False)
    phone = Column(String(20))
    tone = Column(Enum(DepartmentTone), default=DepartmentTone.BLUE)
    subject_prefixes = Column(ARRAY(String), default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    users = relationship("User", foreign_keys="[User.department_id]", back_populates="department")
    programmes = relationship("Programme", back_populates="department", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="department", cascade="all, delete-orphan")
    settings = relationship("DepartmentSettings", back_populates="department", uselist=False, cascade="all, delete-orphan")
