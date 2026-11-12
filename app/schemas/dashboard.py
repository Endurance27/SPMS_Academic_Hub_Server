import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AttentionItem(BaseModel):
    title: str
    detail: str
    page: str


class ReadinessMetrics(BaseModel):
    offerings_assigned: Dict[str, int]
    faculty_coverage: float
    student_groups_mapped: int
    venue_slots_confirmed: int
    percent: float


class RecentRegister(BaseModel):
    course: str
    present: int
    expected: int
    rate: float


class AttendanceHealth(BaseModel):
    rate: float
    check_ins: int
    expected: int
    late: int
    absent: int


class ScheduleItemSummary(BaseModel):
    id: uuid.UUID
    course_code: str
    course_title: str
    venue_code: str
    day: int
    start: Optional[str] = None
    end: Optional[str] = None

    class Config:
        from_attributes = True


class TodayTimelineItem(BaseModel):
    id: uuid.UUID
    course_code: str
    course_title: str
    venue_code: str
    start: Optional[str] = None
    end: Optional[str] = None
    status: Optional[str] = None


class SuperDashboardResponse(BaseModel):
    departments: int = 0
    faculty: int = 0
    assessments: int = 0
    venues: int = 0
    open_slots: int = 0
    free_cells: int = 0
    pending_approvals: int = 0
    open_conflicts: int = 0
    sessions_today: int = 0
    live_sessions: int = 0
    assessments_today: int = 0
    ready_to_publish: int = 0
    departments_not_submitted: List[Dict[str, Any]] = []
    submission_window_closes_in_days: Optional[int] = None
    next_sessions: List[ScheduleItemSummary] = []


class DepartmentDashboardResponse(BaseModel):
    course_offerings: int = 0
    faculty: int = 0
    active_students: int = 0
    schedule_requests: int = 0
    readiness: Optional[ReadinessMetrics] = None
    central_slots_available: int = 0
    submission_window_closes_in_days: Optional[int] = None
    attention: List[AttentionItem] = []


class LecturerDashboardResponse(BaseModel):
    classes_today: int = 0
    assigned_courses: int = 0
    students_reached: int = 0
    attendance_rate: float = 0.0
    attendance_trend: List[float] = []
    today_timeline: List[TodayTimelineItem] = []
    contact_hours: float = 0.0
    workload_percent: float = 0.0
    teaching_groups: int = 0
    recent_registers: List[RecentRegister] = []
    attendance_health: Optional[AttendanceHealth] = None
    next_session_starts_in_minutes: Optional[int] = None


class StudentDashboardResponse(BaseModel):
    classes_today: int = 0
    registered_courses: int = 0
    assessments_soon: int = 0
    attendance_rate: float = 0.0
    today: List[TodayTimelineItem] = []


class BadgesResponse(BaseModel):
    approvals: int = 0
    conflict_centre: int = 0
    schedule_requests: int = 0
