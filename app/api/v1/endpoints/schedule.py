import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.schedule_item import (
    ScheduleItemCreate,
    ScheduleItemUpdate,
    ScheduleItemResponse,
    ScheduleItemListResponse
)
from app.services.schedule_item_service import ScheduleItemService

router = APIRouter()


@router.get("", response_model=ScheduleItemListResponse)
async def list_schedule_items(
    semester_id: uuid.UUID = Query(...),
    department_id: Optional[uuid.UUID] = Query(None),
    level: Optional[int] = Query(None),
    venue_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("schedule.view")),
    db: AsyncSession = Depends(get_db)
):
    """List schedule items"""
    service = ScheduleItemService(db)
    items, meta = await service.list_items(
        semester_id=semester_id,
        department_id=department_id,
        level=level,
        venue_type=venue_type,
        search=search,
        status=status,
        user=current_user
    )
    return ScheduleItemListResponse(data=items, meta=meta)


@router.post("", response_model=ScheduleItemResponse, status_code=201)
async def create_schedule_item(
    data: ScheduleItemCreate,
    current_user: User = Depends(require_permission("schedule.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Create manual schedule item"""
    service = ScheduleItemService(db)
    try:
        return await service.create_item(data, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{item_id}", response_model=ScheduleItemResponse)
async def get_schedule_item(
    item_id: uuid.UUID,
    current_user: User = Depends(require_permission("schedule.view")),
    db: AsyncSession = Depends(get_db)
):
    """Get schedule item by ID"""
    service = ScheduleItemService(db)
    item = await service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    return item


@router.patch("/{item_id}", response_model=ScheduleItemResponse)
async def update_schedule_item(
    item_id: uuid.UUID,
    data: ScheduleItemUpdate,
    current_user: User = Depends(require_permission("schedule.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Update schedule item"""
    service = ScheduleItemService(db)
    try:
        return await service.update_item(item_id, data, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{item_id}", status_code=204)
async def delete_schedule_item(
    item_id: uuid.UUID,
    current_user: User = Depends(require_permission("schedule.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Delete schedule item"""
    service = ScheduleItemService(db)
    await service.delete_item(item_id, current_user)


@router.post("/publish", status_code=200)
async def publish_schedule_items(
    ids: Optional[List[uuid.UUID]] = None,
    course_code: Optional[str] = None,
    current_user: User = Depends(require_permission("schedule.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Publish pending schedule items"""
    service = ScheduleItemService(db)
    count = await service.publish_items(ids, course_code, current_user)
    return {"message": f"{count} courses published"}


@router.get("/final", response_model=ScheduleItemListResponse)
async def get_final_timetable(
    semester_id: uuid.UUID = Query(...),
    level: Optional[int] = Query(None),
    current_user: User = Depends(require_permission("schedule.view")),
    db: AsyncSession = Depends(get_db)
):
    """Get final published timetable"""
    service = ScheduleItemService(db)
    items, meta = await service.get_final_timetable(semester_id, level, current_user)
    return ScheduleItemListResponse(data=items, meta=meta)


@router.get("/final/export")
async def export_final_timetable(
    semester_id: uuid.UUID = Query(...),
    level: Optional[int] = Query(None),
    current_user: User = Depends(require_permission("schedule.view")),
    db: AsyncSession = Depends(get_db)
):
    """Export final timetable as CSV"""
    import io
    import csv
    from fastapi.responses import StreamingResponse
    from sqlalchemy.future import select
    from sqlalchemy.orm import selectinload
    from app.models.schedule_item import ScheduleItem, ScheduleItemStatus

    query = (
        select(ScheduleItem)
        .options(selectinload(ScheduleItem.course), selectinload(ScheduleItem.lecturer))
        .where(ScheduleItem.semester_id == semester_id)
    )
    if current_user.department_id:
        query = query.where(ScheduleItem.department_id == current_user.department_id)
    if level:
        query = query.where(ScheduleItem.level == level)

    query = query.order_by(ScheduleItem.day, ScheduleItem.start, ScheduleItem.venue_code)
    result = await db.execute(query)
    items = result.scalars().all()

    WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    STATUS_LABELS = {"published": "Published", "pending": "Awaiting approval", "conflict": "Blocked by conflict"}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Course", "Title", "Day", "Start", "End", "Venue", "Lecturer", "Mode", "Student group", "Status"])
    for item in items:
        course_code = item.course.code if item.course else ""
        course_title = item.course.title if item.course else ""
        day_name = WEEKDAYS[item.day] if item.day is not None and item.day < len(WEEKDAYS) else ""
        lecturer_name = item.lecturer.name if item.lecturer else "Lecturer to be assigned"
        status_label = STATUS_LABELS.get(item.status.value if isinstance(item.status, ScheduleItemStatus) else item.status, str(item.status))
        groups = ", ".join(item.groups) if item.groups else ""
        writer.writerow([course_code, course_title, day_name, item.start or "", item.end or "", item.venue_code or "", lecturer_name, item.mode or "", groups, status_label])

    dept_code = current_user.department_id or "institution"
    level_str = f"L{level}" if level else "all-levels"
    filename = f"{dept_code}-{level_str}-final-timetable.csv"

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
