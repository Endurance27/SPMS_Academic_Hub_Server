import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SectionCreate(BaseModel):
    programme_id: uuid.UUID
    level: int = Field(..., ge=100)
    name: str = Field(..., min_length=1, max_length=100)
    course_id: Optional[uuid.UUID] = None
    student_ids: Optional[List[uuid.UUID]] = []


class SectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    student_ids: Optional[List[uuid.UUID]] = None


class SectionResponse(BaseModel):
    id: uuid.UUID
    programme_id: uuid.UUID
    level: int
    name: str
    course_id: Optional[uuid.UUID] = None
    student_ids: List[uuid.UUID] = []
    student_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SectionListResponse(BaseModel):
    data: List[SectionResponse]
    meta: Optional[dict] = None
