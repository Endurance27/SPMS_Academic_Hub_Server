import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.role import user_roles

# from datetime import datetime


class UserRole(str, enum.Enum):
    ADMINISTRATOR = "administrator"
    APPLICANT = "applicant"
    #STAFF = "staff"
    #AGENCY = "agency"


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone_number = Column(String(20))

    role = Column(Enum(UserRole), nullable=False, default=UserRole.APPLICANT)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # 2FA
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(32), nullable=True)
    two_factor_method = Column(String(20), nullable=True)  # 'sms' or 'totp'

    # Session tracking
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        foreign_keys="[AuditLog.user_id]",
        cascade="all, delete-orphan",
    )
    roles = relationship("Role", secondary=user_roles, back_populates="users")
