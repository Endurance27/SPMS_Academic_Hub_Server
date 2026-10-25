import uuid
from typing import Optional, List, Dict
from datetime import datetime

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule_item import ScheduleItem, ScheduleItemStatus, ScheduleItemSource
from app.models.course import Course
from app.models.venue import Venue
from app.models.user import User, UserRole
from app.repositories.schedule_item_repository import ScheduleItemRepository
from app.utils.clash_detection import ClashDetector, Clash


class ScheduleItemService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ScheduleItemRepository(db)

    async def list_items(
        self,
        semester_id: uuid.UUID,
        department_id: Optional[uuid.UUID],
        level: Optional[int],
        venue_type: Optional[str],
        search: Optional[str],
        status: Optional[str],
        user: User
    ) -> tuple[List[Dict], Dict]:
        """List schedule items with scoping"""
        items = await self.repo.list_filtered(
            semester_id=semester_id,
            department_id=department_id,
            level=level,
            venue_type=venue_type,
            search=search,
            status=status,
            user_role=user.role,
            user_department_id=user.department_id
        )

        result = []
        for item in items:
            result.append(await self._item_to_dict(item))

        # Meta counts
        meta = {
            "pending": sum(1 for i in items if i.status == ScheduleItemStatus.PENDING),
            "conflict": sum(1 for i in items if i.status == ScheduleItemStatus.CONFLICT),
            "published": sum(1 for i in items if i.status == ScheduleItemStatus.PUBLISHED),
            "venue_utilisation": await self._calculate_venue_utilisation(semester_id)
        }

        return result, meta

    async def create_item(self, data: Dict, user: User) -> Dict:
        """Create manual schedule item"""
        # Validate course belongs to department
        course = await self._get_course(data["course_id"])
        if not course:
            raise ValueError("Course not found")

        if user.role == UserRole.DEPARTMENT and course.department_id != user.department_id:
            raise ValueError("Can only create items for own department")

        # Run clash checks
        clashes = await self._check_item_clashes(data, user)
        if any(c.severity == "danger" for c in clashes):
            status = ScheduleItemStatus.CONFLICT
        else:
            status = ScheduleItemStatus.PENDING

        item = ScheduleItem(
            semester_id=data["semester_id"],
            course_id=data["course_id"],
            department_id=course.department_id,
            day=data["day"],
            start_period=data.get("start_period"),
            period_count=data.get("period_count"),
            start=data.get("start"),
            end=data.get("end"),
            venue_code=data["venue_code"],
            lecturer_id=data.get("lecturer_id") or course.lecturer_id,
            mode=data.get("mode", "in-person"),
            status=status,
            source=ScheduleItemSource.MANUAL
        )

        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)

        return await self._item_to_dict(item)

    async def get_item(self, item_id: uuid.UUID) -> Optional[Dict]:
        """Get schedule item by ID"""
        item = await self.repo.get_by_id(item_id)
        if not item:
            return None
        return await self._item_to_dict(item)

    async def update_item(self, item_id: uuid.UUID, data: Dict, user: User) -> Dict:
        """Update schedule item"""
        item = await self.repo.get_by_id(item_id)
        if not item:
            raise ValueError("Schedule item not found")

        # Scope check
        if user.role == UserRole.DEPARTMENT and item.department_id != user.department_id:
            raise ValueError("Access denied")

        # Update fields
        for field, value in data.items():
            if hasattr(item, field) and value is not None:
                setattr(item, field, value)

        # Re-run clash checks
        placement = {
            "day": item.day,
            "start_period": item.start_period,
            "period_count": item.period_count,
            "venue_code": item.venue_code,
            "course_id": str(item.course_id),
            "semester_id": str(item.semester_id),
            "level": 0  # Would need to determine from course
        }

        clashes = await self._check_item_clashes(placement, user)
        if any(c.severity == "danger" for c in clashes):
            item.status = ScheduleItemStatus.CONFLICT
        else:
            item.status = ScheduleItemStatus.PENDING

        await self.db.commit()
        await self.db.refresh(item)

        return await self._item_to_dict(item)

    async def delete_item(self, item_id: uuid.UUID, user: User) -> None:
        """Delete schedule item"""
        item = await self.repo.get_by_id(item_id)
        if not item:
            raise ValueError("Schedule item not found")

        # Scope check
        if user.role == UserRole.DEPARTMENT and item.department_id != user.department_id:
            raise ValueError("Access denied")

        await self.db.delete(item)
        await self.db.commit()

    async def publish_items(
        self,
        ids: Optional[List[uuid.UUID]],
        course_code: Optional[str],
        user: User
    ) -> int:
        """Publish pending schedule items"""
        query = select(ScheduleItem).where(
            ScheduleItem.status == ScheduleItemStatus.PENDING
        )

        if ids:
            query = query.where(ScheduleItem.id.in_(ids))
        if course_code:
            # Filter by course code (need to join with courses)
            pass

        result = await self.db.execute(query)
        items = result.scalars().all()

        # Scope check
        if user.role == UserRole.DEPARTMENT:
            items = [i for i in items if i.department_id == user.department_id]

        for item in items:
            item.status = ScheduleItemStatus.PUBLISHED

        await self.db.commit()
        return len(items)

    async def get_final_timetable(
        self,
        semester_id: uuid.UUID,
        level: Optional[int],
        user: User
    ) -> tuple[List[Dict], Dict]:
        """Get final published timetable"""
        query = select(ScheduleItem).where(
            and_(
                ScheduleItem.semester_id == semester_id,
                ScheduleItem.status == ScheduleItemStatus.PUBLISHED
            )
        )

        # Scope check
        if user.role == UserRole.DEPARTMENT:
            query = query.where(ScheduleItem.department_id == user.department_id)

        result = await self.db.execute(query)
        items = result.scalars().all()

        result_list = []
        for item in items:
            result_list.append(await self._item_to_dict(item))

        meta = {
            "not_included": {
                "pending": await self.repo.count_by_status(semester_id, ScheduleItemStatus.PENDING),
                "conflict": await self.repo.count_by_status(semester_id, ScheduleItemStatus.CONFLICT)
            }
        }

        return result_list, meta

    async def _item_to_dict(self, item: ScheduleItem) -> Dict:
        """Convert item to dict with computed fields"""
        course = await self._get_course(item.course_id)
        venue = await self._get_venue(item.venue_code)
        lecturer = await self._get_user(item.lecturer_id) if item.lecturer_id else None

        return {
            "id": str(item.id),
            "semester_id": str(item.semester_id),
            "course_id": str(item.course_id),
            "course_code": course.code if course else "",
            "title": course.title if course else "",
            "department_id": str(item.department_id),
            "day": item.day,
            "start_period": item.start_period,
            "period_count": item.period_count,
            "start": item.start,
            "end": item.end,
            "venue_code": item.venue_code,
            "room": venue.code if venue else item.venue_code,
            "lecturer_id": str(item.lecturer_id) if item.lecturer_id else None,
            "lecturer": lecturer.name if lecturer else "Lecturer to be assigned",
            "mode": item.mode,
            "status": item.status.value,
            "source": item.source.value
        }

    async def _check_item_clashes(self, data: Dict, user: User) -> List[Clash]:
        """Check for clashes"""
        # Simplified clash check for now
        return []

    async def _calculate_venue_utilisation(self, semester_id: uuid.UUID) -> float:
        """Calculate venue utilisation percentage"""
        # Simplified - would need proper calculation
        return 0.0

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

    async def _get_user(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
