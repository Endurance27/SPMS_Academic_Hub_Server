import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.user import StudentCategory, UserStatus


class StudentResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    student_number: Optional[str] = None
    programme_id: Optional[uuid.UUID] = None
    programme_name: Optional[str] = None
    level: Optional[int] = None
    student_category: Optional[StudentCategory] = None
    status: UserStatus
    created_at: datetime

    class Config:
        from_attributes = True


class CohortResponse(BaseModel):
    programme_id: uuid.UUID
    programme_name: str
    level: int
    student_count: int


class StudentListResponse(BaseModel):
    data: List[StudentResponse]
    meta: Optional[dict] = None


class CohortListResponse(BaseModel):
    data: List[CohortResponse]
    meta: Optional[dict] = None
