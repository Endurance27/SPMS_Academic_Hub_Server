import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.department import DepartmentTone


class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    school: Optional[str] = "SPMS"
    email: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = None
    tone: Optional[DepartmentTone] = DepartmentTone.BLUE
    subject_prefixes: Optional[List[str]] = []


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    school: Optional[str] = None
    email: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = None
    tone: Optional[DepartmentTone] = None
    subject_prefixes: Optional[List[str]] = None


class DepartmentResponse(DepartmentBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DepartmentDetailResponse(DepartmentResponse):
    programmes_count: int = 0
    courses_count: int = 0
    lecturers_count: int = 0
    students_count: int = 0
    admin_account: Optional[dict] = None


class DepartmentListResponse(BaseModel):
    data: List[DepartmentResponse]
    meta: Optional[dict] = None
