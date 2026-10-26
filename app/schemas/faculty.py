import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.user import StaffRank, UserStatus


class FacultyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=1, max_length=255)
    rank: Optional[StaffRank] = None
    staff_id: Optional[str] = Field(None, max_length=50)
    department_id: Optional[uuid.UUID] = None


class FacultyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    rank: Optional[StaffRank] = None
    phone: Optional[str] = Field(None, max_length=20)
    office: Optional[str] = Field(None, max_length=100)


class FacultyResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    rank: Optional[StaffRank] = None
    staff_id: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    status: UserStatus
    course_count: int = 0
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FacultyListResponse(BaseModel):
    data: List[FacultyResponse]
    meta: Optional[dict] = None
