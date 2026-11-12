import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.user import StaffRank, UserRole, UserStatus


class StaffCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    staff_id: Optional[str] = Field(None, max_length=50)
    email: str = Field(..., min_length=1, max_length=255)
    rank: Optional[StaffRank] = None
    department_id: Optional[uuid.UUID] = None
    role: UserRole = UserRole.LECTURER


class StaffUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    rank: Optional[StaffRank] = None
    department_id: Optional[uuid.UUID] = None
    phone: Optional[str] = Field(None, max_length=20)
    office: Optional[str] = Field(None, max_length=100)


class StaffResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    rank: Optional[StaffRank] = None
    staff_id: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    status: UserStatus
    course_count: int = 0
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StaffListResponse(BaseModel):
    data: List[StaffResponse]
    meta: Optional[dict] = None
