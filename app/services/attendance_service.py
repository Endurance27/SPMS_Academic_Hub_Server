import uuid
import hmac
import time
from typing import Optional, List, Dict
from datetime import datetime

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceSession, AttendanceRecord, AttendanceStatus
from app.models.course import Course
from app.models.user import User, UserRole
from app.repositories.attendance_repository import AttendanceRepository


class AttendanceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AttendanceRepository(db)

    async def list_sessions(
        self,
        status: Optional[str],
        course_id: Optional[uuid.UUID],
        department_id: Optional[uuid.UUID],
        date: Optional[str],
        user: User
    ) -> tuple[List[Dict], Dict]:
        """List attendance sessions"""
        sessions = await self.repo.list_sessions_filtered(
            status=status,
            course_id=course_id,
            department_id=department_id,
            date=date,
            user_role=user.role,
            user_department_id=user.department_id,
            user_id=user.id
        )

        result = []
        for session in sessions:
            result.append(await self._session_to_dict(session))

        meta = {
            "All": len(sessions),
            "Live": sum(1 for s in sessions if s.status == AttendanceStatus.LIVE),
            "Completed": sum(1 for s in sessions if s.status == AttendanceStatus.COMPLETED),
            "Missed": sum(1 for s in sessions if s.status == AttendanceStatus.MISSED)
        }

        return result, meta

    async def create_session(self, data: Dict, user: User) -> Dict:
        """Create attendance session"""
        course = await self._get_course(data["course_id"])
        if not course:
            raise ValueError("Course not found")

        # Count enrolled students
        enrolled_count = await self._count_enrolled_students(data["course_id"])

        session = AttendanceSession(
            course_id=data["course_id"],
            schedule_item_id=data.get("schedule_item_id"),
            lecturer_id=user.id,
            date=data["date"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            venue_code=data.get("venue_code"),
            status=AttendanceStatus.SCHEDULED,
            expected_count=enrolled_count
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        return await self._session_to_dict(session)

    async def open_session(self, session_id: uuid.UUID, user: User) -> Dict:
        """Open session for QR check-in"""
        session = await self.repo.get_session_by_id(session_id)
        if not session:
            raise ValueError("Session not found")

        if session.lecturer_id != user.id:
            raise ValueError("Not your session")

        session.status = AttendanceStatus.LIVE
        session.opened_at = datetime.utcnow()
        session.qr_secret = uuid.uuid4().hex
        session.qr_rotation_seconds = 30

        await self.db.commit()
        await self.db.refresh(session)

        return await self._session_to_dict(session)

    async def get_qr_token(self, session_id: uuid.UUID, user: User) -> Dict:
        """Get rotating QR token"""
        session = await self.repo.get_session_by_id(session_id)
        if not session or session.lecturer_id != user.id:
            raise ValueError("Invalid session")

        if session.status != AttendanceStatus.LIVE:
            raise ValueError("Session not live")

        # Generate token based on time window
        time_window = int(time.time() // session.qr_rotation_seconds)
        token = hmac.new(
            session.qr_secret.encode(),
            str(time_window).encode(),
            'sha256'
        ).hexdigest()[:8]

        return {
            "token": token,
            "expires_at": (time_window + 1) * session.qr_rotation_seconds
        }

    async def check_in(self, token: str, user: User) -> Dict:
        """Student QR check-in"""
        # Find live session for student's courses
        sessions = await self.repo.get_live_sessions_for_student(user.id)

        for session in sessions:
            # Verify token
            time_window = int(time.time() // session.qr_rotation_seconds)
            expected_token = hmac.new(
                session.qr_secret.encode(),
                str(time_window).encode(),
                'sha256'
            ).hexdigest()[:8]

            # Check current or previous window
            prev_window = time_window - 1
            prev_token = hmac.new(
                session.qr_secret.encode(),
                str(prev_window).encode(),
                'sha256'
            ).hexdigest()[:8]

            if token in (expected_token, prev_token):
                # Determine status (late if after start + 15 min)
                is_late = self._is_late(session.start_time)
                status = "Late" if is_late else "Present"

                # Create or update record
                existing = await self.repo.get_record(session.id, user.id)
                if existing:
                    existing.status = status
                    existing.source = "QR scan"
                    existing.recorded_at = datetime.utcnow()
                else:
                    record = AttendanceRecord(
                        session_id=session.id,
                        course_id=session.course_id,
                        student_id=user.id,
                        status=status,
                        source="QR scan",
                        recorded_by_id=user.id,
                        recorded_at=datetime.utcnow()
                    )
                    self.db.add(record)

                await self.db.commit()
                return {"status": status, "session_id": str(session.id)}

        raise ValueError("Invalid or expired token")

    async def close_session(self, session_id: uuid.UUID, user: User) -> Dict:
        """Close attendance session"""
        session = await self.repo.get_session_by_id(session_id)
        if not session or session.lecturer_id != user.id:
            raise ValueError("Invalid session")

        # Mark absent for enrolled students without records
        enrolled = await self._get_enrolled_students(session.course_id)
        recorded = await self.repo.get_recorded_student_ids(session.id)

        for student_id in enrolled:
            if student_id not in recorded:
                record = AttendanceRecord(
                    session_id=session.id,
                    course_id=session.course_id,
                    student_id=student_id,
                    status="Absent",
                    source="Auto-absent",
                    recorded_by_id=user.id,
                    recorded_at=datetime.utcnow()
                )
                self.db.add(record)

        session.status = AttendanceStatus.COMPLETED
        session.closed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(session)

        return await self._session_to_dict(session)

    async def create_record(self, data: Dict, user: User) -> Dict:
        """Manual attendance record"""
        # Create session if needed
        session_id = data.get("session_id")
        if not session_id:
            # Create session from course/date
            session = await self._ensure_session(data, user)
            session_id = session.id

        # Create record
        existing = await self.repo.get_record(session_id, data["student_id"])
        if existing:
            existing.status = data["status"]
            existing.note = data.get("note")
            existing.recorded_by_id = user.id
            existing.recorded_at = datetime.utcnow()
        else:
            record = AttendanceRecord(
                session_id=session_id,
                course_id=data.get("course_id"),
                student_id=data["student_id"],
                status=data["status"],
                source="Manual entry",
                note=data.get("note"),
                recorded_by_id=user.id,
                recorded_at=datetime.utcnow()
            )
            self.db.add(record)

        await self.db.commit()
        return {"student_id": str(data["student_id"]), "status": data["status"]}

    async def bulk_create_records(self, session_id: uuid.UUID, records: List[Dict], user: User) -> Dict:
        """Bulk attendance records"""
        for record_data in records:
            existing = await self.repo.get_record(session_id, record_data["student_id"])
            if existing:
                existing.status = record_data["status"]
                existing.recorded_by_id = user.id
                existing.recorded_at = datetime.utcnow()
            else:
                record = AttendanceRecord(
                    session_id=session_id,
                    student_id=record_data["student_id"],
                    status=record_data["status"],
                    source="Manual entry",
                    recorded_by_id=user.id,
                    recorded_at=datetime.utcnow()
                )
                self.db.add(record)

        await self.db.commit()
        return {"count": len(records)}

    async def list_records(
        self,
        course_id: Optional[uuid.UUID],
        student_id: Optional[uuid.UUID],
        from_date: Optional[str],
        to_date: Optional[str],
        user: User
    ) -> Dict:
        """List attendance records"""
        records = await self.repo.list_records_filtered(
            course_id=course_id,
            student_id=student_id,
            from_date=from_date,
            to_date=to_date,
            user_role=user.role,
            user_id=user.id
        )

        stats = {
            "sessions": len(set(r.session_id for r in records)),
            "present": sum(1 for r in records if r.status == "Present"),
            "late": sum(1 for r in records if r.status == "Late"),
            "absent": sum(1 for r in records if r.status == "Absent"),
            "excused": sum(1 for r in records if r.status == "Excused"),
            "rate": 0.0
        }

        if stats["sessions"] > 0:
            stats["rate"] = (stats["present"] + stats["late"]) / len(records) if records else 0.0

        return {"records": records, "stats": stats}

    async def _session_to_dict(self, session: AttendanceSession) -> Dict:
        """Convert session to dict"""
        # Get counts
        records = await self.repo.get_records_by_session(session.id)
        present = sum(1 for r in records if r.status == "Present")
        late = sum(1 for r in records if r.status == "Late")
        absent = sum(1 for r in records if r.status == "Absent")
        excused = sum(1 for r in records if r.status == "Excused")

        return {
            "id": str(session.id),
            "course_id": str(session.course_id),
            "schedule_item_id": str(session.schedule_item_id) if session.schedule_item_id else None,
            "lecturer_id": str(session.lecturer_id),
            "date": session.date,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "venue_code": session.venue_code,
            "status": session.status.value,
            "opened_at": session.opened_at.isoformat() if session.opened_at else None,
            "closed_at": session.closed_at.isoformat() if session.closed_at else None,
            "expected_count": session.expected_count,
            "present_count": present,
            "late_count": late,
            "absent_count": absent,
            "excused_count": excused,
            "rate": (present + late) / session.expected_count if session.expected_count > 0 else 0.0
        }

    async def _get_course(self, course_id: uuid.UUID) -> Optional[Course]:
        result = await self.db.execute(
            select(Course).where(Course.id == course_id)
        )
        return result.scalar_one_or_none()

    async def _count_enrolled_students(self, course_id: uuid.UUID) -> int:
        from app.models.registration import CourseRegistration
        result = await self.db.execute(
            select(func.count()).select_from(CourseRegistration).where(
                and_(
                    CourseRegistration.course_id == course_id,
                    CourseRegistration.status == "Registered"
                )
            )
        )
        return result.scalar_one() or 0

    async def _get_enrolled_students(self, course_id: uuid.UUID) -> List[uuid.UUID]:
        from app.models.registration import CourseRegistration
        result = await self.db.execute(
            select(CourseRegistration.student_id).where(
                and_(
                    CourseRegistration.course_id == course_id,
                    CourseRegistration.status == "Registered"
                )
            )
        )
        return [r[0] for r in result.all()]

    async def _get_recorded_student_ids(self, session_id: uuid.UUID) -> List[uuid.UUID]:
        result = await self.db.execute(
            select(AttendanceRecord.student_id).where(AttendanceRecord.session_id == session_id)
        )
        return [r[0] for r in result.all()]

    def _is_late(self, start_time: str) -> bool:
        """Check if check-in is late (after start + 15 min)"""
        # Simplified - would need proper time comparison
        return False

    async def _ensure_session(self, data: Dict, user: User) -> AttendanceSession:
        """Ensure session exists for manual record"""
        session = AttendanceSession(
            course_id=data["course_id"],
            lecturer_id=user.id,
            date=data["session_date"],
            start_time="00:00",
            end_time="23:59",
            status=AttendanceStatus.COMPLETED,
            expected_count=1
        )
        self.db.add(session)
        await self.db.flush()
        return session
