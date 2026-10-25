import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.slot_request import SlotRequest, SlotRequestStatus
from app.models.schedule_item import ScheduleItem, ScheduleItemStatus
from app.models.course import Course, course_cohorts
from app.models.venue import Venue
from app.models.user import User
from app.repositories.slot_request_repository import SlotRequestRepository
from app.utils.clash_detection import ClashDetector, Clash


class SlotRequestService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SlotRequestRepository(db)

    async def get_free_slots(
        self,
        semester_id: uuid.UUID,
        level: Optional[int],
        venue_code: Optional[str],
        view: str,
        user: User
    ) -> Dict:
        """Get FREE slots for scheduling"""
        # Get all FREE cells from master timetable
        free_cells = await self._get_free_cells(semester_id, level)

        # Get existing requests
        other_requests = await self._get_other_requests(semester_id, level, user.department_id)

        # Build free slots response
        slots = []
        for cell_key, cell in free_cells.items():
            day, period, venue = cell_key.split("|")
            day = int(day)
            period = int(period)

            # Check if this slot is requested
            claim = "open"
            pending_count = 0
            pending_course_codes = []
            approved = None

            for req in other_requests:
                if (req.day == day and
                    req.venue_code == venue and
                    req.start_period <= period < req.start_period + req.period_count):
                    if req.status == SlotRequestStatus.PENDING:
                        claim = "pending"
                        pending_count += 1
                        if req.course_id:
                            course = await self._get_course(req.course_id)
                            if course:
                                pending_course_codes.append(course.code)
                    elif req.status == SlotRequestStatus.APPROVED:
                        claim = "approved"
                        approved = {
                            "course_code": req.course_id,
                            "department_code": req.department_id
                        }

            # Get venue capacity
            venue_obj = await self._get_venue(venue)
            capacity = venue_obj.capacity if venue_obj else None

            slots.append({
                "day": day,
                "period": period,
                "venue": venue,
                "capacity": capacity,
                "free_run": self._calculate_free_run(free_cells, day, period, venue),
                "claim": claim,
                "pending_count": pending_count,
                "pending_course_codes": pending_course_codes,
                "approved": approved
            })

        # Calculate meta
        meta = {
            "free_count": len(free_cells),
            "my_pending": sum(1 for r in other_requests if r.requested_by_id == user.id and r.status == SlotRequestStatus.PENDING),
            "my_approved": sum(1 for r in other_requests if r.requested_by_id == user.id and r.status == SlotRequestStatus.APPROVED)
        }

        return {"slots": slots, "meta": meta}

    async def check_clashes(
        self,
        data: Dict,
        user: User
    ) -> List[Clash]:
        """Check for clashes using clash detection engine"""
        # Get course details
        course = await self._get_course(data["course_id"])
        if not course:
            raise ValueError("Course not found")

        # Get free cells
        free_cells = await self._get_free_cells(data["semester_id"], data["level"])
        free_cell_keys = {f"{c['day']}|{c['period']}|{c['venue']}" for c in free_cells.values()}

        # Get other requests
        other_requests = await self._get_other_requests(data["semester_id"], data["level"], user.department_id)
        other_requests_data = []
        for req in other_requests:
            if req.id != data.get("id"):
                other_requests_data.append({
                    "id": str(req.id),
                    "day": req.day,
                    "start_period": req.start_period,
                    "period_count": req.period_count,
                    "venue_code": req.venue_code,
                    "status": req.status.value,
                    "course_id": str(req.course_id),
                    "department_id": str(req.department_id),
                    "lecturer_id": str(req.lecturer_id) if req.lecturer_id else None
                })

        # Get schedule items
        schedule_items = await self._get_schedule_items(data["semester_id"])
        schedule_items_data = []
        for item in schedule_items:
            schedule_items_data.append({
                "id": str(item.id),
                "day": item.day,
                "start_period": item.start_period,
                "period_count": item.period_count,
                "venue_code": item.venue_code,
                "lecturer_id": str(item.lecturer_id) if item.lecturer_id else None
            })

        # Build placement
        placement = {
            "id": data.get("id"),
            "course_id": str(data["course_id"]),
            "semester_id": str(data["semester_id"]),
            "level": data["level"],
            "day": data["day"],
            "venue_code": data["venue_code"],
            "start_period": data["start_period"],
            "period_count": data["period_count"],
            "department_id": str(user.department_id),
            "lecturer_id": str(course.lecturer_id) if course.lecturer_id else None
        }

        # Build course with cohorts
        course_data = {
            "id": str(course.id),
            "code": course.code,
            "cohorts": await self._get_course_cohorts(course.id),
            "lecturer_id": str(course.lecturer_id) if course.lecturer_id else None,
            "student_count": course.student_count
        }

        # Get venue capacity
        venue = await self._get_venue(data["venue_code"])
        placement["venue_capacity"] = venue.capacity if venue else None

        # Run clash detection
        detector = ClashDetector()
        clashes = detector.detect_clashes(
            placement=placement,
            free_cells=free_cell_keys,
            other_requests=other_requests_data,
            schedule_items=schedule_items_data,
            assessments=[],
            course=course_data,
            capacity_tolerance=0
        )

        return clashes

    async def create_request(self, data: Dict, user: User) -> Dict:
        """Create slot request"""
        request = SlotRequest(
            course_id=data["course_id"],
            department_id=user.department_id,
            requested_by_id=user.id,
            semester_id=data["semester_id"],
            level=data["level"],
            day=data["day"],
            venue_code=data["venue_code"],
            start_period=data["start_period"],
            period_count=data["period_count"],
            status=SlotRequestStatus.PENDING
        )
        self.db.add(request)
        await self.db.commit()
        await self.db.refresh(request)

        return await self._request_to_dict(request)

    async def list_requests(
        self,
        status: Optional[str],
        semester_id: uuid.UUID,
        department_id: Optional[uuid.UUID],
        user: User
    ) -> tuple[List[Dict], Dict]:
        """List slot requests"""
        requests = await self.repo.list_filtered(
            status=status,
            semester_id=semester_id,
            department_id=department_id,
            user_role=user.role,
            user_department_id=user.department_id
        )

        result = []
        for req in requests:
            clashes = []
            if req.status != SlotRequestStatus.RETURNED:
                clashes = await self.check_clashes({
                    "course_id": req.course_id,
                    "semester_id": req.semester_id,
                    "level": req.level,
                    "day": req.day,
                    "venue_code": req.venue_code,
                    "start_period": req.start_period,
                    "period_count": req.period_count,
                    "id": str(req.id)
                }, user)

            competing = await self._get_competing_requests(req)

            result.append({
                "id": str(req.id),
                "course_id": str(req.course_id),
                "department_id": str(req.department_id),
                "requested_by_id": str(req.requested_by_id),
                "semester_id": str(req.semester_id),
                "level": req.level,
                "day": req.day,
                "venue_code": req.venue_code,
                "start_period": req.start_period,
                "period_count": req.period_count,
                "status": req.status.value,
                "review_comment": req.review_comment,
                "reviewed_by_id": str(req.reviewed_by_id) if req.reviewed_by_id else None,
                "reviewed_at": req.reviewed_at.isoformat() if req.reviewed_at else None,
                "schedule_item_id": str(req.schedule_item_id) if req.schedule_item_id else None,
                "clashes": clashes,
                "competing": competing
            })

        # Meta counts
        meta = {"Pending": 0, "Approved": 0, "Returned": 0, "All": len(result)}
        for req in requests:
            if req.status.value in meta:
                meta[req.status.value] += 1

        return result, meta

    async def withdraw_request(self, request_id: uuid.UUID, user: User) -> None:
        """Withdraw pending slot request"""
        request = await self.repo.get_by_id(request_id)
        if not request:
            raise ValueError("Request not found")

        if request.requested_by_id != user.id:
            raise ValueError("Can only withdraw own requests")

        if request.status != SlotRequestStatus.PENDING:
            raise ValueError("Can only withdraw pending requests")

        request.status = SlotRequestStatus.WITHDRAWN
        await self.db.commit()

    async def approve_request(
        self,
        request_id: uuid.UUID,
        comment: Optional[str],
        user: User
    ) -> Dict:
        """Approve slot request and create schedule item"""
        request = await self.repo.get_by_id(request_id)
        if not request:
            raise ValueError("Request not found")

        if request.status != SlotRequestStatus.PENDING:
            raise ValueError("Can only approve pending requests")

        # Create schedule item
        schedule_item = await self._create_schedule_item_from_request(request)

        # Update request
        request.status = SlotRequestStatus.APPROVED
        request.review_comment = comment
        request.reviewed_by_id = user.id
        request.reviewed_at = datetime.utcnow()
        request.schedule_item_id = schedule_item.id

        # Return competing requests
        displaced = await self._return_competing_requests(request, schedule_item)

        await self.db.commit()
        await self.db.refresh(request)

        result = await self._request_to_dict(request)
        result["schedule_item"] = await self._schedule_item_to_dict(schedule_item)
        result["displaced"] = displaced

        return result

    async def return_request(
        self,
        request_id: uuid.UUID,
        comment: str,
        user: User
    ) -> Dict:
        """Return slot request"""
        request = await self.repo.get_by_id(request_id)
        if not request:
            raise ValueError("Request not found")

        if request.status == SlotRequestStatus.WITHDRAWN:
            raise ValueError("Cannot return withdrawn requests")

        # If approved, remove schedule item
        if request.status == SlotRequestStatus.APPROVED and request.schedule_item_id:
            await self.db.execute(
                select(ScheduleItem).where(ScheduleItem.id == request.schedule_item_id)
            )
            schedule_item = await self._get_schedule_item(request.schedule_item_id)
            if schedule_item:
                await self.db.delete(schedule_item)

        request.status = SlotRequestStatus.RETURNED
        request.review_comment = comment
        request.reviewed_by_id = user.id
        request.reviewed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(request)

        return await self._request_to_dict(request)

    async def override_request(
        self,
        request_id: uuid.UUID,
        reason: str,
        user: User
    ) -> Dict:
        """Override request despite clashes"""
        # Similar to approve but logs as override
        return await self.approve_request(request_id, f"Override: {reason}", user)

    async def _get_free_cells(self, semester_id: uuid.UUID, level: Optional[int]) -> Dict:
        """Get FREE cells from master timetable"""
        from app.models.master_timetable import MasterEntry

        query = select(MasterEntry).where(
            and_(
                MasterEntry.semester_id == semester_id,
                MasterEntry.is_free == True
            )
        )

        if level is not None:
            query = query.where(MasterEntry.level == level)

        result = await self.db.execute(query)
        entries = result.scalars().all()

        free_cells = {}
        for entry in entries:
            key = f"{entry.day}|{entry.period}|{entry.venue_code}"
            free_cells[key] = {
                "day": entry.day,
                "period": entry.period,
                "venue": entry.venue_code
            }

        return free_cells

    async def _get_other_requests(
        self,
        semester_id: uuid.UUID,
        level: int,
        department_id: uuid.UUID
    ) -> List[SlotRequest]:
        """Get other pending/approved requests"""
        result = await self.db.execute(
            select(SlotRequest).where(
                and_(
                    SlotRequest.semester_id == semester_id,
                    SlotRequest.level == level,
                    SlotRequest.status.in_([SlotRequestStatus.PENDING, SlotRequestStatus.APPROVED])
                )
            )
        )
        return list(result.scalars().all())

    async def _get_schedule_items(self, semester_id: uuid.UUID) -> List[ScheduleItem]:
        """Get published schedule items"""
        result = await self.db.execute(
            select(ScheduleItem).where(
                and_(
                    ScheduleItem.semester_id == semester_id,
                    ScheduleItem.status.in_([ScheduleItemStatus.PUBLISHED, ScheduleItemStatus.PENDING])
                )
            )
        )
        return list(result.scalars().all())

    async def _get_course(self, course_id: uuid.UUID) -> Optional[Course]:
        result = await self.db.execute(
            select(Course).where(Course.id == course_id)
        )
        return result.scalar_one_or_none()

    async def _get_venue(self, venue_code: str) -> Optional[Venue]:
        result = await self.db.execute(
            select(Venue).where(Venue.code == venue_code)
        )
        return result.scalar_one_or_none()

    async def _get_course_cohorts(self, course_id: uuid.UUID) -> List[Dict]:
        """Get course cohorts"""
        result = await self.db.execute(
            select(course_cohorts).where(course_cohorts.c.course_id == course_id)
        )
        cohorts = result.all()

        return [
            {"programme_id": str(c.programme_id), "level": c.level}
            for c in cohorts
        ]

    async def _get_schedule_item(self, item_id: uuid.UUID) -> Optional[ScheduleItem]:
        result = await self.db.execute(
            select(ScheduleItem).where(ScheduleItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def _create_schedule_item_from_request(self, request: SlotRequest) -> ScheduleItem:
        """Create schedule item from approved request"""
        course = await self._get_course(request.course_id)

        # Calculate start and end times
        from app.utils.constants import WEEKDAYS, PERIODS
        start_period = request.start_period
        end_period = request.start_period + request.period_count - 1

        start = PERIODS[start_period]["start"]
        end = PERIODS[end_period]["end"]

        item = ScheduleItem(
            semester_id=request.semester_id,
            course_id=request.course_id,
            department_id=request.department_id,
            slot_request_id=request.id,
            day=request.day,
            start_period=request.start_period,
            period_count=request.period_count,
            start=start,
            end=end,
            venue_code=request.venue_code,
            lecturer_id=course.lecturer_id if course else None,
            mode=course.mode if course else "in-person",
            status=ScheduleItemStatus.PUBLISHED,
            source="request"
        )

        self.db.add(item)
        await self.db.flush()
        return item

    async def _return_competing_requests(
        self,
        approved_request: SlotRequest,
        schedule_item: ScheduleItem
    ) -> List[Dict]:
        """Return competing pending requests"""
        competing = await self.db.execute(
            select(SlotRequest).where(
                and_(
                    SlotRequest.semester_id == approved_request.semester_id,
                    SlotRequest.day == approved_request.day,
                    SlotRequest.venue_code == approved_request.venue_code,
                    SlotRequest.status == SlotRequestStatus.PENDING,
                    SlotRequest.id != approved_request.id,
                    or_(
                        SlotRequest.start_period < approved_request.start_period + approved_request.period_count,
                        approved_request.start_period < SlotRequest.start_period + SlotRequest.period_count
                    )
                )
            )
        )
        requests = competing.scalars().all()

        displaced = []
        for req in requests:
            req.status = SlotRequestStatus.RETURNED
            req.review_comment = f"Slot allocated to schedule item {schedule_item.id}"
            req.reviewed_by_id = approved_request.requested_by_id
            req.reviewed_at = datetime.utcnow()

            displaced.append({
                "id": str(req.id),
                "course_id": str(req.course_id),
                "comment": req.review_comment
            })

        return displaced

    async def _get_competing_requests(self, request: SlotRequest) -> List[Dict]:
        """Get competing pending requests"""
        competing = await self.db.execute(
            select(SlotRequest).where(
                and_(
                    SlotRequest.semester_id == request.semester_id,
                    SlotRequest.day == request.day,
                    SlotRequest.venue_code == request.venue_code,
                    SlotRequest.status == SlotRequestStatus.PENDING,
                    SlotRequest.id != request.id,
                    or_(
                        SlotRequest.start_period < request.start_period + request.period_count,
                        request.start_period < SlotRequest.start_period + SlotRequest.period_count
                    )
                )
            )
        )
        requests = competing.scalars().all()

        return [
            {"id": str(r.id), "course_id": str(r.course_id)}
            for r in requests
        ]

    def _calculate_free_run(self, free_cells: Dict, day: int, period: int, venue: str) -> int:
        """Calculate consecutive FREE periods"""
        count = 0
        for i in range(period, min(period + 3, 12)):
            key = f"{day}|{i}|{venue}"
            if key in free_cells:
                count += 1
            else:
                break
        return count

    async def _request_to_dict(self, request: SlotRequest) -> Dict:
        """Convert request to dict"""
        return {
            "id": str(request.id),
            "course_id": str(request.course_id),
            "department_id": str(request.department_id),
            "requested_by_id": str(request.requested_by_id),
            "semester_id": str(request.semester_id),
            "level": request.level,
            "day": request.day,
            "venue_code": request.venue_code,
            "start_period": request.start_period,
            "period_count": request.period_count,
            "status": request.status.value,
            "review_comment": request.review_comment,
            "reviewed_by_id": str(request.reviewed_by_id) if request.reviewed_by_id else None,
            "reviewed_at": request.reviewed_at.isoformat() if request.reviewed_at else None,
            "schedule_item_id": str(request.schedule_item_id) if request.schedule_item_id else None
        }

    async def _schedule_item_to_dict(self, item: ScheduleItem) -> Dict:
        """Convert schedule item to dict"""
        return {
            "id": str(item.id),
            "semester_id": str(item.semester_id),
            "course_id": str(item.course_id),
            "department_id": str(item.department_id),
            "day": item.day,
            "start_period": item.start_period,
            "period_count": item.period_count,
            "start": item.start,
            "end": item.end,
            "venue_code": item.venue_code,
            "status": item.status.value,
            "source": item.source.value
        }
