import asyncio
import logging
import re
import uuid
import json
from typing import Optional, List, Dict, Any, Set
from datetime import datetime
from collections import defaultdict

from sqlalchemy import select, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.models.master_timetable import MasterTimetable, MasterEntry
from app.models.timetable_upload import TimetableUpload
from app.models.semester import Semester
from app.models.venue import Venue
from app.models.venue import VenueType, VenueStatus
from app.models.slot_request import SlotRequest
from app.models.department import Department
from app.repositories.master_timetable_repository import MasterTimetableRepository
from app.utils.timetable_parser import TimetableParser

logger = logging.getLogger(__name__)

SKIP_VENUE_CODES = {"DEPT", "ONLINE", "FREE", "TBA", "TBD", "N/A", ""}

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _extract_subject_prefix(subject: str) -> str:
    """Extract the alphabetic department prefix from a subject.
    'DCIT 111 (C)' → 'DCIT', 'MATH' → 'MATH', 'FREE' → 'FREE'
    """
    cleaned = re.sub(r'\s*\([CE]\)\s*$', '', subject.strip())
    m = re.match(r'^([A-Z]+)', cleaned.strip())
    return m.group(1) if m else cleaned.strip()


def _merge_entries(entries: list) -> list:
    """Merge department entries over matching master entries.

    For each (day, period, level) slot, if a department entry shares the same
    subject prefix as a master entry, the department entry replaces the master.
    """
    slots: Dict[tuple, Dict[str, Dict[str, list]]] = defaultdict(
        lambda: defaultdict(lambda: {"master": [], "dept": []})
    )
    for entry in entries:
        key = (entry.day, entry.period, entry.level)
        prefix = _extract_subject_prefix(entry.subject)
        if entry.department_id is None:
            slots[key][prefix]["master"].append(entry)
        else:
            slots[key][prefix]["dept"].append(entry)

    merged = []
    for prefix_groups in slots.values():
        for pair in prefix_groups.values():
            if pair["dept"]:
                merged.extend(pair["dept"])
            else:
                merged.extend(pair["master"])

    merged.sort(key=lambda e: (e.day, e.period, e.venue_code))
    return merged


