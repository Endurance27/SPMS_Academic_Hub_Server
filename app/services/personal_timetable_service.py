import csv
import io
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.course import Course, course_cohorts
from app.models.department import Department
from app.models.registration import CourseRegistration, RegistrationStatus
from app.models.schedule_item import ScheduleItem, ScheduleItemStatus
from app.models.semester import Semester
from app.models.user import User, UserRole


WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


class PersonalTimetableService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_active_semester_id(self, semester_id: Optional[uuid.UUID] = None) -> Optional[uuid.UUID]:
        if semester_id:
            return semester_id
        result = await self.db.execute(
            select(Semester.id).where(Semester.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_lecturer_timetable(
        self,
        user_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        semester_id: Optional[uuid.UUID] = None,
        include_department: bool = False,
    ) -> Dict[str, Any]:
        sid = await self._get_active_semester_id(semester_id)
        if not sid:
            return {"items": [], "assessments": [], "stats": {}}

        today_idx = date.today().weekday()

        q = select(ScheduleItem).where(
            ScheduleItem.semester_id == sid,
            ScheduleItem.status == ScheduleItemStatus.PUBLISHED,
            ScheduleItem.lecturer_id == user_id,
        )
        result = await self.db.execute(q.order_by(ScheduleItem.day, ScheduleItem.start))
        items = list(result.scalars().all())

        if include_department and department_id:
            dept_q = select(ScheduleItem).where(
                ScheduleItem.semester_id == sid,
                ScheduleItem.status == ScheduleItemStatus.PUBLISHED,
                ScheduleItem.department_id == department_id,
                ScheduleItem.lecturer_id != user_id,
            )
            dept_result = await self.db.execute(dept_q.order_by(ScheduleItem.day, ScheduleItem.start))
            items.extend(dept_result.scalars().all())

        timetable_items = []
        classes_today = 0
        for item in items:
            course = (await self.db.execute(
                select(Course).where(Course.id == item.course_id)
            )).scalar_one_or_none()
            dept = (await self.db.execute(
                select(Department).where(Department.id == item.department_id)
            )).scalar_one_or_none()
            lecturer_name = None
            if item.lecturer_id:
                lec = (await self.db.execute(
                    select(User.name).where(User.id == item.lecturer_id)
                )).scalar()
                lecturer_name = lec

            if item.day == today_idx:
                classes_today += 1

            timetable_items.append({
                "id": str(item.id),
                "course_code": course.code if course else "",
                "course_title": course.title if course else "",
                "day": item.day,
                "start": item.start,
                "end": item.end,
                "venue_code": item.venue_code,
                "lecturer_name": lecturer_name,
                "mode": item.mode,
                "department_name": dept.name if dept else "",
                "tone": dept.tone.value if dept and dept.tone else None,
                "status": item.status.value if item.status else None,
                "groups": [],
                "assigned_to_me": item.lecturer_id == user_id,
            })

        course_ids = [item.course_id for item in items if item.lecturer_id == user_id]
        unique_course_ids = list(set(course_ids))

        assessments = await self._get_assessments(unique_course_ids, sid)
        upcoming_assessments = len(assessments)

        cohort_count = 0
        if unique_course_ids:
            cohort_count = (await self.db.execute(
                select(func.count()).select_from(course_cohorts).where(
                    course_cohorts.c.course_id.in_(unique_course_ids)
                )
            )).scalar() or 0

        own_classes_today = sum(1 for item in items if item.lecturer_id == user_id and item.day == today_idx)

        stats = {
            "weekly_classes": sum(1 for item in items if item.lecturer_id == user_id),
            "classes_today": own_classes_today,
            "upcoming_assessments": upcoming_assessments,
            "registered_courses": len(unique_course_ids),
            "teaching_groups": cohort_count,
        }

        return {
            "items": timetable_items,
            "assessments": assessments,
            "stats": stats,
        }

    async def get_student_timetable(
        self,
        user_id: uuid.UUID,
        programme_id: Optional[uuid.UUID] = None,
        level: Optional[int] = None,
        semester_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        sid = await self._get_active_semester_id(semester_id)
        if not sid:
            return {"items": [], "assessments": [], "stats": {}}

        today_idx = date.today().weekday()

        reg_result = await self.db.execute(
            select(CourseRegistration.course_id).where(
                CourseRegistration.student_id == user_id,
                CourseRegistration.semester_id == sid,
                CourseRegistration.status == RegistrationStatus.REGISTERED,
            )
        )
        registered_course_ids = list(reg_result.scalars().all())

        cohort_course_ids: List[uuid.UUID] = []
        if programme_id and level:
            cohort_result = await self.db.execute(
                select(course_cohorts.c.course_id).where(
                    course_cohorts.c.programme_id == programme_id,
                    course_cohorts.c.level == level,
                )
            )
            cohort_course_ids = list(cohort_result.scalars().all())

        all_course_ids = list(set(registered_course_ids + cohort_course_ids))
        if not all_course_ids:
            return {"items": [], "assessments": [], "stats": {"weekly_classes": 0, "classes_today": 0, "upcoming_assessments": 0, "registered_courses": 0, "teaching_groups": 0}}

        result = await self.db.execute(
            select(ScheduleItem).where(
                ScheduleItem.semester_id == sid,
                ScheduleItem.status == ScheduleItemStatus.PUBLISHED,
                ScheduleItem.course_id.in_(all_course_ids),
            ).order_by(ScheduleItem.day, ScheduleItem.start)
        )
        items = list(result.scalars().all())

        timetable_items = []
        classes_today = 0
        for item in items:
            course = (await self.db.execute(
                select(Course).where(Course.id == item.course_id)
            )).scalar_one_or_none()
            dept = (await self.db.execute(
                select(Department).where(Department.id == item.department_id)
            )).scalar_one_or_none()
            lecturer_name = "Lecturer to be assigned"
            if item.lecturer_id:
                lec = (await self.db.execute(
                    select(User.name).where(User.id == item.lecturer_id)
                )).scalar()
                lecturer_name = lec or lecturer_name

            if item.day == today_idx:
                classes_today += 1

            timetable_items.append({
                "id": str(item.id),
                "course_code": course.code if course else "",
                "course_title": course.title if course else "",
                "day": item.day,
                "start": item.start,
                "end": item.end,
                "venue_code": item.venue_code,
                "lecturer_name": lecturer_name,
                "mode": item.mode,
                "department_name": dept.name if dept else "",
                "tone": dept.tone.value if dept and dept.tone else None,
                "status": item.status.value if item.status else None,
                "groups": [],
                "assigned_to_me": False,
            })

        assessments = await self._get_assessments(all_course_ids, sid, student=True)

        stats = {
            "weekly_classes": len(items),
            "classes_today": classes_today,
            "upcoming_assessments": len(assessments),
            "registered_courses": len(registered_course_ids),
            "teaching_groups": 0,
        }

        return {
            "items": timetable_items,
            "assessments": assessments,
            "stats": stats,
        }

    async def _get_assessments(
        self,
        course_ids: List[uuid.UUID],
        semester_id: uuid.UUID,
        student: bool = False,
    ) -> List[Dict[str, Any]]:
        if not course_ids:
            return []

        statuses = [AssessmentStatus.UPCOMING, AssessmentStatus.SHARED]
        if not student:
            statuses.extend([AssessmentStatus.SUBMITTED, AssessmentStatus.DRAFT])

        result = await self.db.execute(
            select(Assessment).where(
                Assessment.course_id.in_(course_ids),
                Assessment.status.in_(statuses),
                Assessment.date >= datetime.now(timezone.utc),
            ).order_by(Assessment.date)
        )
        assessments = []
        for a in result.scalars().all():
            assessments.append({
                "id": str(a.id),
                "course_code": a.course_code,
                "course_title": a.course_title,
                "assessment_type": a.assessment_type.value if a.assessment_type else "",
                "date": a.date.isoformat() if a.date else None,
                "start_time": a.start_time,
                "end_time": a.end_time,
                "location": a.location,
                "status": a.status.value if a.status else "",
            })
        return assessments

    async def export_timetable_csv(
        self,
        user: Any,
        semester_id: Optional[uuid.UUID] = None,
    ) -> str:
        if user.role == UserRole.LECTURER:
            data = await self.get_lecturer_timetable(
                user.id, user.department_id, semester_id
            )
        else:
            data = await self.get_student_timetable(
                user.id, user.programme_id, user.level, semester_id
            )

        output = io.StringIO()
        headers = ["Day", "Start", "End", "Course", "Title", "Venue", "Lecturer", "Mode"]
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        for item in data["items"]:
            day_idx = item.get("day", 0)
            day_name = WEEKDAYS[day_idx] if 0 <= day_idx < len(WEEKDAYS) else str(day_idx)
            writer.writerow({
                "Day": day_name,
                "Start": item.get("start", ""),
                "End": item.get("end", ""),
                "Course": item.get("course_code", ""),
                "Title": item.get("course_title", ""),
                "Venue": item.get("venue_code", ""),
                "Lecturer": item.get("lecturer_name", ""),
                "Mode": item.get("mode", ""),
            })

        return output.getvalue()
