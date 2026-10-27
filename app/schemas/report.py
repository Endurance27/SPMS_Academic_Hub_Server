import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    report_type: str = Field(..., min_length=1)
    academic_year: Optional[str] = None
    semester: Optional[str] = None
    programme_id: Optional[uuid.UUID] = None
    student_category: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    format: str = "csv"
    department_id: Optional[uuid.UUID] = None


class ReportResponse(BaseModel):
    id: uuid.UUID
    report_type: str
    academic_year: Optional[str] = None
    semester: Optional[str] = None
    status: str
    file_url: Optional[str] = None
    row_count: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    data: List[ReportResponse]
    meta: Optional[dict] = None