async def sync_venues_from_codes(venue_codes: Set[str]) -> None:
    """Create Venue rows for codes that don't exist yet.

    Runs in its own DB session so it can be called from a background task
    without depending on the request's session lifecycle.
    """
    from app.core.database import AsyncSessionLocal

    codes = {c.upper().strip() for c in venue_codes} - SKIP_VENUE_CODES
    if not codes:
        return

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Venue.code).where(Venue.code.in_(codes))
            )
            existing = {row[0] for row in result.all()}
            new_codes = codes - existing

            if not new_codes:
                return

            for code in new_codes:
                match = re.match(r"^([A-Za-z]+)(\d+.*)$", code)
                if match:
                    building = match.group(1)
                    room = match.group(2)
                else:
                    building = code
                    room = "-"

                db.add(Venue(
                    code=code,
                    building=building,
                    room_number=room,
                    type=VenueType.LECTURE_HALL,
                    status=VenueStatus.AVAILABLE,
                ))

            await db.commit()
            logger.info("Auto-created %d venue(s): %s", len(new_codes), ", ".join(sorted(new_codes)))
        except Exception:
            await db.rollback()
            logger.exception("Failed to sync venues from timetable upload")


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

    async def list_timetables(self, semester_id: uuid.UUID, category: Optional[str] = None) -> List[Dict]:
        """List all master timetables for a semester"""
        timetables = await self.repo.list_by_semester(semester_id, category=category)

        result = []
        for tt in timetables:
            entries_count = await self.repo.count_entries(tt.id)
            free_count = await self.repo.count_free_entries(tt.id)

            result.append({
                "id": str(tt.id),
                "semester_id": str(tt.semester_id),
                "level": tt.level,
                "category": tt.category,
                "filename": tt.filename,
                "uploaded_by_id": str(tt.uploaded_by_id),
                "uploaded_at": tt.uploaded_at.isoformat() if tt.uploaded_at else None,
                "version": tt.version,
                "entry_count": entries_count,
                "free_count": free_count
            })

        return result

    async def get_timetable_detail(self, timetable_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Return one timetable with its complete, ordered entry details."""
        result = await self.db.execute(
            select(MasterTimetable).where(MasterTimetable.id == timetable_id)
        )
        timetable = result.scalar_one_or_none()
        if not timetable:
            return None

        entries_result = await self.db.execute(
            select(MasterEntry)
            .where(MasterEntry.timetable_id == timetable_id)
            .order_by(MasterEntry.day, MasterEntry.period, MasterEntry.venue_code)
        )
        shared_venues = {"DEPT", "ONLINE"}

        all_entries = _merge_entries(list(entries_result.scalars().all()))

        master_slot_subjects: Dict[tuple, set] = {}
        dept_slot_subjects: Dict[tuple, set] = {}
        for entry in all_entries:
            if entry.is_free or entry.venue_code in shared_venues:
                continue
            key = (entry.venue_code, entry.day, entry.period)
            if entry.department_id is None:
                master_slot_subjects.setdefault(key, set()).add(entry.subject)
            else:
                dept_slot_subjects.setdefault(key, set()).add(entry.subject)

        double_booked_slots: Dict[tuple, set] = {}
        for k, v in master_slot_subjects.items():
            if len(v) > 1:
                double_booked_slots[k] = v
        for k, v in dept_slot_subjects.items():
            if len(v) > 1:
                double_booked_slots[k] = v

        entries = []
        for entry in all_entries:
            if entry.start_time and entry.end_time:
                period_start = entry.start_time
                period_end = entry.end_time
            else:
                period_start_hour = 7 + entry.period
                period_start = f"{period_start_hour:02d}:30"
                period_end = f"{period_start_hour + 1:02d}:20"
            key = (entry.venue_code, entry.day, entry.period)
            clashing = double_booked_slots.get(key)
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
                "department_id": str(entry.department_id) if entry.department_id else None,
                "course_kind": entry.course_kind,
                "source": "department" if entry.department_id else "master",
                "programme": entry.programme,
                "lecturer_name": entry.lecturer_name,
                "course_title": entry.course_title,
                "double_booked": clashing is not None,
                "clashing_subjects": sorted(clashing) if clashing else [],
            })

        double_bookings = [
            {
                "venue": k[0],
                "day": k[1],
                "day_name": DAY_NAMES[k[1]] if 0 <= k[1] < len(DAY_NAMES) else None,
                "period": k[2],
                "subjects": sorted(v),
            }
            for k, v in double_booked_slots.items()
        ]

        return {
            "id": str(timetable.id),
            "semester_id": str(timetable.semester_id),
            "level": timetable.level,
            "category": timetable.category,
            "filename": timetable.filename,
            "uploaded_by_id": str(timetable.uploaded_by_id),
            "uploaded_at": timetable.uploaded_at.isoformat() if timetable.uploaded_at else None,
            "version": timetable.version,
            "entry_count": len(entries),
            "entries": entries,
            "double_bookings": double_bookings,
            "double_booking_count": len(double_bookings),
        }

    async def delete_timetable(self, timetable_id: uuid.UUID) -> bool:
        """Delete a master timetable and all its entries (cascade)."""
        result = await self.db.execute(
            select(MasterTimetable).where(MasterTimetable.id == timetable_id)
        )
        timetable = result.scalar_one_or_none()
        if not timetable:
            return False

        await self.db.execute(
            delete(MasterEntry).where(MasterEntry.timetable_id == timetable_id)
        )
        await self.db.delete(timetable)
        await self.db.commit()
        return True

    async def get_entries(
        self,
        semester_id: uuid.UUID,
        level: Optional[int] = None,
        venue_code: Optional[str] = None,
        subjects: Optional[List[str]] = None,
        day: Optional[int] = None,
        source: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        category: Optional[str] = None,
        programme: Optional[str] = None,
        cohort: Optional[str] = None,
        course_kind: Optional[str] = None,
    ) -> tuple[List[Dict], Dict]:
        """Get timetable entries with filtering.

        When ``source`` is omitted, returns a **merged** view: department
        entries override matching master entries (matched by day/period/level
        and subject prefix).  Pass ``source="master"`` or
        ``source="department"`` for raw, un-merged entries.
        """
        do_merge = source is None and department_id is None

        if do_merge:
            all_entries = await self.repo.get_entries(
                semester_id=semester_id,
                level=level,
                day=day,
                category=category,
                programme=programme,
                cohort=cohort,
                course_kind=course_kind,
            )
            entries = _merge_entries(all_entries)

            if venue_code is not None:
                entries = [e for e in entries if e.venue_code == venue_code]
            if subjects is not None:
                entries = [e for e in entries if e.subject in subjects]
        else:
            entries = await self.repo.get_entries(
                semester_id=semester_id,
                level=level,
                venue_code=venue_code,
                subjects=subjects,
                day=day,
                source=source,
                department_id=department_id,
                category=category,
                programme=programme,
                cohort=cohort,
                course_kind=course_kind,
            )

        meta = {}
        if level is None:
            if do_merge:
                distinct_levels = sorted({e.level for e in entries})
                for lvl in distinct_levels:
                    lvl_entries = [e for e in entries if e.level == lvl]
                    meta[f"level_{lvl}_count"] = len(lvl_entries)
                    meta[f"level_{lvl}_free"] = sum(1 for e in lvl_entries if e.is_free)
            else:
                all_entries = await self.repo.get_entries(
                    semester_id, source=source, department_id=department_id, category=category,
                )
                distinct_levels = sorted({e.level for e in all_entries})
                for lvl in distinct_levels:
                    level_entries = [e for e in all_entries if e.level == lvl]
                    meta[f"level_{lvl}_count"] = len(level_entries)
                    meta[f"level_{lvl}_free"] = sum(1 for e in level_entries if e.is_free)

        meta["total_count"] = len(entries)
        meta["free_count"] = sum(1 for e in entries if e.is_free)

        distinct_programmes = sorted({e.programme for e in entries if e.programme})
        if distinct_programmes:
            meta["programmes"] = distinct_programmes

        result = []
        for entry in entries:
            if entry.start_time and entry.end_time:
                period_start = entry.start_time
                period_end = entry.end_time
            else:
                period_start_hour = 7 + entry.period
                period_start = f"{period_start_hour:02d}:30"
                period_end = f"{period_start_hour + 1:02d}:20"
            result.append({
                "id": str(entry.id),
                "timetable_id": str(entry.timetable_id),
                "level": entry.level,
                "day": entry.day,
                "day_name": DAY_NAMES[entry.day] if 0 <= entry.day < len(DAY_NAMES) else None,
                "period": entry.period,
                "period_start": period_start,
                "period_end": period_end,
                "subject": entry.subject,
                "venue_code": entry.venue_code,
                "is_free": entry.is_free,
                "department_id": str(entry.department_id) if entry.department_id else None,
                "course_kind": entry.course_kind,
                "source": "department" if entry.department_id else "master",
                "programme": entry.programme,
                "lecturer_name": entry.lecturer_name,
                "course_title": entry.course_title,
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

        category = parse_result.get("category", "undergraduate")

        preview_id = str(uuid.uuid4())
        preview_data = {
            "entries": parse_result["entries"],
            "issues": parse_result["issues"],
            "summary": parse_result["summary"],
            "semester_id": str(semester_id),
            "level": level,
            "filename": filename,
            "category": category,
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
    ) -> Dict[str, Any]:
        """Persist the uploaded master timetable and its parsed entries."""
        preview_data = await self._load_preview(preview_id)
        semester_id = uuid.UUID(preview_data["semester_id"])
        category = preview_data.get("category", "undergraduate")
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
                timetable.category = category
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
                    category=category,
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
                    start_time=entry.get("start_time"),
                    end_time=entry.get("end_time"),
                    programme=entry.get("programme") or None,
                    lecturer_name=entry.get("lecturer_name") or None,
                    course_title=entry.get("course_title") or None,
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
                category=category,
            ))

        venue_codes = {
            e.get("venue_code", "") for entries in entries_by_level.values() for e in entries
        }

        await self.db.commit()
        await self.redis.delete(f"timetable_preview:{preview_id}")
        return {"message": "Timetable published successfully", "venue_codes": venue_codes}

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

        conflicts = await self._check_department_conflicts(semester_id, department_id, filtered_entries)
        master_warnings = await self._check_master_compatibility(semester_id, filtered_entries)

        preview_id = str(uuid.uuid4())

        category = parse_result.get("category", "undergraduate")

        preview_data = {
            "entries": filtered_entries,
            "semester_id": str(semester_id),
            "department_id": str(department_id),
            "filename": filename,
            "category": category,
        }
        await self._store_preview(preview_id, preview_data)

        levels = sorted({e.get("level") for e in filtered_entries if e.get("level") is not None})
        venues = sorted({e.get("venue_code", e.get("venue", "")) for e in filtered_entries} - {""})

        return {
            "preview_id": preview_id,
            "entries": filtered_entries,
            "conflicts": conflicts,
            "warnings": master_warnings,
            "summary": {
                "entry_count": len(filtered_entries),
                "levels": levels,
                "venues": venues,
                "conflict_count": len(conflicts),
                "warning_count": len(master_warnings),
            },
        }

    async def publish_department_timetable(
        self,
        preview_id: str,
        uploaded_by_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Persist department entries on their semester's master timetable."""
        preview_data = await self._load_preview(preview_id)
        semester_id = uuid.UUID(preview_data["semester_id"])
        department_id = uuid.UUID(preview_data["department_id"])
        category = preview_data.get("category", "undergraduate")
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
                    category=category,
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
                    start_time=entry.get("start_time"),
                    end_time=entry.get("end_time"),
                    programme=entry.get("programme") or None,
                    lecturer_name=entry.get("lecturer_name") or None,
                    course_title=entry.get("course_title") or None,
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
                category=category,
                department_id=department_id,
            ))

        venue_codes = {e.get("venue_code", "") for e in entries}

        await self.db.commit()
        await self.redis.delete(f"timetable_preview:{preview_id}")
        return {"message": "Department timetable published successfully", "venue_codes": venue_codes}

    async def export_timetable(
        self,
        semester_id: uuid.UUID,
        level: Optional[int] = None,
        category: Optional[str] = None,
        programme: Optional[str] = None,
        cohort: Optional[str] = None,
    ) -> str:
        """Export timetable as CSV"""
        entries, _ = await self.get_entries(semester_id, level, category=category, programme=programme, cohort=cohort)

        lines = ["Level,Day,Time,Subject,Venue,Programme"]
        for entry in entries:
            time = f"{entry['period_start']}-{entry['period_end']}"
            prog = entry.get('programme') or ''
            lines.append(f"{entry['level']},{entry['day']},{time},{entry['subject']},{entry['venue_code']},{prog}")

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
                "category": upload.category,
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

    async def _check_master_compatibility(
        self,
        semester_id: uuid.UUID,
        entries: List[Dict],
    ) -> List[Dict]:
        """Validate department entries against master timetable allocations.

        For each department entry at (day, period, level), checks that its
        subject prefix matches a master entry at the same slot.  Returns
        warnings for mismatches (e.g. master has DCIT but dept entry is EASC111).
        """
        master_entries = await self.repo.get_entries(
            semester_id=semester_id,
            source="master",
        )

        master_lookup: Dict[tuple, List[Dict]] = defaultdict(list)
        for me in master_entries:
            if me.is_free:
                continue
            key = (me.day, me.period, me.level)
            master_lookup[key].append({
                "subject": me.subject,
                "prefix": _extract_subject_prefix(me.subject),
                "venue_code": me.venue_code,
            })

        warnings: List[Dict] = []
        for entry in entries:
            if entry.get("is_free"):
                continue

            dept_prefix = _extract_subject_prefix(entry["subject"])
            level = entry.get("level", 0)
            key = (entry["day"], entry["period"], level)
            masters_at_slot = master_lookup.get(key, [])

            if not masters_at_slot:
                continue

            if any(m["prefix"] == dept_prefix for m in masters_at_slot):
                continue

            master_subjects = [m["subject"] for m in masters_at_slot]
            day_name = DAY_NAMES[entry["day"]] if 0 <= entry["day"] < len(DAY_NAMES) else f"Day {entry['day']}"
            warnings.append({
                "type": "master_mismatch",
                "severity": "error",
                "level": level,
                "day": entry["day"],
                "day_name": day_name,
                "period": entry["period"],
                "department_subject": entry["subject"],
                "department_venue": entry.get("venue_code", ""),
                "master_subjects": master_subjects,
                "message": (
                    f"{entry['subject']} at {day_name} period {entry['period'] + 1} (L{level}) "
                    f"does not match master allocation: {', '.join(master_subjects)}"
                ),
            })

        return warnings

    async def _check_department_conflicts(
        self,
        semester_id: uuid.UUID,
        department_id: uuid.UUID,
        entries: List[Dict],
    ) -> List[Dict]:
        """Check for venue clashes between new department entries and
        existing *other* department entries.

        Master entries (department_id IS NULL) are excluded because they
        carry broad department codes (e.g. "DCIT") that would false-
        positive against specific course codes (e.g. "DCIT111").
        The uploading department's own existing entries are also excluded
        since they will be replaced on publish.
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
                        MasterEntry.department_id.isnot(None),
                        MasterEntry.department_id != department_id,
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
                    "existing_department_id": str(ex.department_id),
                })

        return conflicts
