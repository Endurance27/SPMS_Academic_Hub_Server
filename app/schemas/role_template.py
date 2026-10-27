import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RoleTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=20)
    permissions: List[str] = []


class RoleTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    permissions: Optional[List[str]] = None


class RoleTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    permissions: List[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoleTemplateListResponse(BaseModel):
    data: List[RoleTemplateResponse]
    meta: Optional[dict] = None
