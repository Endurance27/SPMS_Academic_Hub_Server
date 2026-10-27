import csv
import io
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.attendance import AttendanceRecord, AttendanceRecordStatus, AttendanceSession, AttendanceStatus
from app.models.course import Course
from app.models.department import Department
from app.models.graduation import GraduationSubmission
from app.models.programme import Programme
from app.models.registration import CourseRegistration, RegistrationStatus
from app.models.supporting import ReportJob
from app.models.schedule_item import ScheduleItem, ScheduleItemStatus
from app.models.slot_request import SlotRequest, SlotRequestStatus
from app.models.user import User, UserRole
from app.models.venue import Venue
from app.models.master_timetable import MasterEntry


REPORT_TYPES = [
    "Institution timetable",
    "Department timetable",
    "Department submissions",
    "Faculty workload",
    "Venue utilisation",
    "Attendance summary",
    "Assessment schedule",
    "Graduation data",
    "Student enrollment",
    "Course offerings",
]


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_report(
        self,
        data: Dict[str, Any],
        created_by_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
    ) -> ReportJob:
        report_type = data.get("report_type", "")
        rows: List[Dict[str, Any]] = []
        headers: List[str] = []

        if report_type == "Course offerings":
            rows, headers = await self._course_offerings(department_id)
        elif report_type == "Faculty workload":
            rows, headers = await self._faculty_workload(department_id)
        elif report_type == "Venue utilisation":
            rows, headers = await self._venue_utilisation()
        elif report_type == "Attendance summary":
            rows, headers = await self._attendance_summary(department_id)
        elif report_type == "Assessment schedule":
            rows, headers = await self._assessment_schedule(department_id)
        elif report_type == "Graduation data":
            rows, headers = await self._graduation_data(department_id)
        elif report_type == "Student enrollment":
            rows, headers = await self._student_enrollment(department_id)
        elif report_type == "Department submissions":
            rows, headers = await self._department_submissions()
        elif report_type in ("Institution timetable", "Department timetable"):
            rows, headers = await self._timetable_report(department_id)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
        csv_content = output.getvalue()

        job = ReportJob(
            report_type=report_type,
            academic_year=data.get("academic_year"),
            semester=data.get("semester"),
            programme_id=data.get("programme_id"),
            student_category=data.get("student_category"),
            date_from=data.get("date_from"),
            date_to=data.get("date_to"),
            format=data.get("format", "csv"),
            department_id=department_id or data.get("department_id"),
            status="Ready",
            file_url=None,
            row_count=len(rows),
            created_by_id=created_by_id,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        return job

    async def list_reports(
        self,
        department_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 25,
    ) -> List[ReportJob]:
        q = select(ReportJob).order_by(ReportJob.created_at.desc())
        if department_id:
            q = q.where(ReportJob.department_id == department_id)
        q = q.offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_report(self, report_id: uuid.UUID) -> Optional[ReportJob]:
        result = await self.db.execute(
            select(ReportJob).where(ReportJob.id == report_id)
        )
        return result.scalar_one_or_none()

    async def get_report_csv(self, report_id: uuid.UUID, department_id: Optional[uuid.UUID] = None) -> Optional[str]:
        job = await self.get_report(report_id)
        if not job:
            return None

        rows: List[Dict[str, Any]] = []
        headers: List[str] = []
        dept_id = department_id or job.department_id

        if job.report_type == "Course offerings":
            rows, headers = await self._course_offerings(dept_id)
        elif job.report_type == "Faculty workload":
            rows, headers = await self._faculty_workload(dept_id)
        elif job.report_type == "Venue utilisation":
            rows, headers = await self._venue_utilisation()
        elif job.report_type == "Attendance summary":
            rows, headers = await self._attendance_summary(dept_id)
        elif job.report_type == "Assessment schedule":
            rows, headers = await self._assessment_schedule(dept_id)
        elif job.report_type == "Graduation data":
            rows, headers = await self._graduation_data(dept_id)
        elif job.report_type == "Student enrollment":
            rows, headers = await self._student_enrollment(dept_id)
        elif job.report_type == "Department submissions":
            rows, headers = await self._department_submissions()
        elif job.report_type in ("Institution timetable", "Department timetable"):
            rows, headers = await self._timetable_report(dept_id)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    async def _course_offerings(self, department_id: Optional[uuid.UUID] = None):
        headers = ["Course", "Title", "Type", "Credits", "Lecturer", "Students"]
        q = select(Course)
        if department_id:
            q = q.where(Course.department_id == department_id)
        result = await self.db.execute(q.order_by(Course.code))
        rows = []
        for c in result.scalars().all():
            lecturer_name = ""
            if c.lecturer_id:
                lec = (await self.db.execute(
                    select(User.name).where(User.id == c.lecturer_id)
                )).scalar()
                lecturer_name = lec or ""
            rows.append({
                "Course": c.code,
                "Title": c.title,
                "Type": c.type.value if c.type else "",
                "Credits": c.credit_hours,
                "Lecturer": lecturer_name,
                "Students": c.student_count,
            })
        return rows, headers

    async def _faculty_workload(self, department_id: Optional[uuid.UUID] = None):
        headers = ["Lecturer", "Department", "Courses", "Weekly Contact Hours", "Workload %"]
        q = select(User).where(User.role == UserRole.LECTURER)
        if department_id:
            q = q.where(User.department_id == department_id)
        result = await self.db.execute(q.order_by(User.name))
        rows = []
        for u in result.scalars().all():
            course_count = (await self.db.execute(
                select(func.count()).select_from(Course).where(Course.lecturer_id == u.id)
            )).scalar() or 0
            dept_name = ""
            if u.department_id:
                dept = (await self.db.execute(
                    select(Department.name).where(Department.id == u.department_id)
                )).scalar()
                dept_name = dept or ""

            contact_hours = 0.0
            items_result = await self.db.execute(
                select(ScheduleItem).where(
                    ScheduleItem.lecturer_id == u.id,
                    ScheduleItem.status == ScheduleItemStatus.PUBLISHED,
                )
            )
            for item in items_result.scalars().all():
                if item.start and item.end:
                    try:
                        sh, sm = map(int, item.start.split(":"))
                        eh, em = map(int, item.end.split(":"))
                        contact_hours += (eh * 60 + em - sh * 60 - sm) / 60
                    except (ValueError, AttributeError):
                        pass

            rows.append({
                "Lecturer": u.name,
                "Department": dept_name,
                "Courses": course_count,
                "Weekly Contact Hours": round(contact_hours, 1),
                "Workload %": round(contact_hours / 25 * 100, 1),
            })
        return rows, headers

    async def _venue_utilisation(self):
        headers = ["Venue", "Capacity", "Occupied Periods", "Utilisation %", "Peak Period"]
        result = await self.db.execute(select(Venue).order_by(Venue.code))
        rows = []
        total_teaching_cells = 5 * 12
        for v in result.scalars().all():
            occupied = (await self.db.execute(
                select(func.count()).select_from(ScheduleItem).where(
                    ScheduleItem.venue_code == v.code,
                    ScheduleItem.status == ScheduleItemStatus.PUBLISHED,
                )
            )).scalar() or 0
            util_pct = round(occupied / total_teaching_cells * 100, 1) if total_teaching_cells > 0 else 0
            rows.append({
                "Venue": v.code,
                "Capacity": v.capacity or "",
                "Occupied Periods": occupied,
                "Utilisation %": util_pct,
                "Peak Period": "",
            })
        return rows, headers

    async def _attendance_summary(self, department_id: Optional[uuid.UUID] = None):
        headers = ["Course", "Sessions", "Present", "Late", "Absent", "Excused", "Rate"]
        q = select(Course)
        if department_id:
            q = q.where(Course.department_id == department_id)
        result = await self.db.execute(q.order_by(Course.code))
        rows = []
        for c in result.scalars().all():
            sessions = (await self.db.execute(
                select(func.count()).select_from(AttendanceSession).where(
                    AttendanceSession.course_id == c.id
                )
            )).scalar() or 0

            for status_val, key in [
                (AttendanceRecordStatus.PRESENT, "present"),
                (AttendanceRecordStatus.LATE, "late"),
                (AttendanceRecordStatus.ABSENT, "absent"),
                (AttendanceRecordStatus.EXCUSED, "excused"),
            ]:
                pass
            present = (await self.db.execute(
                select(func.count()).select_from(AttendanceRecord).where(
                    AttendanceRecord.course_id == c.id,
                    AttendanceRecord.status == AttendanceRecordStatus.PRESENT,
                )
            )).scalar() or 0
            late = (await self.db.execute(
                select(func.count()).select_from(AttendanceRecord).where(
                    AttendanceRecord.course_id == c.id,
                    AttendanceRecord.status == AttendanceRecordStatus.LATE,
                )
            )).scalar() or 0
            absent = (await self.db.execute(
                select(func.count()).select_from(AttendanceRecord).where(
                    AttendanceRecord.course_id == c.id,
                    AttendanceRecord.status == AttendanceRecordStatus.ABSENT,
                )
            )).scalar() or 0
            excused = (await self.db.execute(
                select(func.count()).select_from(AttendanceRecord).where(
                    AttendanceRecord.course_id == c.id,
                    AttendanceRecord.status == AttendanceRecordStatus.EXCUSED,
                )
            )).scalar() or 0
            total = present + late + absent + excused
            rate = round((present + late) / total * 100, 1) if total > 0 else 0
            rows.append({
                "Course": c.code,
                "Sessions": sessions,
                "Present": present,
                "Late": late,
                "Absent": absent,
                "Excused": excused,
                "Rate": f"{rate}%",
            })
        return rows, headers

    async def _assessment_schedule(self, department_id: Optional[uuid.UUID] = None):
        headers = ["Course", "Type", "Date", "Start", "End", "Location", "Status"]
        q = select(Assessment).where(
            Assessment.status.notin_([AssessmentStatus.CANCELLED, AssessmentStatus.DRAFT])
        )
        if department_id:
            q = q.where(Assessment.department_id == department_id)
        result = await self.db.execute(q.order_by(Assessment.date))
        rows = []
        for a in result.scalars().all():
            rows.append({
                "Course": a.course_code,
                "Type": a.assessment_type.value if a.assessment_type else "",
                "Date": str(a.date.date()) if a.date else "",
                "Start": a.start_time,
                "End": a.end_time,
                "Location": a.location or "",
                "Status": a.status.value if a.status else "",
            })
        return rows, headers

    async def _graduation_data(self, department_id: Optional[uuid.UUID] = None):
        headers = ["Programme", "Category", "Year", "Students", "Status"]
        q = select(GraduationSubmission)
        if department_id:
            q = q.where(GraduationSubmission.department_id == department_id)
        result = await self.db.execute(q.order_by(GraduationSubmission.created_at.desc()))
        rows = []
        for g in result.scalars().all():
            rows.append({
                "Programme": g.programme_text or "",
                "Category": g.student_category or "",
                "Year": g.academic_year or "",
                "Students": g.declared_count,
                "Status": g.status.value if g.status else "",
            })
        return rows, headers

    async def _student_enrollment(self, department_id: Optional[uuid.UUID] = None):
        headers = ["Programme", "Level", "Category", "Students"]
        q = select(Programme)
        if department_id:
            q = q.where(Programme.department_id == department_id)
        result = await self.db.execute(q.order_by(Programme.code))
        rows = []
        for p in result.scalars().all():
            for level in (p.levels or []):
                count = (await self.db.execute(
                    select(func.count()).select_from(User).where(
                        User.programme_id == p.id,
                        User.level == level,
                        User.role == UserRole.STUDENT,
                    )
                )).scalar() or 0
                rows.append({
                    "Programme": p.code,
                    "Level": level,
                    "Category": p.category.value if p.category else "",
                    "Students": count,
                })
        return rows, headers

    async def _department_submissions(self):
        headers = ["Department", "Pending", "Approved", "Returned", "Last Submission"]
        result = await self.db.execute(select(Department).order_by(Department.name))
        rows = []
        for d in result.scalars().all():
            pending = (await self.db.execute(
                select(func.count()).select_from(SlotRequest).where(
                    SlotRequest.department_id == d.id,
                    SlotRequest.status == SlotRequestStatus.PENDING,
                )
            )).scalar() or 0
            approved = (await self.db.execute(
                select(func.count()).select_from(SlotRequest).where(
                    SlotRequest.department_id == d.id,
                    SlotRequest.status == SlotRequestStatus.APPROVED,
                )
            )).scalar() or 0
            returned = (await self.db.execute(
                select(func.count()).select_from(SlotRequest).where(
                    SlotRequest.department_id == d.id,
                    SlotRequest.status == SlotRequestStatus.RETURNED,
                )
            )).scalar() or 0
            last = (await self.db.execute(
                select(func.max(SlotRequest.created_at)).where(
                    SlotRequest.department_id == d.id,
                )
            )).scalar()
            rows.append({
                "Department": d.name,
                "Pending": pending,
                "Approved": approved,
                "Returned": returned,
                "Last Submission": str(last) if last else "",
            })
        return rows, headers

    async def _timetable_report(self, department_id: Optional[uuid.UUID] = None):
        headers = ["Course", "Title", "Day", "Start", "End", "Venue", "Lecturer", "Mode", "Student group", "Status"]
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        q = select(ScheduleItem).where(
            ScheduleItem.status == ScheduleItemStatus.PUBLISHED
        )
        if department_id:
            q = q.where(ScheduleItem.department_id == department_id)
        result = await self.db.execute(q.order_by(ScheduleItem.day, ScheduleItem.start))
        rows = []
        for item in result.scalars().all():
            course = (await self.db.execute(
                select(Course.code, Course.title).where(Course.id == item.course_id)
            )).first()
            lecturer_name = "Lecturer to be assigned"
            if item.lecturer_id:
                lec = (await self.db.execute(
                    select(User.name).where(User.id == item.lecturer_id)
                )).scalar()
                lecturer_name = lec or lecturer_name
            status_labels = {
                ScheduleItemStatus.PUBLISHED: "Published",
                ScheduleItemStatus.PENDING: "Awaiting approval",
                ScheduleItemStatus.CONFLICT: "Blocked by conflict",
            }
            rows.append({
                "Course": course.code if course else "",
                "Title": course.title if course else "",
                "Day": weekdays[item.day] if 0 <= item.day < len(weekdays) else str(item.day),
                "Start": item.start or "",
                "End": item.end or "",
                "Venue": item.venue_code or "",
                "Lecturer": lecturer_name,
                "Mode": item.mode or "",
                "Student group": "",
                "Status": status_labels.get(item.status, str(item.status.value)) if item.status else "",
            })
        return rows, headers
