import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, course_cohorts
from app.models.department import Department
from app.models.master_timetable import MasterEntry, MasterTimetable
from app.models.schedule_item import ScheduleItem, ScheduleItemStatus
from app.models.semester import Semester
from app.models.slot_request import SlotRequest, SlotRequestStatus
from app.models.user import User
from app.models.venue import Venue


WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PERIODS = [
    {"index": i, "start": f"{7+i:02d}:30", "end": f"{8+i:02d}:20"}
    for i in range(12)
]


def _overlaps(a_start: int, a_count: int, b_start: int, b_count: int) -> bool:
    return a_start < b_start + b_count and b_start < a_start + a_count


def _slot_label(day: int, start_period: int, period_count: int) -> str:
    day_name = WEEKDAYS[day] if 0 <= day < len(WEEKDAYS) else str(day)
    start = PERIODS[start_period]["start"] if 0 <= start_period < len(PERIODS) else "?"
    end_idx = start_period + period_count - 1
    end = PERIODS[end_idx]["end"] if 0 <= end_idx < len(PERIODS) else "?"
    return f"{day_name} {start}–{end}"


class ConflictService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_conflicts(self, semester_id: uuid.UUID) -> Dict[str, Any]:
        requests_result = await self.db.execute(
            select(SlotRequest).where(
                SlotRequest.semester_id == semester_id,
                SlotRequest.status.in_([SlotRequestStatus.PENDING, SlotRequestStatus.APPROVED]),
            ).order_by(SlotRequest.day, SlotRequest.start_period)
        )
        requests = list(requests_result.scalars().all())

        conflict_items_result = await self.db.execute(
            select(ScheduleItem).where(
                ScheduleItem.semester_id == semester_id,
                ScheduleItem.status == ScheduleItemStatus.CONFLICT,
            )
        )
        conflict_items = list(conflict_items_result.scalars().all())

        free_cells = set()
        timetables_result = await self.db.execute(
            select(MasterTimetable).where(MasterTimetable.semester_id == semester_id)
        )
        for tt in timetables_result.scalars().all():
            entries_result = await self.db.execute(
                select(MasterEntry).where(
                    MasterEntry.timetable_id == tt.id,
                    MasterEntry.is_free == True,
                )
            )
            for e in entries_result.scalars().all():
                free_cells.add(f"{e.day}|{e.period}|{e.venue_code}")

        requests_with_clashes: List[Dict[str, Any]] = []
        with_danger = 0
        warnings_only_count = 0

        for req in requests:
            clashes: List[Dict[str, Any]] = []

            course = (await self.db.execute(
                select(Course).where(Course.id == req.course_id)
            )).scalar_one_or_none()
            dept = (await self.db.execute(
                select(Department).where(Department.id == req.department_id)
            )).scalar_one_or_none()

            for p in range(req.start_period, req.start_period + req.period_count):
                key = f"{req.day}|{p}|{req.venue_code}"
                if key not in free_cells:
                    clashes.append({
                        "kind": "not-free",
                        "severity": "danger",
                        "message": f"{req.venue_code} is not FREE for {_slot_label(req.day, req.start_period, req.period_count)} in the active master timetable.",
                    })
                    break

            for other in requests:
                if other.id == req.id:
                    continue
                if other.day != req.day:
                    continue
                if not _overlaps(req.start_period, req.period_count, other.start_period, other.period_count):
                    continue

                other_course = (await self.db.execute(
                    select(Course).where(Course.id == other.course_id)
                )).scalar_one_or_none()
                other_dept = (await self.db.execute(
                    select(Department).where(Department.id == other.department_id)
                )).scalar_one_or_none()

                if other.venue_code == req.venue_code:
                    if other.status == SlotRequestStatus.APPROVED:
                        clashes.append({
                            "kind": "venue-taken",
                            "severity": "danger",
                            "message": f"{req.venue_code} is already allocated to {other_course.code if other_course else '?'} ({other_dept.code if other_dept else '?'}) for {_slot_label(other.day, other.start_period, other.period_count)}.",
                            "other_request_id": str(other.id),
                        })
                    elif other.status == SlotRequestStatus.PENDING:
                        clashes.append({
                            "kind": "pending-venue",
                            "severity": "warning",
                            "message": f"Requested by {other_dept.code if other_dept else '?'} for {other_course.code if other_course else '?'}, awaiting approval.",
                            "other_request_id": str(other.id),
                        })

                if course and other_course and course.lecturer_id and course.lecturer_id == other_course.lecturer_id:
                    lecturer = (await self.db.execute(
                        select(User.name).where(User.id == course.lecturer_id)
                    )).scalar()
                    clashes.append({
                        "kind": "lecturer",
                        "severity": "danger",
                        "message": f"{lecturer or 'Lecturer'} also teaches {other_course.code} at {_slot_label(other.day, other.start_period, other.period_count)}.",
                        "other_request_id": str(other.id),
                    })

                if course and other_course:
                    req_cohorts = await self.db.execute(
                        select(course_cohorts.c.programme_id, course_cohorts.c.level).where(
                            course_cohorts.c.course_id == course.id
                        )
                    )
                    other_cohorts = await self.db.execute(
                        select(course_cohorts.c.programme_id, course_cohorts.c.level).where(
                            course_cohorts.c.course_id == other_course.id
                        )
                    )
                    req_set = {(str(r[0]), r[1]) for r in req_cohorts.all()}
                    other_set = {(str(r[0]), r[1]) for r in other_cohorts.all()}
                    shared = req_set & other_set
                    if shared:
                        clashes.append({
                            "kind": "student",
                            "severity": "danger",
                            "message": f"Students from {len(shared)} cohort(s) take both {course.code} and {other_course.code}.",
                            "other_request_id": str(other.id),
                        })

            if course and req.venue_code:
                venue = (await self.db.execute(
                    select(Venue).where(Venue.code == req.venue_code)
                )).scalar_one_or_none()
                if venue and venue.capacity and course.student_count > venue.capacity:
                    clashes.append({
                        "kind": "capacity",
                        "severity": "warning",
                        "message": f"{course.code} has {course.student_count} students but {req.venue_code} seats {venue.capacity}.",
                    })

            if clashes:
                has_danger = any(c["severity"] == "danger" for c in clashes)
                if has_danger:
                    with_danger += 1
                else:
                    warnings_only_count += 1

                requests_with_clashes.append({
                    "id": str(req.id),
                    "course_code": course.code if course else "",
                    "course_title": course.title if course else "",
                    "department_name": dept.name if dept else "",
                    "venue_code": req.venue_code,
                    "day": req.day,
                    "start_period": req.start_period,
                    "period_count": req.period_count,
                    "status": req.status.value if req.status else "",
                    "slot_label": _slot_label(req.day, req.start_period, req.period_count),
                    "clashes": clashes,
                })

        for item in conflict_items:
            course = (await self.db.execute(
                select(Course).where(Course.id == item.course_id)
            )).scalar_one_or_none()
            dept = (await self.db.execute(
                select(Department).where(Department.id == item.department_id)
            )).scalar_one_or_none()
            sp = item.start_period or 0
            pc = item.period_count or 1
            with_danger += 1
            requests_with_clashes.append({
                "id": str(item.id),
                "course_code": course.code if course else "",
                "course_title": course.title if course else "",
                "department_name": dept.name if dept else "",
                "venue_code": item.venue_code,
                "day": item.day,
                "start_period": sp,
                "period_count": pc,
                "status": "conflict",
                "slot_label": _slot_label(item.day, sp, pc),
                "clashes": [{"kind": "conflict-item", "severity": "danger", "message": "Schedule item has unresolved conflicts."}],
            })

        double_bookings = await self._get_double_bookings(semester_id)

        requests_with_clashes.sort(key=lambda r: (
            0 if any(c["severity"] == "danger" for c in r["clashes"]) else 1,
            r["day"],
            r["start_period"],
        ))

        return {
            "requests": requests_with_clashes,
            "stats": {
                "with_danger": with_danger,
                "warnings_only": warnings_only_count,
                "double_bookings": len(double_bookings),
            },
            "double_bookings": double_bookings,
        }

    async def _get_double_bookings(self, semester_id: uuid.UUID) -> List[Dict[str, Any]]:
        shared_venues = {"DEPT", "ONLINE"}
        timetables_result = await self.db.execute(
            select(MasterTimetable.id).where(MasterTimetable.semester_id == semester_id)
        )
        tt_ids = [r[0] for r in timetables_result.all()]

        if not tt_ids:
            return []

        entries_result = await self.db.execute(
            select(
                MasterEntry.venue_code,
                MasterEntry.day,
                MasterEntry.period,
                func.array_agg(func.distinct(MasterEntry.subject)),
            ).where(
                MasterEntry.timetable_id.in_(tt_ids),
                MasterEntry.is_free == False,
                MasterEntry.venue_code.notin_(shared_venues),
            ).group_by(
                MasterEntry.venue_code,
                MasterEntry.day,
                MasterEntry.period,
            ).having(
                func.count(func.distinct(MasterEntry.subject)) > 1
            )
        )

        double_bookings = []
        for row in entries_result.all():
            double_bookings.append({
                "venue": row[0],
                "day": row[1],
                "period": row[2],
                "subjects": list(row[3]) if row[3] else [],
            })

        return double_bookings
