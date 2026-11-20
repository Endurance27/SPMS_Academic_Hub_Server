from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, Field


class ScheduleItemCreate(BaseModel):
    semester_id: UUID
    course_id: UUID
    day: int = Field(..., ge=0, le=4)
    start: Optional[str] = None
    end: Optional[str] = None
    start_period: Optional[int] = None
    period_count: Optional[int] = Field(None, ge=1, le=3)
    venue_code: str
    lecturer_id: Optional[UUID] = None
    mode: str = "in-person"
    meeting_link: Optional[str] = Field(None, max_length=2048)
    groups: List[dict] = []


class ScheduleItemUpdate(BaseModel):
    day: Optional[int] = Field(None, ge=0, le=4)
    start: Optional[str] = None
    end: Optional[str] = None
    start_period: Optional[int] = None
    period_count: Optional[int] = Field(None, ge=1, le=3)
    venue_code: Optional[str] = None
    lecturer_id: Optional[UUID] = None
    mode: Optional[str] = None
    meeting_link: Optional[str] = Field(None, max_length=2048)
    groups: Optional[List[dict]] = None


class ScheduleItemResponse(BaseModel):
    id: UUID
    semester_id: UUID
    course_id: UUID
    department_id: UUID
    day: int
    start_period: Optional[int]
    period_count: Optional[int]
    start: Optional[str]
    end: Optional[str]
    venue_code: str
    lecturer_id: Optional[UUID]
    mode: str
    meeting_link: Optional[str] = None
    status: str
    source: str

    class Config:
        from_attributes = True


class ScheduleItemListResponse(BaseModel):
    data: List[ScheduleItemResponse]
    meta: dict
