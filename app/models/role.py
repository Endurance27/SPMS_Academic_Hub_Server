import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base

# Association table for user-role many-to-many relationship
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("assigned_at", DateTime, default=datetime.utcnow),
)

# Association table for role-permission many-to-many relationship
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "permission_id",
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(100), unique=True, nullable=False)  # e.g., "application.create"
    description = Column(Text)
    module = Column(String(50), index=True)  # e.g., "applications", "reports", "users"

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class Role(Base):
    __tablename__ = "roles"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(100), unique=True, nullable=False)  # e.g., "financial_investigator"
    description = Column(Text)

    # Role type
    is_system_role = Column(Boolean, default=False)  # Cannot be deleted if True
    is_admin_role = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True)

    # Metadata
    created_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    users = relationship("User", secondary=user_roles, back_populates="roles")
    created_by = relationship("User", foreign_keys=[created_by_id])
