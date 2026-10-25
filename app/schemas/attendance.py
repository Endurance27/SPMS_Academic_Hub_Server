from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class AttendanceSessionCreate(BaseModel):
    course_id: UUID
    schedule_item_id: Optional[UUID] = None
    date: str
    start_time: str
    end_time: str
    venue_code: Optional[str] = None


class AttendanceRecordCreate(BaseModel):
    session_id: Optional[UUID] = None
    course_id: Optional[UUID] = None
    session_date: Optional[str] = None
    student_id: UUID
    status: str = "Present"
    note: Optional[str] = None


class AttendanceSessionResponse(BaseModel):
    id: UUID
    course_id: UUID
    schedule_item_id: Optional[UUID]
    lecturer_id: UUID
    date: str
    start_time: str
    end_time: str
    venue_code: Optional[str]
    status: str
    opened_at: Optional[datetime]
    closed_at: Optional[datetime]
    expected_count: int
    present_count: int = 0
    late_count: int = 0
    absent_count: int = 0
    excused_count: int = 0
    rate: float = 0.0

    class Config:
        from_attributes = True


class AttendanceRecordResponse(BaseModel):
    id: UUID
    session_id: UUID
    course_id: UUID
    student_id: UUID
    status: str
    source: str
    recorded_at: datetime
    note: Optional[str]

    class Config:
        from_attributes = True


class AttendanceSessionListResponse(BaseModel):
    data: list[AttendanceSessionResponse]
    meta: dict
