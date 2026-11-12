from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class AssessmentCreate(BaseModel):
    course_id: Optional[UUID] = None
    course_code: str
    course_title: str
    department_id: UUID
    assessment_type: str
    delivery_mode: str
    date: str
    start_time: str
    end_time: str
    location: str
    venue_code: Optional[str] = None
    cohorts: List[dict] = []
    scope: str = "department"
    is_shared: bool = False


class AssessmentUpdate(BaseModel):
    course_id: Optional[UUID] = None
    course_code: Optional[str] = None
    course_title: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    venue_code: Optional[str] = None
    cohorts: Optional[List[dict]] = None


class AssessmentResponse(BaseModel):
    id: UUID
    course_id: Optional[UUID]
    course_code: str
    course_title: str
    department_id: UUID
    assessment_type: str
    delivery_mode: str
    date: str
    start_time: str
    end_time: str
    location: str
    venue_code: Optional[str]
    cohorts: List[dict]
    status: str
    scope: str
    is_shared: bool
    created_by_id: UUID
    created_by_role: str
    review_comment: Optional[str]
    reviewed_by_id: Optional[UUID]
    reviewed_at: Optional[datetime]

    class Config:
        from_attributes = True


class AssessmentListResponse(BaseModel):
    data: List[AssessmentResponse]
    meta: dict
