import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TimetableItem(BaseModel):
    id: uuid.UUID
    course_code: str
    course_title: str
    day: int
    start: Optional[str] = None
    end: Optional[str] = None
    venue_code: str
    lecturer_name: Optional[str] = None
    mode: Optional[str] = None
    department_name: Optional[str] = None
    tone: Optional[str] = None
    status: Optional[str] = None
    groups: List[str] = []
    assigned_to_me: bool = False


class PersonalAssessment(BaseModel):
    id: uuid.UUID
    course_code: str
    course_title: str
    assessment_type: str
    date: Optional[datetime] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    status: str


class TimetableStats(BaseModel):
    weekly_classes: int = 0
    classes_today: int = 0
    upcoming_assessments: int = 0
    registered_courses: int = 0
    teaching_groups: int = 0


class PersonalTimetableResponse(BaseModel):
    items: List[TimetableItem] = []
    assessments: List[PersonalAssessment] = []
    stats: TimetableStats = TimetableStats()
