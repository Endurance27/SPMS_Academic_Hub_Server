import uuid
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import select, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.models.master_timetable import MasterTimetable, MasterEntry
from app.models.timetable_upload import TimetableUpload
from app.models.semester import Semester
from app.models.venue import Venue
from app.models.slot_request import SlotRequest
from app.models.department import Department
from app.repositories.master_timetable_repository import MasterTimetableRepository
from app.utils.timetable_parser import TimetableParser


class MasterTimetableService:
    def __init__(self, db: AsyncSession, redis: Optional[Redis] = None):
        self.db = db
        self.redis = redis
        self.repo = MasterTimetableRepository(db)

    async def _store_preview(self, preview_id: str, data: Dict[str, Any]) -> None:
        if self.redis is None:
            raise RuntimeError("Redis is required to store timetable previews")
        await self.redis.setex(
            f"timetable_preview:{preview_id}", 1800, json.dumps(data)
        )

    async def _load_preview(self, preview_id: str) -> Dict[str, Any]:
        if self.redis is None:
            raise RuntimeError("Redis is required to retrieve timetable previews")
        raw_data = await self.redis.get(f"timetable_preview:{preview_id}")
        if not raw_data:
            raise ValueError("Timetable preview was not found or has expired")
        return json.loads(raw_data)

    async def list_timetables(self, semester_id: uuid.UUID) -> List[Dict]:
        """List all master timetables for a semester"""
        timetables = await self.repo.list_by_semester(semester_id)

        result = []
        for tt in timetables:
            entries_count = await self.repo.count_entries(tt.id)
            free_count = await self.repo.count_free_entries(tt.id)

            result.append({
                "id": str(tt.id),
                "semester_id": str(tt.semester_id),
                "level": tt.level,
                "filename": tt.filename,
                "uploaded_by_id": str(tt.uploaded_by_id),
                "uploaded_at": tt.uploaded_at.isoformat() if tt.uploaded_at else None,
                "version": tt.version,
                "entry_count": entries_count,
                "free_count": free_count
            })

        return result

    async def get_entries(
        self,
        semester_id: uuid.UUID,
        level: Optional[int] = None,
        venue_code: Optional[str] = None,
        subjects: Optional[List[str]] = None,
        day: Optional[int] = None
    ) -> tuple[List[Dict], Dict]:
        """Get master timetable entries with filtering"""
        entries = await self.repo.get_entries(
            semester_id=semester_id,
            level=level,
            venue_code=venue_code,
            subjects=subjects,
            day=day
        )

        # Calculate meta counts
        meta = {}
        if level is None:
            # Count per level
            levels = [100, 200, 300, 400]
            for lvl in levels:
                level_entries = await self.repo.get_entries(semester_id, level=lvl)
                meta[f"level_{lvl}_count"] = len(level_entries)
                meta[f"level_{lvl}_free"] = sum(1 for e in level_entries if e.is_free)

        meta["total_count"] = len(entries)
        meta["free_count"] = sum(1 for e in entries if e.is_free)

        result = []
        for entry in entries:
            result.append({
                "id": str(entry.id),
                "timetable_id": str(entry.timetable_id),
                "level": entry.level,
                "day": entry.day,
                "period": entry.period,
                "subject": entry.subject,
                "venue_code": entry.venue_code,
                "is_free": entry.is_free,
                "department_id": str(entry.department_id) if entry.department_id else None,
                "course_kind": entry.course_kind
            })

        return result, meta

    async def preview_upload(
        self,
        content: bytes,
        file_type: str,
        semester_id: uuid.UUID,
        level: int,
        filename: str
    ) -> Dict:
        """Preview timetable upload"""
        # Verify semester exists
        semester_result = await self.db.execute(
            select(Semester).where(Semester.id == semester_id)
        )
        semester = semester_result.scalar_one_or_none()
        if not semester:
            raise ValueError("Semester not found")

        # Parse file
        parser = TimetableParser()
        parse_result = parser.parse_file(content, file_type, level, str(semester_id))

        preview_id = str(uuid.uuid4())
        preview_data = {
            "entries": parse_result["entries"],
            "issues": parse_result["issues"],
            "summary": parse_result["summary"],
            "semester_id": str(semester_id),
            "level": level,
            "filename": filename
        }
        await self._store_preview(preview_id, preview_data)

        # Check if existing timetable(s) exist
        replaces = None
        if level:
            existing = await self.repo.get_by_semester_and_level(semester_id, level)
            if existing:
                replaces = {
                    "uploaded_at": existing.uploaded_at.isoformat() if existing.uploaded_at else None,
                    "uploaded_by_id": str(existing.uploaded_by_id)
                }

        # Check affected slot requests
        affected_requests = await self._check_affected_requests(semester_id, level, parse_result["entries"])

        return {
            "preview_id": preview_id,
            "entries": parse_result["entries"],
            "issues": parse_result["issues"],
            "summary": parse_result["summary"],
            "replaces": replaces,
            "affected_requests": affected_requests
        }

    async def publish_timetable(
        self,
        preview_id: str,
        uploaded_by_id: uuid.UUID
    ) -> str:
        """Persist the uploaded master timetable and its parsed entries."""
        preview_data = await self._load_preview(preview_id)
        semester_id = uuid.UUID(preview_data["semester_id"])
        entries_by_level: Dict[int, List[Dict[str, Any]]] = {}
        for entry in preview_data.get("entries", []):
            entry_level = int(entry.get("level") or preview_data.get("level") or 0)
            entries_by_level.setdefault(entry_level, []).append(entry)
        if not entries_by_level:
            raise ValueError("Cannot publish a timetable with no entries")

        semester_result = await self.db.execute(
            select(Semester).where(Semester.id == semester_id)
        )
        if not semester_result.scalar_one_or_none():
            raise ValueError("Semester not found")

        for level, level_entries in entries_by_level.items():
            timetable = await self.repo.get_by_semester_and_level(semester_id, level)
            if timetable:
                timetable.version = (timetable.version or 1) + 1
                timetable.filename = preview_data["filename"]
                timetable.uploaded_by_id = uploaded_by_id
                await self.db.execute(
                    delete(MasterEntry).where(
                        MasterEntry.timetable_id == timetable.id,
                        MasterEntry.department_id.is_(None),
                    )
                )
            else:
                timetable = MasterTimetable(
                    semester_id=semester_id,
                    level=level,
                    filename=preview_data["filename"],
                    uploaded_by_id=uploaded_by_id,
                    version=1,
                )
                self.db.add(timetable)
                await self.db.flush()

            self.db.add_all([
                MasterEntry(
                    timetable_id=timetable.id,
                    level=level,
                    day=int(entry["day"]),
                    period=int(entry["period"]),
                    subject=entry["subject"],
                    venue_code=entry["venue_code"],
                    is_free=bool(entry.get("is_free", False)),
                    department_id=entry.get("department_id"),
                    course_kind=entry.get("course_kind"),
                )
                for entry in level_entries
            ])
            self.db.add(TimetableUpload(
                semester_id=semester_id,
                level=level,
                filename=preview_data["filename"],
                uploaded_by_id=uploaded_by_id,
                entry_count=len(level_entries),
                kind="master",
            ))

        await self.db.commit()
        await self.redis.delete(f"timetable_preview:{preview_id}")
        return "Timetable published successfully"

    async def preview_department_upload(
        self,
        content: bytes,
        file_type: str,
        semester_id: uuid.UUID,
        department_id: uuid.UUID,
        filename: str
    ) -> Dict:
        """Preview department timetable upload"""
        # Get department subject prefixes
        dept_result = await self.db.execute(
            select(Department).where(Department.id == department_id)
        )
        department = dept_result.scalar_one_or_none()
        if not department:
            raise ValueError("Department not found")

        # Parse file
        parser = TimetableParser()
        parse_result = parser.parse_file(content, file_type, 0, str(semester_id))

        # Filter entries by department subject prefixes
        # Fall back to department code when no subject prefixes are configured
        prefixes = department.subject_prefixes or []
        if not prefixes:
            prefixes = [department.code.upper()]

        filtered_entries = []
        for entry in parse_result["entries"]:
            subject = entry.get("subject", "")
            if any(subject.startswith(prefix) for prefix in prefixes):
                filtered_entries.append(entry)

        # Check for conflicts with master timetable
        conflicts = await self._check_department_conflicts(semester_id, filtered_entries)

        preview_id = str(uuid.uuid4())

        preview_data = {
            "entries": filtered_entries,
            "semester_id": str(semester_id),
            "department_id": str(department_id),
            "filename": filename,
        }
        await self._store_preview(preview_id, preview_data)

        levels = sorted({e.get("level") for e in filtered_entries if e.get("level") is not None})
        venues = sorted({e.get("venue_code", e.get("venue", "")) for e in filtered_entries} - {""})

        return {
            "preview_id": preview_id,
            "entries": filtered_entries,
            "conflicts": conflicts,
            "summary": {
                "entry_count": len(filtered_entries),
                "levels": levels,
                "venues": venues,
                "conflict_count": len(conflicts),
            },
        }

    async def publish_department_timetable(
        self,
        preview_id: str,
        uploaded_by_id: uuid.UUID
    ) -> str:
        """Persist department entries on their semester's master timetable."""
        preview_data = await self._load_preview(preview_id)
        semester_id = uuid.UUID(preview_data["semester_id"])
        department_id = uuid.UUID(preview_data["department_id"])
        entries = preview_data.get("entries", [])
        if not entries:
            raise ValueError("Cannot publish a department timetable with no entries")

        semester_result = await self.db.execute(
            select(Semester).where(Semester.id == semester_id)
        )
        if not semester_result.scalar_one_or_none():
            raise ValueError("Semester not found")
        dept_result = await self.db.execute(
            select(Department).where(Department.id == department_id)
        )
        if not dept_result.scalar_one_or_none():
            raise ValueError("Department not found")

        # Replace this department's previously published entries for this semester.
        timetable_ids = select(MasterTimetable.id).where(
            MasterTimetable.semester_id == semester_id
        )
        await self.db.execute(delete(MasterEntry).where(
            MasterEntry.timetable_id.in_(timetable_ids),
            MasterEntry.department_id == department_id,
        ))

        entries_by_level: Dict[int, List[Dict[str, Any]]] = {}
        for entry in entries:
            level = int(entry.get("level") or 0)
            entries_by_level.setdefault(level, []).append(entry)
        for level, level_entries in entries_by_level.items():
            timetable = await self.repo.get_by_semester_and_level(semester_id, level)
            if not timetable:
                timetable = MasterTimetable(
                    semester_id=semester_id,
                    level=level,
                    filename=preview_data["filename"],
                    uploaded_by_id=uploaded_by_id,
                    version=1,
                )
                self.db.add(timetable)
                await self.db.flush()
            self.db.add_all([
                MasterEntry(
                    timetable_id=timetable.id,
                    level=level,
                    day=int(entry["day"]),
                    period=int(entry["period"]),
                    subject=entry["subject"],
                    venue_code=entry["venue_code"],
                    is_free=bool(entry.get("is_free", False)),
                    department_id=department_id,
                    course_kind=entry.get("course_kind"),
                )
                for entry in level_entries
            ])
            self.db.add(TimetableUpload(
                semester_id=semester_id,
                level=level,
                filename=preview_data["filename"],
                uploaded_by_id=uploaded_by_id,
                entry_count=len(level_entries),
                kind="department",
                department_id=department_id,
            ))

        await self.db.commit()
        await self.redis.delete(f"timetable_preview:{preview_id}")
        return "Department timetable published successfully"

    async def export_timetable(
        self,
        semester_id: uuid.UUID,
        level: Optional[int] = None
    ) -> str:
        """Export timetable as CSV"""
        entries, _ = await self.get_entries(semester_id, level)

        lines = ["Level,Day,Time,Subject,Venue"]
        for entry in entries:
            # Calculate time label from period
            period = entry["period"]
            start = f"{7 + period:02d}:30"
            end = f"{8 + period:02d}:20"
            time = f"{start}-{end}"

            lines.append(f"{entry['level']},{entry['day']},{time},{entry['subject']},{entry['venue_code']}")

        return "\n".join(lines)

    async def get_upload_history(self, semester_id: uuid.UUID) -> List[Dict]:
        """Get upload history"""
        uploads = await self.repo.get_upload_history(semester_id)

        result = []
        for upload in uploads:
            result.append({
                "id": str(upload.id),
                "semester_id": str(upload.semester_id),
                "level": upload.level,
                "filename": upload.filename,
                "uploaded_by_id": str(upload.uploaded_by_id),
                "uploaded_at": upload.uploaded_at.isoformat() if upload.uploaded_at else None,
                "entry_count": upload.entry_count,
                "kind": upload.kind,
                "department_id": str(upload.department_id) if upload.department_id else None
            })

        return result

    async def _check_affected_requests(
        self,
        semester_id: uuid.UUID,
        level: int,
        entries: List[Dict]
    ) -> List[Dict]:
        """Check which slot requests are affected by timetable changes"""
        conditions = [
            SlotRequest.semester_id == semester_id,
            SlotRequest.status.in_(["Pending", "Approved"]),
        ]
        if level:
            conditions.append(SlotRequest.level == level)

        result = await self.db.execute(
            select(SlotRequest).where(and_(*conditions))
        )
        requests = result.scalars().all()

        affected = []
        for req in requests:
            # Check if any entry conflicts with this request
            for entry in entries:
                if (entry["day"] == req.day and
                    entry["venue_code"] == req.venue_code and
                    not entry["is_free"] and
                    req.start_period <= entry["period"] < req.start_period + req.period_count):
                    affected.append({
                        "request_id": str(req.id),
                        "course_id": str(req.course_id),
                        "status": req.status
                    })
                    break

        return affected

    async def _check_department_conflicts(
        self,
        semester_id: uuid.UUID,
        entries: List[Dict]
    ) -> List[Dict]:
        """Check for venue clashes between department entries and the master timetable.

        A conflict occurs when a department entry occupies the same
        venue + day + period as an existing master entry with a
        different subject (i.e. the venue is already booked).
        """
        conflicts = []

        for entry in entries:
            venue = entry.get("venue_code", "")
            if not venue or venue in ("DEPT", "ONLINE"):
                continue

            result = await self.db.execute(
                select(MasterEntry)
                .join(MasterTimetable, MasterEntry.timetable_id == MasterTimetable.id)
                .where(
                    and_(
                        MasterTimetable.semester_id == semester_id,
                        MasterEntry.day == entry["day"],
                        MasterEntry.period == entry["period"],
                        MasterEntry.venue_code == venue,
                        MasterEntry.subject != entry["subject"],
                        MasterEntry.is_free == False,
                    )
                )
            )
            existing = result.scalars().all()

            for ex in existing:
                conflicts.append({
                    "level": ex.level,
                    "day": entry["day"],
                    "period": entry["period"],
                    "venue": venue,
                    "existing_subject": ex.subject,
                    "new_subject": entry["subject"],
                    "new_level": entry.get("level"),
                })

        return conflicts
