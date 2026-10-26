import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.graduation import GraduationStatus


class GraduationSubmissionCreate(BaseModel):
    student_category: str = Field(..., min_length=1)
    academic_year: str = Field(..., min_length=1, max_length=20)
    programme_id: Optional[uuid.UUID] = None
    programme_text: Optional[str] = Field(None, max_length=255)
    declared_count: int = Field(..., ge=1)


class GraduationCandidateResponse(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    student_number: str
    name: str
    programme: Optional[str] = None
    student_id: Optional[uuid.UUID] = None
    academic_clearance: Optional[bool] = None
    financial_clearance: Optional[bool] = None
    issues: List[str] = []

    class Config:
        from_attributes = True


class GraduationCandidateUpdate(BaseModel):
    academic_clearance: Optional[bool] = None
    financial_clearance: Optional[bool] = None


class GraduationSubmissionResponse(BaseModel):
    id: uuid.UUID
    department_id: uuid.UUID
    department_name: Optional[str] = None
    programme_id: Optional[uuid.UUID] = None
    programme_text: Optional[str] = None
    student_category: str
    academic_year: str
    declared_count: int
    filename: str
    file_url: Optional[str] = None
    row_count: Optional[int] = None
    status: GraduationStatus
    review_comment: Optional[str] = None
    reviewed_by_id: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    created_by_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class GraduationSubmissionDetailResponse(GraduationSubmissionResponse):
    candidates: List[GraduationCandidateResponse] = []


class GraduationListResponse(BaseModel):
    data: List[GraduationSubmissionResponse]
    meta: Optional[dict] = None
