import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ClashDetail(BaseModel):
    kind: str
    severity: str
    message: str
    other_request_id: Optional[uuid.UUID] = None
    other_schedule_item_id: Optional[uuid.UUID] = None


class RequestWithClashes(BaseModel):
    id: uuid.UUID
    course_code: str
    course_title: str
    department_name: str
    venue_code: str
    day: int
    start_period: int
    period_count: int
    status: str
    slot_label: str
    clashes: List[ClashDetail] = []


class DoubleBooking(BaseModel):
    venue: str
    day: int
    period: int
    subjects: List[str]


class ConflictStats(BaseModel):
    with_danger: int = 0
    warnings_only: int = 0
    double_bookings: int = 0


class ConflictResponse(BaseModel):
    requests: List[RequestWithClashes] = []
    stats: ConflictStats = ConflictStats()
    double_bookings: List[DoubleBooking] = []
