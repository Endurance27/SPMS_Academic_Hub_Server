import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.registration import RegistrationStatus, RegistrationType


class RegistrationCreate(BaseModel):
    course_id: Optional[uuid.UUID] = None
    custom_course_code: Optional[str] = Field(None, max_length=50)
    custom_course_title: Optional[str] = Field(None, max_length=255)
    semester_id: uuid.UUID
    level: int = Field(..., ge=100)
    registration_type: RegistrationType
    credits: int = Field(..., ge=1, le=6)


class RegistrationResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: Optional[uuid.UUID] = None
    course_code: Optional[str] = None
    course_title: Optional[str] = None
    custom_course_code: Optional[str] = None
    custom_course_title: Optional[str] = None
    semester_id: uuid.UUID
    level: int
    registration_type: RegistrationType
    credits: int
    status: RegistrationStatus
    source: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RegistrationListResponse(BaseModel):
    data: List[RegistrationResponse]
    meta: Optional[dict] = None


class RegistrationTimetableEntry(BaseModel):
    id: uuid.UUID
    day: int
    day_name: Optional[str] = None
    period: int
    period_start: str
    period_end: str
    venue_code: str
    course_kind: Optional[str] = None
    source: str = "master"


class RegistrationDetailResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: Optional[uuid.UUID] = None
    course_code: Optional[str] = None
    course_title: Optional[str] = None
    custom_course_code: Optional[str] = None
    custom_course_title: Optional[str] = None
    semester_id: uuid.UUID
    level: int
    registration_type: RegistrationType
    credits: int
    status: RegistrationStatus
    source: Optional[str] = None
    created_at: datetime

    course_type: Optional[str] = None
    course_mode: Optional[str] = None
    credit_hours: Optional[int] = None
    student_count: Optional[int] = None

    lecturer_id: Optional[uuid.UUID] = None
    lecturer_name: Optional[str] = None
    lecturer_email: Optional[str] = None
    lecturer_office: Optional[str] = None

    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    department_code: Optional[str] = None

    cohorts: List[dict] = []
    timetable_entries: List[RegistrationTimetableEntry] = []

    class Config:
        from_attributes = True


class CatalogueCourseResponse(BaseModel):
    id: uuid.UUID
    code: str
    title: str
    department_id: uuid.UUID
    department_name: Optional[str] = None
    course_type: str
    credit_hours: int
    mode: str
    lecturer_name: Optional[str] = None
    is_programme_match: bool = False

    class Config:
        from_attributes = True


class CatalogueListResponse(BaseModel):
    data: List[CatalogueCourseResponse]
    meta: Optional[dict] = None
