import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.attendance import AttendanceRecord, AttendanceRecordStatus, AttendanceSession, AttendanceStatus
from app.models.course import Course, course_cohorts
from app.models.department import Department
from app.models.graduation import GraduationSubmission, GraduationStatus
from app.models.master_timetable import MasterEntry
from app.models.registration import CourseRegistration, RegistrationStatus
from app.models.schedule_item import ScheduleItem, ScheduleItemStatus
from app.models.semester import Semester
from app.models.slot_request import SlotRequest, SlotRequestStatus
from app.models.user import User, UserRole, UserStatus
from app.models.venue import Venue


WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PERIODS = [
    {"index": i, "start": f"{7+i:02d}:30", "end": f"{8+i:02d}:20"}
    for i in range(12)
]


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_active_semester(self) -> Optional[Any]:
        result = await self.db.execute(
            select(Semester).where(Semester.is_active == True)
        )
        return result.scalar_one_or_none()

    async def _today_weekday_index(self) -> int:
        today = date.today()
        return today.weekday()

    async def get_super_dashboard(self) -> Dict[str, Any]:
        semester = await self._get_active_semester()
        today_idx = await self._today_weekday_index()

        dept_count = (await self.db.execute(
            select(func.count()).select_from(Department)
        )).scalar() or 0

        faculty_count = (await self.db.execute(
            select(func.count()).select_from(User).where(User.role == UserRole.LECTURER)
        )).scalar() or 0

        venue_count = (await self.db.execute(
            select(func.count()).select_from(Venue)
        )).scalar() or 0

        assessment_count = 0
        pending_approvals = 0
        free_cells = 0
        open_slots = 0
        open_conflicts = 0
        sessions_today = 0
        live_sessions = 0
        assessments_today = 0
        ready_to_publish = 0
        departments_not_submitted: List[Dict[str, Any]] = []
        submission_window_closes_in_days: Optional[int] = None
        next_sessions: List[Dict[str, Any]] = []

        if semester:
            sid = semester.id

            assessment_count = (await self.db.execute(
                select(func.count()).select_from(Assessment).where(
                    Assessment.status.notin_([AssessmentStatus.CANCELLED, AssessmentStatus.DRAFT])
                )
            )).scalar() or 0

            pending_approvals = (await self.db.execute(
                select(func.count()).select_from(SlotRequest).where(
                    SlotRequest.semester_id == sid,
                    SlotRequest.status == SlotRequestStatus.PENDING,
                )
            )).scalar() or 0

            free_cells = (await self.db.execute(
                select(func.count()).select_from(MasterEntry).where(
                    MasterEntry.is_free == True,
                    MasterEntry.timetable_id.in_(
                        select(MasterEntry.timetable_id).join(
                            MasterEntry.timetable
                        ).where(MasterEntry.timetable.has(semester_id=sid))
                    )
                )
            )).scalar() or 0

            open_slots = (await self.db.execute(
                select(func.count()).select_from(SlotRequest).where(
                    SlotRequest.semester_id == sid,
                    SlotRequest.status.in_([SlotRequestStatus.PENDING, SlotRequestStatus.APPROVED]),
                )
            )).scalar() or 0

            open_conflicts = (await self.db.execute(
                select(func.count()).select_from(ScheduleItem).where(
                    ScheduleItem.semester_id == sid,
                    ScheduleItem.status == ScheduleItemStatus.CONFLICT,
                )
            )).scalar() or 0

            today = date.today()
            sessions_today = (await self.db.execute(
                select(func.count()).select_from(AttendanceSession).where(
                    func.date(AttendanceSession.date) == today
                )
            )).scalar() or 0

            live_sessions = (await self.db.execute(
                select(func.count()).select_from(AttendanceSession).where(
                    AttendanceSession.status == AttendanceStatus.LIVE
                )
            )).scalar() or 0

            assessments_today = (await self.db.execute(
                select(func.count()).select_from(Assessment).where(
                    func.date(Assessment.date) == today,
                    Assessment.status.in_([AssessmentStatus.UPCOMING, AssessmentStatus.SHARED]),
                )
            )).scalar() or 0

            ready_to_publish = (await self.db.execute(
                select(func.count()).select_from(ScheduleItem).where(
                    ScheduleItem.semester_id == sid,
                    ScheduleItem.status == ScheduleItemStatus.PENDING,
                )
            )).scalar() or 0

            submitted_dept_ids_q = select(GraduationSubmission.department_id).where(
                GraduationSubmission.academic_year == semester.academic_year,
                GraduationSubmission.status.in_([GraduationStatus.SUBMITTED, GraduationStatus.VALIDATED]),
            ).distinct()
            not_submitted_result = await self.db.execute(
                select(Department.id, Department.name, Department.code).where(
                    Department.id.notin_(submitted_dept_ids_q)
                )
            )
            departments_not_submitted = [
                {"id": str(r.id), "name": r.name, "code": r.code}
                for r in not_submitted_result.all()
            ]

            if semester.graduation_deadline:
                dl = semester.graduation_deadline
                if hasattr(dl, 'date'):
                    dl = dl.date() if callable(dl.date) else dl
                days_left = (dl - datetime.now(timezone.utc)).days if isinstance(dl, datetime) else None
                submission_window_closes_in_days = max(0, days_left) if days_left is not None else None

            next_items_result = await self.db.execute(
                select(ScheduleItem).where(
                    ScheduleItem.semester_id == sid,
                    ScheduleItem.status == ScheduleItemStatus.PUBLISHED,
                    ScheduleItem.day >= today_idx,
                ).order_by(ScheduleItem.day, ScheduleItem.start).limit(3)
            )
            for item in next_items_result.scalars().all():
                course = (await self.db.execute(
                    select(Course.code, Course.title).where(Course.id == item.course_id)
                )).first()
                next_sessions.append({
                    "id": str(item.id),
                    "course_code": course.code if course else "",
                    "course_title": course.title if course else "",
                    "venue_code": item.venue_code,
                    "day": item.day,
                    "start": item.start,
                    "end": item.end,
                })

        return {
            "departments": dept_count,
            "faculty": faculty_count,
            "assessments": assessment_count,
            "venues": venue_count,
            "open_slots": open_slots,
            "free_cells": free_cells,
            "pending_approvals": pending_approvals,
            "open_conflicts": open_conflicts,
            "sessions_today": sessions_today,
            "live_sessions": live_sessions,
            "assessments_today": assessments_today,
            "ready_to_publish": ready_to_publish,
            "departments_not_submitted": departments_not_submitted,
            "submission_window_closes_in_days": submission_window_closes_in_days,
            "next_sessions": next_sessions,
        }

    async def get_department_dashboard(self, department_id: uuid.UUID) -> Dict[str, Any]:
        semester = await self._get_active_semester()

        course_offerings = (await self.db.execute(
            select(func.count()).select_from(Course).where(Course.department_id == department_id)
        )).scalar() or 0

        faculty_count = (await self.db.execute(
            select(func.count()).select_from(User).where(
                User.department_id == department_id,
                User.role == UserRole.LECTURER,
            )
        )).scalar() or 0

        active_students = (await self.db.execute(
            select(func.count()).select_from(User).where(
                User.department_id == department_id,
                User.role == UserRole.STUDENT,
                User.status == UserStatus.ACTIVE,
            )
        )).scalar() or 0

        schedule_requests = 0
        central_slots_available = 0
        submission_window_closes_in_days: Optional[int] = None
        attention: List[Dict[str, str]] = []

        if semester:
            sid = semester.id

            schedule_requests = (await self.db.execute(
                select(func.count()).select_from(SlotRequest).where(
                    SlotRequest.semester_id == sid,
                    SlotRequest.department_id == department_id,
                    SlotRequest.status.in_([SlotRequestStatus.PENDING, SlotRequestStatus.APPROVED]),
                )
            )).scalar() or 0

            central_slots_available = (await self.db.execute(
                select(func.count()).select_from(MasterEntry).where(
                    MasterEntry.is_free == True,
                    MasterEntry.timetable_id.in_(
                        select(MasterEntry.timetable_id).join(
                            MasterEntry.timetable
                        ).where(MasterEntry.timetable.has(semester_id=sid))
                    )
                )
            )).scalar() or 0

            if semester.graduation_deadline:
                dl = semester.graduation_deadline
                days_left = (dl - datetime.now(timezone.utc)).days if isinstance(dl, datetime) else None
                submission_window_closes_in_days = max(0, days_left) if days_left is not None else None

            courses_without_lecturer = (await self.db.execute(
                select(func.count()).select_from(Course).where(
                    Course.department_id == department_id,
                    Course.lecturer_id == None,
                )
            )).scalar() or 0
            if courses_without_lecturer > 0:
                attention.append({
                    "title": f"{courses_without_lecturer} course(s) without lecturer",
                    "detail": "Assign lecturers to all courses for scheduling.",
                    "page": "Programmes & courses",
                })

            pending_invitations = (await self.db.execute(
                select(func.count()).select_from(User).where(
                    User.department_id == department_id,
                    User.status == UserStatus.INVITED,
                )
            )).scalar() or 0
            if pending_invitations > 0:
                attention.append({
                    "title": f"{pending_invitations} pending invitation(s)",
                    "detail": "Users who haven't accepted their invitations.",
                    "page": "Faculty",
                })

        assigned_courses = (await self.db.execute(
            select(func.count()).select_from(Course).where(
                Course.department_id == department_id,
                Course.lecturer_id != None,
            )
        )).scalar() or 0

        readiness = {
            "offerings_assigned": {"done": assigned_courses, "total": course_offerings},
            "faculty_coverage": round(assigned_courses / course_offerings * 100, 1) if course_offerings > 0 else 0.0,
            "student_groups_mapped": 0,
            "venue_slots_confirmed": schedule_requests,
            "percent": round(assigned_courses / max(course_offerings, 1) * 100, 1),
        }

        return {
            "course_offerings": course_offerings,
            "faculty": faculty_count,
            "active_students": active_students,
            "schedule_requests": schedule_requests,
            "readiness": readiness,
            "central_slots_available": central_slots_available,
            "submission_window_closes_in_days": submission_window_closes_in_days,
            "attention": attention,
        }

    async def get_lecturer_dashboard(self, user_id: uuid.UUID) -> Dict[str, Any]:
        semester = await self._get_active_semester()
        today_idx = await self._today_weekday_index()
        today = date.today()

        assigned_courses = (await self.db.execute(
            select(func.count()).select_from(Course).where(Course.lecturer_id == user_id)
        )).scalar() or 0

        classes_today = 0
        today_timeline: List[Dict[str, Any]] = []
        contact_hours = 0.0
        teaching_groups = 0
        next_session_starts_in_minutes: Optional[int] = None

        if semester:
            sid = semester.id

            classes_today_result = await self.db.execute(
                select(ScheduleItem).where(
                    ScheduleItem.semester_id == sid,
                    ScheduleItem.lecturer_id == user_id,
                    ScheduleItem.status == ScheduleItemStatus.PUBLISHED,
                    ScheduleItem.day == today_idx,
                ).order_by(ScheduleItem.start)
            )
            today_items = classes_today_result.scalars().all()
            classes_today = len(today_items)

            for item in today_items:
                course = (await self.db.execute(
                    select(Course.code, Course.title).where(Course.id == item.course_id)
                )).first()
                today_timeline.append({
                    "id": str(item.id),
                    "course_code": course.code if course else "",
                    "course_title": course.title if course else "",
                    "venue_code": item.venue_code,
                    "start": item.start,
                    "end": item.end,
                    "status": item.status.value if item.status else None,
                })

            all_items_result = await self.db.execute(
                select(ScheduleItem).where(
                    ScheduleItem.semester_id == sid,
                    ScheduleItem.lecturer_id == user_id,
                    ScheduleItem.status == ScheduleItemStatus.PUBLISHED,
                )
            )
            all_items = all_items_result.scalars().all()
            for item in all_items:
                if item.start and item.end:
                    try:
                        sh, sm = map(int, item.start.split(":"))
                        eh, em = map(int, item.end.split(":"))
                        contact_hours += (eh * 60 + em - sh * 60 - sm) / 60
                    except (ValueError, AttributeError):
                        pass

        students_reached = 0
        course_ids_result = await self.db.execute(
            select(Course.id).where(Course.lecturer_id == user_id)
        )
        course_ids = [r[0] for r in course_ids_result.all()]

        if course_ids:
            students_reached = (await self.db.execute(
                select(func.count(func.distinct(CourseRegistration.student_id))).where(
                    CourseRegistration.course_id.in_(course_ids),
                    CourseRegistration.status == RegistrationStatus.REGISTERED,
                )
            )).scalar() or 0

        total_records = 0
        present_late = 0
        late_count = 0
        absent_count = 0
        if course_ids:
            total_records = (await self.db.execute(
                select(func.count()).select_from(AttendanceRecord).where(
                    AttendanceRecord.course_id.in_(course_ids)
                )
            )).scalar() or 0
            present_late = (await self.db.execute(
                select(func.count()).select_from(AttendanceRecord).where(
                    AttendanceRecord.course_id.in_(course_ids),
                    AttendanceRecord.status.in_([AttendanceRecordStatus.PRESENT, AttendanceRecordStatus.LATE]),
                )
            )).scalar() or 0
            late_count = (await self.db.execute(
                select(func.count()).select_from(AttendanceRecord).where(
                    AttendanceRecord.course_id.in_(course_ids),
                    AttendanceRecord.status == AttendanceRecordStatus.LATE,
                )
            )).scalar() or 0
            absent_count = (await self.db.execute(
                select(func.count()).select_from(AttendanceRecord).where(
                    AttendanceRecord.course_id.in_(course_ids),
                    AttendanceRecord.status == AttendanceRecordStatus.ABSENT,
                )
            )).scalar() or 0

        attendance_rate = round(present_late / total_records * 100, 1) if total_records > 0 else 0.0
        attendance_health = {
            "rate": attendance_rate,
            "check_ins": present_late,
            "expected": total_records,
            "late": late_count,
            "absent": absent_count,
        }

        recent_registers: List[Dict[str, Any]] = []
        if course_ids:
            recent_sessions_result = await self.db.execute(
                select(AttendanceSession).where(
                    AttendanceSession.course_id.in_(course_ids),
                    AttendanceSession.status == AttendanceStatus.COMPLETED,
                ).order_by(AttendanceSession.date.desc()).limit(5)
            )
            for session in recent_sessions_result.scalars().all():
                course = (await self.db.execute(
                    select(Course.code).where(Course.id == session.course_id)
                )).scalar()
                present_count = (await self.db.execute(
                    select(func.count()).select_from(AttendanceRecord).where(
                        AttendanceRecord.session_id == session.id,
                        AttendanceRecord.status.in_([AttendanceRecordStatus.PRESENT, AttendanceRecordStatus.LATE]),
                    )
                )).scalar() or 0
                expected = session.expected_count or 0
                recent_registers.append({
                    "course": course or "",
                    "present": present_count,
                    "expected": expected,
                    "rate": round(present_count / expected * 100, 1) if expected > 0 else 0.0,
                })

        workload_percent = round(contact_hours / 25 * 100, 1)

        return {
            "classes_today": classes_today,
            "assigned_courses": assigned_courses,
            "students_reached": students_reached,
            "attendance_rate": attendance_rate,
            "attendance_trend": [],
            "today_timeline": today_timeline,
            "contact_hours": round(contact_hours, 1),
            "workload_percent": workload_percent,
            "teaching_groups": teaching_groups,
            "recent_registers": recent_registers,
            "attendance_health": attendance_health,
            "next_session_starts_in_minutes": next_session_starts_in_minutes,
        }

    async def get_student_dashboard(self, user_id: uuid.UUID, programme_id: Optional[uuid.UUID] = None, level: Optional[int] = None) -> Dict[str, Any]:
        semester = await self._get_active_semester()
        today_idx = await self._today_weekday_index()
        today = date.today()

        registered_courses = 0
        assessments_soon = 0
        classes_today = 0
        today_items: List[Dict[str, Any]] = []
        attendance_rate = 0.0

        if semester:
            sid = semester.id

            registered_courses = (await self.db.execute(
                select(func.count()).select_from(CourseRegistration).where(
                    CourseRegistration.student_id == user_id,
                    CourseRegistration.semester_id == sid,
                    CourseRegistration.status == RegistrationStatus.REGISTERED,
                )
            )).scalar() or 0

            assessments_soon = (await self.db.execute(
                select(func.count()).select_from(Assessment).where(
                    Assessment.status.in_([AssessmentStatus.UPCOMING, AssessmentStatus.SHARED]),
                    Assessment.date >= datetime.now(timezone.utc),
                    Assessment.date <= datetime.now(timezone.utc) + timedelta(days=7),
                )
            )).scalar() or 0

            reg_course_ids = (await self.db.execute(
                select(CourseRegistration.course_id).where(
                    CourseRegistration.student_id == user_id,
                    CourseRegistration.semester_id == sid,
                    CourseRegistration.status == RegistrationStatus.REGISTERED,
                )
            )).scalars().all()

            if reg_course_ids:
                today_result = await self.db.execute(
                    select(ScheduleItem).where(
                        ScheduleItem.semester_id == sid,
                        ScheduleItem.status == ScheduleItemStatus.PUBLISHED,
                        ScheduleItem.day == today_idx,
                        ScheduleItem.course_id.in_(reg_course_ids),
                    ).order_by(ScheduleItem.start)
                )
                for item in today_result.scalars().all():
                    course = (await self.db.execute(
                        select(Course.code, Course.title).where(Course.id == item.course_id)
                    )).first()
                    today_items.append({
                        "id": str(item.id),
                        "course_code": course.code if course else "",
                        "course_title": course.title if course else "",
                        "venue_code": item.venue_code,
                        "start": item.start,
                        "end": item.end,
                        "status": item.status.value if item.status else None,
                    })
                classes_today = len(today_items)

                total_att = (await self.db.execute(
                    select(func.count()).select_from(AttendanceRecord).where(
                        AttendanceRecord.student_id == user_id,
                        AttendanceRecord.course_id.in_(reg_course_ids),
                    )
                )).scalar() or 0
                present_att = (await self.db.execute(
                    select(func.count()).select_from(AttendanceRecord).where(
                        AttendanceRecord.student_id == user_id,
                        AttendanceRecord.course_id.in_(reg_course_ids),
                        AttendanceRecord.status.in_([AttendanceRecordStatus.PRESENT, AttendanceRecordStatus.LATE]),
                    )
                )).scalar() or 0
                attendance_rate = round(present_att / total_att * 100, 1) if total_att > 0 else 0.0

        return {
            "classes_today": classes_today,
            "registered_courses": registered_courses,
            "assessments_soon": assessments_soon,
            "attendance_rate": attendance_rate,
            "today": today_items,
        }

    async def get_badges(self, user: Any) -> Dict[str, int]:
        semester = await self._get_active_semester()
        approvals = 0
        conflict_centre = 0
        schedule_requests = 0

        if semester:
            sid = semester.id

            if user.role in (UserRole.SUPER,):
                approvals = (await self.db.execute(
                    select(func.count()).select_from(SlotRequest).where(
                        SlotRequest.semester_id == sid,
                        SlotRequest.status == SlotRequestStatus.PENDING,
                    )
                )).scalar() or 0

                conflict_centre = (await self.db.execute(
                    select(func.count()).select_from(ScheduleItem).where(
                        ScheduleItem.semester_id == sid,
                        ScheduleItem.status == ScheduleItemStatus.CONFLICT,
                    )
                )).scalar() or 0

            if user.role in (UserRole.SUPER, UserRole.DEPARTMENT):
                dept_filter = []
                if user.role == UserRole.DEPARTMENT and user.department_id:
                    dept_filter.append(SlotRequest.department_id == user.department_id)

                q = select(func.count()).select_from(SlotRequest).where(
                    SlotRequest.semester_id == sid,
                    SlotRequest.status.in_([SlotRequestStatus.PENDING, SlotRequestStatus.APPROVED]),
                    *dept_filter,
                )
                schedule_requests = (await self.db.execute(q)).scalar() or 0

        return {
            "approvals": approvals,
            "conflict_centre": conflict_centre,
            "schedule_requests": schedule_requests,
        }
