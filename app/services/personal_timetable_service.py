import csv
import io
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, course_cohorts
from app.models.master_timetable import MasterTimetable, MasterEntry
from app.models.registration import CourseRegistration, RegistrationStatus
from app.models.semester import Semester


DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _normalize_course_code(raw: str) -> str:
    cleaned = re.sub(r'\s*\([^)]*\)\s*$', '', raw.strip())
    return re.sub(r'\s+', '', cleaned).upper()


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

    async def _get_student_course_codes(
        self,
        user_id: uuid.UUID,
        programme_id: Optional[uuid.UUID],
        level: Optional[int],
        semester_id: uuid.UUID,
    ) -> List[str]:
        codes: List[str] = []

        reg_result = await self.db.execute(
            select(Course.code)
            .join(CourseRegistration, CourseRegistration.course_id == Course.id)
            .where(
                CourseRegistration.student_id == user_id,
                CourseRegistration.semester_id == semester_id,
                CourseRegistration.status == RegistrationStatus.REGISTERED,
            )
        )
        codes.extend(reg_result.scalars().all())

        custom_result = await self.db.execute(
            select(CourseRegistration.custom_course_code).where(
                CourseRegistration.student_id == user_id,
                CourseRegistration.semester_id == semester_id,
                CourseRegistration.status == RegistrationStatus.REGISTERED,
                CourseRegistration.course_id.is_(None),
                CourseRegistration.custom_course_code.isnot(None),
            )
        )
        codes.extend(custom_result.scalars().all())

        if programme_id and level:
            cohort_result = await self.db.execute(
                select(Course.code)
                .join(course_cohorts, course_cohorts.c.course_id == Course.id)
                .where(
                    course_cohorts.c.programme_id == programme_id,
                    course_cohorts.c.level == level,
                )
            )
            codes.extend(cohort_result.scalars().all())

        return list(set(codes))

    async def get_student_master_timetable(
        self,
        user_id: uuid.UUID,
        programme_id: Optional[uuid.UUID] = None,
        level: Optional[int] = None,
        student_category: Optional[str] = None,
        semester_id: Optional[uuid.UUID] = None,
        course_codes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        sid = await self._get_active_semester_id(semester_id)
        if not sid:
            return {"entries": [], "matched_courses": [], "unmatched_courses": [], "stats": {}}

        if course_codes:
            target_codes = course_codes
        else:
            target_codes = await self._get_student_course_codes(
                user_id, programme_id, level, sid,
            )

        if not target_codes:
            return {
                "entries": [],
                "matched_courses": [],
                "unmatched_courses": [],
                "stats": {"total_entries": 0, "weekly_classes": 0, "courses_found": 0},
            }

        category = None
        if student_category:
            category = student_category.lower()

        query = (
            select(MasterEntry)
            .join(MasterTimetable, MasterEntry.timetable_id == MasterTimetable.id)
            .where(MasterTimetable.semester_id == sid)
        )
        if category:
            query = query.where(MasterTimetable.category == category)
        query = query.order_by(MasterEntry.day, MasterEntry.period, MasterEntry.venue_code)

        result = await self.db.execute(query)
        all_entries = list(result.scalars().all())

        normalized_targets = {_normalize_course_code(c): c for c in target_codes}

        matched_entries: List[MasterEntry] = []
        matched_norm_codes: Set[str] = set()
        seen: Set[tuple] = set()
        for entry in all_entries:
            if entry.is_free:
                continue
            norm = _normalize_course_code(entry.subject)
            if norm in normalized_targets:
                key = (entry.subject, entry.day, entry.period, entry.venue_code)
                if key in seen:
                    continue
                seen.add(key)
                matched_entries.append(entry)
                matched_norm_codes.add(norm)

        matched_courses = sorted(
            {normalized_targets[n] for n in matched_norm_codes}
        )
        unmatched_courses = sorted(
            {c for c in target_codes if _normalize_course_code(c) not in matched_norm_codes}
        )

        today_idx = date.today().weekday()
        classes_today = sum(1 for e in matched_entries if e.day == today_idx)

        entries = []
        for entry in matched_entries:
            if entry.start_time and entry.end_time:
                period_start = entry.start_time
                period_end = entry.end_time
            else:
                h = 7 + entry.period
                period_start = f"{h:02d}:30"
                period_end = f"{h + 1:02d}:20"
            entries.append({
                "id": str(entry.id),
                "level": entry.level,
                "course_code": entry.subject,
                "subject": entry.subject,
                "day": entry.day,
                "day_name": DAY_NAMES[entry.day] if 0 <= entry.day < len(DAY_NAMES) else None,
                "period": entry.period,
                "period_start": period_start,
                "period_end": period_end,
                "venue_code": entry.venue_code,
                "is_free": entry.is_free,
                "course_kind": entry.course_kind,
                "source": "department" if entry.department_id else "master",
            })

        stats = {
            "total_entries": len(entries),
            "weekly_classes": len(entries),
            "classes_today": classes_today,
            "courses_found": len(matched_courses),
            "courses_not_found": len(unmatched_courses),
        }

        return {
            "entries": entries,
            "matched_courses": matched_courses,
            "unmatched_courses": unmatched_courses,
            "stats": stats,
        }

    async def export_student_master_csv(
        self,
        user_id: uuid.UUID,
        programme_id: Optional[uuid.UUID] = None,
        level: Optional[int] = None,
        student_category: Optional[str] = None,
        semester_id: Optional[uuid.UUID] = None,
        course_codes: Optional[List[str]] = None,
    ) -> str:
        data = await self.get_student_master_timetable(
            user_id, programme_id, level, student_category, semester_id, course_codes,
        )

        output = io.StringIO()
        headers = ["Day", "Time", "Course", "Venue", "Level", "Type"]
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        for entry in data["entries"]:
            day_idx = entry.get("day", 0)
            day_name = DAY_NAMES[day_idx] if 0 <= day_idx < len(DAY_NAMES) else str(day_idx)
            writer.writerow({
                "Day": day_name,
                "Time": f"{entry['period_start']}-{entry['period_end']}",
                "Course": entry.get("subject", ""),
                "Venue": entry.get("venue_code", ""),
                "Level": entry.get("level", ""),
                "Type": entry.get("course_kind", ""),
            })

        return output.getvalue()
