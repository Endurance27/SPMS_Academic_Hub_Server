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
