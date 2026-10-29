import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_redis
from app.core.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.master_timetable import (
    DepartmentTimetablePreviewResponse,
    TimetablePreviewResponse,
    TimetablePublishRequest,
    TimetableListResponse,
    TimetableEntriesResponse,
)
from app.services.master_timetable_service import MasterTimetableService

router = APIRouter()


@router.get("", response_model=TimetableListResponse)
async def list_timetables(
    semester_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """List uploaded master timetables"""
    service = MasterTimetableService(db)
    timetables = await service.list_timetables(semester_id)
    return TimetableListResponse(data=timetables)


@router.get("/{timetable_id}")
async def get_timetable_detail(
    timetable_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get one timetable and its course, day, period, and venue entries."""
    service = MasterTimetableService(db)
    timetable = await service.get_timetable_detail(timetable_id)
    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable not found")
    return {"data": timetable}


@router.get("/entries", response_model=TimetableEntriesResponse)
async def get_timetable_entries(
    semester_id: uuid.UUID = Query(...),
    level: Optional[int] = Query(None),
    venue: Optional[str] = Query(None),
    subjects: Optional[str] = Query(None),
    day: Optional[int] = Query(None),
    current_user: User = Depends(require_permission("timetable.view")),
    db: AsyncSession = Depends(get_db)
):
    """Get master timetable entries"""
    service = MasterTimetableService(db)
    subjects_list = subjects.split(",") if subjects else None

    entries, meta = await service.get_entries(
        semester_id=semester_id,
        level=level,
        venue_code=venue,
        subjects=subjects_list,
        day=day
    )
    return TimetableEntriesResponse(data=entries, meta=meta)


@router.post("/preview", response_model=TimetablePreviewResponse)
async def preview_timetable(
    file: UploadFile = File(...),
    semester_id: uuid.UUID = Query(...),
    level: Optional[int] = Query(None, description="Level to parse (100-400). Omit to parse all levels."),
    current_user: User = Depends(require_permission("timetable.upload")),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Preview master timetable upload.

    For Excel files with multiple sheets (L100v1, L200v1, ...) omit
    ``level`` to parse every sheet, or pass a specific level to parse
    only that sheet.
    """
    service = MasterTimetableService(db, redis)

    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.csv')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload the master timetable as an Excel (.xlsx) or CSV file"
        )

    content = await file.read()
    file_type = file.filename.lower().split('.')[-1]

    result = await service.preview_upload(
        content=content,
        file_type=file_type,
        semester_id=semester_id,
        level=level or 0,
        filename=file.filename
    )

    return result


@router.post("/publish", status_code=status.HTTP_200_OK)
async def publish_timetable(
    data: TimetablePublishRequest,
    current_user: User = Depends(require_permission("timetable.upload")),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Publish master timetable"""
    service = MasterTimetableService(db, redis)

    result = await service.publish_timetable(
        preview_id=data.preview_id,
        uploaded_by_id=current_user.id
    )

    return {"message": result}


@router.post("/department/preview", response_model=DepartmentTimetablePreviewResponse)
async def preview_department_timetable(
    file: UploadFile = File(...),
    semester_id: uuid.UUID = Query(...),
    department_id: uuid.UUID = Query(...),
    current_user: User = Depends(require_permission("timetable.department_upload")),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Preview department timetable upload"""
    service = MasterTimetableService(db, redis)

    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.csv')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload the department timetable as an Excel (.xlsx) or CSV file"
        )

    content = await file.read()
    file_type = file.filename.lower().split('.')[-1]

    result = await service.preview_department_upload(
        content=content,
        file_type=file_type,
        semester_id=semester_id,
        department_id=department_id,
        filename=file.filename
    )

    return result


@router.post("/department/publish", status_code=status.HTTP_200_OK)
async def publish_department_timetable(
    data: TimetablePublishRequest,
    current_user: User = Depends(require_permission("timetable.department_upload")),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Publish department timetable"""
    service = MasterTimetableService(db, redis)

    result = await service.publish_department_timetable(
        preview_id=data.preview_id,
        uploaded_by_id=current_user.id
    )

    return {"message": result}


@router.get("/template")
async def get_timetable_template():
    """Get sample CSV template"""
    from fastapi.responses import Response

    csv_content = """Level,Day,Time,Subject,Venue
400,Monday,07:30-08:20,DCIT101,JQB09
400,Monday,08:30-09:20,DCIT101,JQB09
400,Monday,09:30-10:20,FREE,JQB09
400,Tuesday,07:30-08:20,MATH301,NNB1
"""

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=master-timetable-template.csv"}
    )


@router.get("/export")
async def export_timetable(
    semester_id: uuid.UUID = Query(...),
    level: Optional[int] = Query(None),
    current_user: User = Depends(require_permission("timetable.view")),
    db: AsyncSession = Depends(get_db)
):
    """Export master timetable as CSV"""
    from fastapi.responses import Response

    service = MasterTimetableService(db)
    csv_content = await service.export_timetable(semester_id, level)

    filename = f"semester-{semester_id}"
    if level:
        filename += f"-L{level}"
    filename += "-master-timetable.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/history")
async def get_upload_history(
    semester_id: uuid.UUID = Query(...),
    current_user: User = Depends(require_permission("timetable.view")),
    db: AsyncSession = Depends(get_db)
):
    """Get timetable upload history"""
    service = MasterTimetableService(db)
    history = await service.get_upload_history(semester_id)
    return {"data": history}


@router.patch("/entries/{entry_id}")
async def update_entry(
    entry_id: uuid.UUID,
    subject: Optional[str] = None,
    venue_code: Optional[str] = None,
    is_free: Optional[bool] = None,
    current_user: User = Depends(require_permission("timetable.edit")),
    db: AsyncSession = Depends(get_db)
):
    """Update a master timetable entry"""
    from sqlalchemy.future import select
    from app.models.master_timetable import MasterEntry

    result = await db.execute(select(MasterEntry).where(MasterEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    if is_free:
        entry.subject = "FREE"
        entry.is_free = True
    elif subject is not None:
        entry.subject = subject.upper().strip()
        entry.is_free = entry.subject == "FREE"
    if venue_code is not None:
        entry.venue_code = venue_code.upper().strip()

    await db.commit()
    await db.refresh(entry)
    return {"data": {"id": str(entry.id), "subject": entry.subject, "venue_code": entry.venue_code, "is_free": entry.is_free}}


@router.post("/entries", status_code=status.HTTP_201_CREATED)
async def create_entry(
    semester_id: uuid.UUID,
    level: int,
    day: int,
    period: int,
    subject: str,
    venue_code: str,
    current_user: User = Depends(require_permission("timetable.edit")),
    db: AsyncSession = Depends(get_db)
):
    """Create a new master timetable entry"""
    from sqlalchemy.future import select
    from app.models.master_timetable import MasterTimetable, MasterEntry

    result = await db.execute(
        select(MasterTimetable).where(
            MasterTimetable.semester_id == semester_id,
            MasterTimetable.level == level,
        )
    )
    timetable = result.scalar_one_or_none()
    if not timetable:
        raise HTTPException(status_code=404, detail="Master timetable not found for this semester and level")

    normalised_subject = subject.upper().strip()
    entry = MasterEntry(
        timetable_id=timetable.id,
        level=level,
        day=day,
        period=period,
        subject=normalised_subject,
        venue_code=venue_code.upper().strip(),
        is_free=normalised_subject == "FREE",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {"data": {"id": str(entry.id), "subject": entry.subject, "venue_code": entry.venue_code}}


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(require_permission("timetable.edit")),
    db: AsyncSession = Depends(get_db)
):
    """Delete a master timetable entry"""
    from sqlalchemy.future import select
    from app.models.master_timetable import MasterEntry

    result = await db.execute(select(MasterEntry).where(MasterEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    await db.delete(entry)
    await db.commit()


@router.get("/double-bookings")
async def get_double_bookings(
    semester_id: uuid.UUID = Query(...),
    current_user: User = Depends(require_permission("timetable.view")),
    db: AsyncSession = Depends(get_db)
):
    """Find cells with multiple subjects (excluding shared venues)"""
    from sqlalchemy.future import select
    from sqlalchemy import func
    from app.models.master_timetable import MasterTimetable, MasterEntry

    result = await db.execute(
        select(MasterTimetable.id).where(MasterTimetable.semester_id == semester_id)
    )
    timetable_ids = [row[0] for row in result.all()]
    if not timetable_ids:
        return {"data": []}

    result = await db.execute(
        select(
            MasterEntry.venue_code,
            MasterEntry.day,
            MasterEntry.period,
            func.array_agg(func.distinct(MasterEntry.subject)),
            func.count(func.distinct(MasterEntry.subject)),
        )
        .where(
            MasterEntry.timetable_id.in_(timetable_ids),
            MasterEntry.venue_code.notin_(["DEPT", "ONLINE"]),
        )
        .group_by(MasterEntry.venue_code, MasterEntry.day, MasterEntry.period)
        .having(func.count(func.distinct(MasterEntry.subject)) > 1)
    )

    bookings = [
        {"venue": row[0], "day": row[1], "period": row[2], "subjects": row[3]}
        for row in result.all()
    ]
    return {"data": bookings}


