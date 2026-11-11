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
