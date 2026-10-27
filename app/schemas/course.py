import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.course import CourseType, CourseMode


class CourseCohort(BaseModel):
    programme_id: uuid.UUID
    level: int


class CourseBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    department_id: uuid.UUID
    type: CourseType
    credit_hours: int = Field(..., ge=1, le=6)
    mode: CourseMode = CourseMode.IN_PERSON
    student_count: int = Field(..., ge=1)
    lecturer_id: Optional[uuid.UUID] = None
    cohorts: List[CourseCohort] = Field(..., min_items=1)


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[CourseType] = None
    credit_hours: Optional[int] = Field(None, ge=1, le=6)
    mode: Optional[CourseMode] = None
    student_count: Optional[int] = Field(None, ge=1)
    lecturer_id: Optional[uuid.UUID] = None
    cohorts: Optional[List[CourseCohort]] = None


class CourseResponse(CourseBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CourseListResponse(BaseModel):
    data: List[CourseResponse]
    meta: Optional[dict] = None
