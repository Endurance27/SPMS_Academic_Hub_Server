import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SemesterBase(BaseModel):
    academic_year: str = Field(..., min_length=7, max_length=20)  # e.g., "2026/27"
    number: int = Field(..., ge=1, le=2)  # 1 or 2
    label: str = Field(..., min_length=1, max_length=50)
    start_date: datetime
    end_date: datetime
    teaching_start: Optional[datetime] = None
    teaching_end: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None
    graduation_deadline: Optional[datetime] = None
    is_active: bool = False


class SemesterCreate(SemesterBase):
    pass


class SemesterUpdate(BaseModel):
    academic_year: Optional[str] = None
    number: Optional[int] = None
    label: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    teaching_start: Optional[datetime] = None
    teaching_end: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None
    graduation_deadline: Optional[datetime] = None
    is_active: Optional[bool] = None


class SemesterResponse(SemesterBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SemesterListResponse(BaseModel):
    data: list[SemesterResponse]
