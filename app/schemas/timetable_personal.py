import uuid
from typing import List, Optional

from pydantic import BaseModel


class MasterEntryItem(BaseModel):
    id: uuid.UUID
    level: int
    course_code: str
    subject: str
    day: int
    day_name: Optional[str] = None
    period: int
    period_start: str
    period_end: str
    venue_code: str
    is_free: bool = False
    course_kind: Optional[str] = None
    source: str = "master"


class VenueDetail(BaseModel):
    id: uuid.UUID
    code: Optional[str] = None
    building: str
    room_number: str
    location: Optional[str] = None
    capacity: Optional[int] = None
    type: Optional[str] = None


class MasterEntryDetailResponse(BaseModel):
    id: uuid.UUID
    level: int
    course_code: str
    subject: str
    day: int
    day_name: Optional[str] = None
    period: int
    period_start: str
    period_end: str
    venue_code: str
    is_free: bool = False
    course_kind: Optional[str] = None
    source: str = "master"

    course_id: Optional[uuid.UUID] = None
    course_title: Optional[str] = None
    course_type: Optional[str] = None
    course_mode: Optional[str] = None
    credit_hours: Optional[int] = None

    lecturer_id: Optional[uuid.UUID] = None
    lecturer_name: Optional[str] = None
    lecturer_email: Optional[str] = None
    lecturer_office: Optional[str] = None

    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    department_code: Optional[str] = None

    venue: Optional[VenueDetail] = None


class PersonalMasterStats(BaseModel):
    total_entries: int = 0
    weekly_classes: int = 0
    classes_today: int = 0
    courses_found: int = 0
    courses_not_found: int = 0


class PersonalMasterTimetableResponse(BaseModel):
    entries: List[MasterEntryItem] = []
    matched_courses: List[str] = []
    unmatched_courses: List[str] = []
    stats: PersonalMasterStats = PersonalMasterStats()
