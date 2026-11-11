import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import re

from app.models.course import Course, course_cohorts
from app.models.department import Department
from app.models.master_timetable import MasterEntry, MasterTimetable
from app.models.registration import CourseRegistration, RegistrationSource, RegistrationStatus
from app.models.semester import Semester
from app.models.user import User
from app.schemas.registration import RegistrationCreate

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _normalize_course_code(raw: str) -> str:
    cleaned = re.sub(r'\s*\([^)]*\)\s*$', '', raw.strip())
    return re.sub(r'\s+', '', cleaned).upper()


class RegistrationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_registrations(
        self,
        student_id: uuid.UUID,
        semester_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[dict], int, dict]:
        base = select(CourseRegistration).where(
            CourseRegistration.student_id == student_id
        )
        if semester_id:
            base = base.where(CourseRegistration.semester_id == semester_id)

        total_result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = total_result.scalar() or 0

        query = (
            select(CourseRegistration, Course)
            .outerjoin(Course, Course.id == CourseRegistration.course_id)
            .where(CourseRegistration.student_id == student_id)
        )
        if semester_id:
            query = query.where(CourseRegistration.semester_id == semester_id)

        query = query.order_by(CourseRegistration.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        rows = result.all()

        registrations = []
        total_credits = 0
        counts = {"Current": 0, "Required": 0, "Electives": 0}

        for reg, course in rows:
            if reg.status != RegistrationStatus.DROPPED:
                total_credits += reg.credits
                counts["Current"] += 1
                if reg.registration_type.value == "Elective":
                    counts["Electives"] += 1
                else:
                    counts["Required"] += 1

            registrations.append({
                "id": reg.id,
                "student_id": reg.student_id,
                "course_id": reg.course_id,
                "course_code": course.code if course else reg.custom_course_code,
                "course_title": course.title if course else reg.custom_course_title,
                "custom_course_code": reg.custom_course_code,
                "custom_course_title": reg.custom_course_title,
                "semester_id": reg.semester_id,
                "level": reg.level,
                "registration_type": reg.registration_type,
                "credits": reg.credits,
                "status": reg.status,
                "source": reg.source,
                "created_at": reg.created_at,
            })

        return registrations, total, {"counts": counts, "totalCredits": total_credits}

    async def get_registration_detail(
        self,
        registration_id: uuid.UUID,
        student_id: uuid.UUID,
        student_category: Optional[str] = None,
    ) -> Optional[dict]:
        result = await self.db.execute(
            select(CourseRegistration, Course, Department)
            .outerjoin(Course, Course.id == CourseRegistration.course_id)
            .outerjoin(Department, Department.id == Course.department_id)
            .where(
                CourseRegistration.id == registration_id,
                CourseRegistration.student_id == student_id,
            )
        )
        row = result.first()
        if not row:
            return None

        reg, course, department = row

        data: dict = {
            "id": reg.id,
            "student_id": reg.student_id,
            "course_id": reg.course_id,
            "course_code": course.code if course else reg.custom_course_code,
            "course_title": course.title if course else reg.custom_course_title,
            "custom_course_code": reg.custom_course_code,
            "custom_course_title": reg.custom_course_title,
            "semester_id": reg.semester_id,
            "level": reg.level,
            "registration_type": reg.registration_type,
            "credits": reg.credits,
            "status": reg.status,
            "source": reg.source,
            "created_at": reg.created_at,
            "cohorts": [],
            "timetable_entries": [],
        }

        if course:
            data["course_type"] = course.type.value if course.type else None
            data["course_mode"] = course.mode.value if course.mode else None
            data["credit_hours"] = course.credit_hours
            data["student_count"] = course.student_count

            if course.lecturer_id:
                lecturer_result = await self.db.execute(
                    select(User).where(User.id == course.lecturer_id)
                )
                lecturer = lecturer_result.scalar_one_or_none()
                if lecturer:
                    data["lecturer_id"] = lecturer.id
                    data["lecturer_name"] = lecturer.name
                    data["lecturer_email"] = lecturer.email
                    data["lecturer_office"] = lecturer.office

            if department:
                data["department_id"] = department.id
                data["department_name"] = department.name
                data["department_code"] = department.code

            cohort_result = await self.db.execute(
                select(
                    course_cohorts.c.programme_id,
                    course_cohorts.c.level,
                )
                .where(course_cohorts.c.course_id == course.id)
            )
            data["cohorts"] = [
                {"programme_id": str(r.programme_id), "level": r.level}
                for r in cohort_result.all()
            ]

            code_to_match = course.code
        else:
            code_to_match = reg.custom_course_code

        if code_to_match:
            norm_target = _normalize_course_code(code_to_match)

            category = student_category.lower() if student_category else None
            entry_query = (
                select(MasterEntry)
                .join(MasterTimetable, MasterEntry.timetable_id == MasterTimetable.id)
                .where(
                    MasterTimetable.semester_id == reg.semester_id,
                    MasterEntry.is_free == False,
                )
            )
            if category:
                entry_query = entry_query.where(MasterTimetable.category == category)
            entry_query = entry_query.order_by(MasterEntry.day, MasterEntry.period)

            entry_result = await self.db.execute(entry_query)
            seen: set[tuple] = set()
            for entry in entry_result.scalars():
                if _normalize_course_code(entry.subject) != norm_target:
                    continue
                key = (entry.subject, entry.day, entry.period, entry.venue_code)
                if key in seen:
                    continue
                seen.add(key)

                if entry.start_time and entry.end_time:
                    p_start = entry.start_time
                    p_end = entry.end_time
                else:
                    h = 7 + entry.period
                    p_start = f"{h:02d}:30"
                    p_end = f"{h + 1:02d}:20"

                data["timetable_entries"].append({
                    "id": entry.id,
                    "day": entry.day,
                    "day_name": DAY_NAMES[entry.day] if 0 <= entry.day < len(DAY_NAMES) else None,
                    "period": entry.period,
                    "period_start": p_start,
                    "period_end": p_end,
                    "venue_code": entry.venue_code,
                    "course_kind": entry.course_kind,
                    "source": "department" if entry.department_id else "master",
                })

        return data

    async def get_catalogue(
        self,
        student: User,
        semester_id: uuid.UUID,
    ) -> List[dict]:
        all_courses_q = (
            select(Course, Department.name.label("department_name"))
            .join(Department, Department.id == Course.department_id)
        )
        result = await self.db.execute(all_courses_q)
        rows = result.all()

        programme_course_ids = set()
        if student.programme_id and student.level:
            cohort_q = select(course_cohorts.c.course_id).where(
                course_cohorts.c.programme_id == student.programme_id,
                course_cohorts.c.level == student.level,
            )
            cohort_result = await self.db.execute(cohort_q)
            programme_course_ids = {r[0] for r in cohort_result.all()}

        # Get already registered course IDs
        registered_q = select(CourseRegistration.course_id).where(
            CourseRegistration.student_id == student.id,
            CourseRegistration.semester_id == semester_id,
            CourseRegistration.status != RegistrationStatus.DROPPED,
        )
        registered_result = await self.db.execute(registered_q)
        registered_ids = {r[0] for r in registered_result.all() if r[0]}

        catalogue = []
        for course, dept_name in rows:
            if course.id in registered_ids:
                continue

            lecturer_name = None
            if course.lecturer:
                lecturer_name = course.lecturer.name

            catalogue.append({
                "id": course.id,
                "code": course.code,
                "title": course.title,
                "department_id": course.department_id,
                "department_name": dept_name,
                "course_type": course.type.value if course.type else "Core",
                "credit_hours": course.credit_hours,
                "mode": course.mode or "in-person",
                "lecturer_name": lecturer_name,
                "is_programme_match": course.id in programme_course_ids,
            })

        catalogue.sort(key=lambda c: (not c["is_programme_match"], c["code"]))
        return catalogue

    async def create_registration(
        self,
        student: User,
        data: RegistrationCreate,
    ) -> CourseRegistration:
        # Check registration deadline
        semester_result = await self.db.execute(
            select(Semester).where(Semester.id == data.semester_id)
        )
        semester = semester_result.scalar_one_or_none()
        if not semester:
            raise ValueError("Semester not found.")

        if semester.registration_deadline:
            if datetime.now(timezone.utc) > semester.registration_deadline:
                raise ValueError("Registration for this semester has closed.")

        # Check duplicate
        if data.course_id:
            dup_q = select(CourseRegistration).where(
                CourseRegistration.student_id == student.id,
                CourseRegistration.course_id == data.course_id,
                CourseRegistration.semester_id == data.semester_id,
                CourseRegistration.status != RegistrationStatus.DROPPED,
            )
            dup_result = await self.db.execute(dup_q)
            if dup_result.scalar_one_or_none():
                raise ValueError("You are already registered for this course.")

        status = RegistrationStatus.REGISTERED
        if data.custom_course_code and not data.course_id:
            status = RegistrationStatus.PENDING_APPROVAL

        registration = CourseRegistration(
            student_id=student.id,
            course_id=data.course_id,
            custom_course_code=data.custom_course_code,
            custom_course_title=data.custom_course_title,
            semester_id=data.semester_id,
            level=data.level,
            registration_type=data.registration_type,
            credits=data.credits,
            status=status,
            source=RegistrationSource.SELF,
        )
        self.db.add(registration)
        await self.db.commit()
        await self.db.refresh(registration)
        return registration

    async def drop_registration(
        self, registration_id: uuid.UUID, student_id: uuid.UUID
    ) -> bool:
        result = await self.db.execute(
            select(CourseRegistration).where(
                CourseRegistration.id == registration_id,
                CourseRegistration.student_id == student_id,
            )
        )
        reg = result.scalar_one_or_none()
        if not reg:
            return False

        if reg.status == RegistrationStatus.DROPPED:
            raise ValueError("Registration already dropped.")

        # Check deadline
        semester_result = await self.db.execute(
            select(Semester).where(Semester.id == reg.semester_id)
        )
        semester = semester_result.scalar_one_or_none()
        if semester and semester.registration_deadline:
            if datetime.now(timezone.utc) > semester.registration_deadline:
                raise ValueError("Registration deadline has passed. Cannot drop.")

        reg.status = RegistrationStatus.DROPPED
        await self.db.commit()
        return True
