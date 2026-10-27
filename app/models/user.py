import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.role import user_roles


class UserRole(str, enum.Enum):
    SUPER = "super"
    DEPARTMENT = "department"
    LECTURER = "lecturer"
    STUDENT = "student"


class UserStatus(str, enum.Enum):
    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"


class StudentCategory(str, enum.Enum):
    UNDERGRADUATE = "Undergraduate"
    POSTGRADUATE = "Postgraduate"


class StaffRank(str, enum.Enum):
    PROFESSOR = "Professor"
    ASSOCIATE_PROFESSOR = "Associate Professor"
    SENIOR_LECTURER = "Senior Lecturer"
    LECTURER = "Lecturer"
    ASSISTANT_LECTURER = "Assistant Lecturer"


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    
    role = Column(Enum(UserRole), nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.INVITED, nullable=False)
    
    # Department & Programme scoping
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    programme_id = Column(UUID(as_uuid=True), ForeignKey("programmes.id"), nullable=True)
    
    # Student-specific fields
    level = Column(Integer, nullable=True)  # 100, 200, 300, 400, 500+
    student_category = Column(Enum(StudentCategory), nullable=True)
    student_number = Column(String(50), unique=True, nullable=True)
    
    # Staff-specific fields
    staff_id = Column(String(50), unique=True, nullable=True)
    rank = Column(Enum(StaffRank), nullable=True)
    
    # Contact info
    phone = Column(String(20))
    office = Column(String(100))
    photo_url = Column(String(500), nullable=True)
    
    # Display title (computed field, stored for performance)
    title = Column(String(255), nullable=True)
    
    # 2FA
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(32), nullable=True)
    two_factor_method = Column(String(20), nullable=True)  # 'sms' or 'totp'
    
    # Role template for admins
    role_template_id = Column(UUID(as_uuid=True), ForeignKey("role_templates.id"), nullable=True)
    
    # Session tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        foreign_keys="[AuditLog.user_id]",
        cascade="all, delete-orphan",
    )
    department = relationship("Department", foreign_keys=[department_id], back_populates="users")
    programme = relationship("Programme", foreign_keys=[programme_id], back_populates="students")
    role_template = relationship("RoleTemplate", foreign_keys=[role_template_id])
    
    # Lecturer relationships
    courses = relationship("Course", foreign_keys="[Course.lecturer_id]", back_populates="lecturer")
    
    # Notification preferences (1:1)
    notification_preferences = relationship(
        "NotificationPreferences",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Roles (many-to-many)
    roles = relationship("Role", secondary=user_roles, back_populates="users")
