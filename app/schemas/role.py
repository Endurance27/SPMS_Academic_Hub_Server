import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PermissionBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    module: str


class PermissionCreate(PermissionBase):
    pass


class PermissionResponse(PermissionBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    is_admin_role: bool = False


class RoleCreate(RoleBase):
    permission_ids: List[uuid.UUID] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[uuid.UUID]] = None
    is_active: Optional[bool] = None


class RoleResponse(RoleBase):
    id: uuid.UUID
    is_system_role: bool
    is_active: bool
    created_at: datetime
    permissions: List[PermissionResponse] = []

    class Config:
        from_attributes = True
