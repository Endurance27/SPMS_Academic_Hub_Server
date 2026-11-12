import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File, status
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
from app.schemas.timetable_personal import MasterEntryDetailResponse
from app.schemas.pagination import PaginationMeta
from app.services.master_timetable_service import MasterTimetableService, sync_venues_from_codes
from app.services.personal_timetable_service import PersonalTimetableService

router = APIRouter()


# ── Static GET paths (must come before /{timetable_id}) ─────────────

@router.get("", response_model=TimetableListResponse)
async def list_timetables(
    semester_id: uuid.UUID = Query(...),
    category: Optional[str] = Query(None, description="Filter by 'undergraduate' or 'postgraduate'"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List uploaded master timetables"""
    service = MasterTimetableService(db)
    timetables = await service.list_timetables(semester_id, category=category)
    total = len(timetables)
    start = (page - 1) * page_size
    paged = timetables[start:start + page_size]
    return TimetableListResponse(
        data=paged,
        meta=PaginationMeta.build(page, page_size, total),
    )


@router.get("/entries", response_model=TimetableEntriesResponse)
async def get_timetable_entries(
    semester_id: uuid.UUID = Query(...),
    level: Optional[int] = Query(None),
    venue: Optional[str] = Query(None),
    subjects: Optional[str] = Query(None),
    day: Optional[int] = Query(None),
    category: Optional[str] = Query(None, description="Filter by 'undergraduate' or 'postgraduate'"),
    programme: Optional[str] = Query(None, description="Filter PG entries by programme (e.g. 'CS', 'ITB', 'DS', 'AI & ML', 'NET')"),
    cohort: Optional[str] = Query(None, description="Filter PG entries by cohort: 'evening' (Mon-Fri), 'weekend_saturday' (Fri+Sat), 'weekend_sunday' (Fri+Sun)"),
    course_kind: Optional[str] = Query(None, description="Filter by course type: 'C' (Core), 'E' (Elective), 'R' (Required/Seminar), 'S' (Special)"),
    current_user: User = Depends(require_permission("timetable.view")),
    db: AsyncSession = Depends(get_db)
):
    """Get all timetable entries (master + department combined)"""
    service = MasterTimetableService(db)
    subjects_list = subjects.split(",") if subjects else None

    entries, meta = await service.get_entries(
        semester_id=semester_id,
        level=level,
        venue_code=venue,
        subjects=subjects_list,
        day=day,
        category=category,
        programme=programme,
        cohort=cohort,
        course_kind=course_kind,
    )
    return TimetableEntriesResponse(data=entries, meta=meta)


@router.get("/master-entries", response_model=TimetableEntriesResponse)
async def get_master_only_entries(
    semester_id: uuid.UUID = Query(...),
    level: Optional[int] = Query(None),
    venue: Optional[str] = Query(None),
    subjects: Optional[str] = Query(None),
    day: Optional[int] = Query(None),
    category: Optional[str] = Query(None, description="Filter by 'undergraduate' or 'postgraduate'"),
    programme: Optional[str] = Query(None, description="Filter PG entries by programme (e.g. 'CS', 'ITB', 'DS', 'AI & ML', 'NET')"),
    cohort: Optional[str] = Query(None, description="Filter PG entries by cohort: 'evening' (Mon-Fri), 'weekend_saturday' (Fri+Sat), 'weekend_sunday' (Fri+Sun)"),
    course_kind: Optional[str] = Query(None, description="Filter by course type: 'C' (Core), 'E' (Elective), 'R' (Required/Seminar), 'S' (Special)"),
    current_user: User = Depends(require_permission("timetable.view")),
    db: AsyncSession = Depends(get_db),
):
    """Get master timetable entries only (broad department codes like DCIT, MATH, STAT)"""
    service = MasterTimetableService(db)
    subjects_list = subjects.split(",") if subjects else None

    entries, meta = await service.get_entries(
        semester_id=semester_id,
        level=level,
        venue_code=venue,
        subjects=subjects_list,
        day=day,
        source="master",
        category=category,
        programme=programme,
        cohort=cohort,
        course_kind=course_kind,
    )
    return TimetableEntriesResponse(data=entries, meta=meta)


@router.get("/department-entries", response_model=TimetableEntriesResponse)
async def get_department_entries(
    semester_id: uuid.UUID = Query(...),
    department_id: Optional[uuid.UUID] = Query(None),
    level: Optional[int] = Query(None),
    venue: Optional[str] = Query(None),
    subjects: Optional[str] = Query(None),
    day: Optional[int] = Query(None),
    category: Optional[str] = Query(None, description="Filter by 'undergraduate' or 'postgraduate'"),
    programme: Optional[str] = Query(None, description="Filter PG entries by programme (e.g. 'CS', 'ITB', 'DS', 'AI & ML', 'NET')"),
    cohort: Optional[str] = Query(None, description="Filter PG entries by cohort: 'evening' (Mon-Fri), 'weekend_saturday' (Fri+Sat), 'weekend_sunday' (Fri+Sun)"),
    course_kind: Optional[str] = Query(None, description="Filter by course type: 'C' (Core), 'E' (Elective), 'R' (Required/Seminar), 'S' (Special)"),
    current_user: User = Depends(require_permission("timetable.view")),
    db: AsyncSession = Depends(get_db),
):
    """Get department timetable entries (specific courses like DCIT111, MATH201)"""
    service = MasterTimetableService(db)
    subjects_list = subjects.split(",") if subjects else None

    entries, meta = await service.get_entries(
        semester_id=semester_id,
        level=level,
        venue_code=venue,
        subjects=subjects_list,
        day=day,
        source="department",
        department_id=department_id,
        category=category,
        programme=programme,
        cohort=cohort,
        course_kind=course_kind,
    )
    return TimetableEntriesResponse(data=entries, meta=meta)


@router.get("/template")
async def get_timetable_template():
    """Get sample CSV template"""
    from fastapi.responses import Response

    csv_content = """Level,Day,Time,Subject,Venue
400,Monday,07:30-08:20,DCIT101,JQB09
400,Monday,08:30-09:20,DCIT101,JQB09
400,Monday,09:30-10:20,FREE,JQB09
400,Tuesday,07:30-08:20,MATH301,NNB1
600,Monday,07:30-08:20,DCIT601,JQB12
600,Monday,08:30-09:20,FREE,JQB12
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
    category: Optional[str] = Query(None, description="Filter by 'undergraduate' or 'postgraduate'"),
    programme: Optional[str] = Query(None, description="Filter PG entries by programme"),
    cohort: Optional[str] = Query(None, description="Filter PG entries by cohort: 'evening', 'weekend_saturday', 'weekend_sunday'"),
    current_user: User = Depends(require_permission("timetable.view")),
    db: AsyncSession = Depends(get_db)
):
    """Export master timetable as CSV"""
    from fastapi.responses import Response

    service = MasterTimetableService(db)
    csv_content = await service.export_timetable(semester_id, level, category=category, programme=programme, cohort=cohort)

    filename = f"semester-{semester_id}"
    if level:
        filename += f"-L{level}"
    if programme:
        filename += f"-{programme}"
    filename += "-master-timetable.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/history")
async def get_upload_history(
    semester_id: uuid.UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("timetable.view")),
    db: AsyncSession = Depends(get_db)
):
    """Get timetable upload history"""
    service = MasterTimetableService(db)
    history = await service.get_upload_history(semester_id)
    total = len(history)
    start = (page - 1) * page_size
    paged = history[start:start + page_size]
    return {
        "data": paged,
        "meta": PaginationMeta.build(page, page_size, total),
    }


@router.get("/double-bookings")
async def get_double_bookings(
    semester_id: uuid.UUID = Query(...),
    source: Optional[str] = Query(
        None, description="Filter by source: 'master', 'department', or omit for department-only (default)"
    ),
    category: Optional[str] = Query(None, description="Filter by 'undergraduate' or 'postgraduate'"),
    current_user: User = Depends(require_permission("timetable.view")),
    db: AsyncSession = Depends(get_db),
):
    """Find venue cells where multiple distinct subjects are booked.

    Defaults to checking department entries only, since master entries
    carry broad codes (DCIT) that would false-positive against specific
    department courses (DCIT111).
    """
    from sqlalchemy.future import select
    from sqlalchemy import func
    from app.models.master_timetable import MasterTimetable, MasterEntry

    tt_query = select(MasterTimetable.id).where(MasterTimetable.semester_id == semester_id)
    if category:
        tt_query = tt_query.where(MasterTimetable.category == category)
    result = await db.execute(tt_query)
    timetable_ids = [row[0] for row in result.all()]
    if not timetable_ids:
        return {"data": []}

    filters = [
        MasterEntry.timetable_id.in_(timetable_ids),
        MasterEntry.venue_code.notin_(["DEPT", "ONLINE"]),
    ]

    check_source = source or "department"
    if check_source == "master":
        filters.append(MasterEntry.department_id.is_(None))
    elif check_source == "department":
        filters.append(MasterEntry.department_id.isnot(None))

    result = await db.execute(
        select(
            MasterEntry.venue_code,
            MasterEntry.day,
            MasterEntry.period,
            func.array_agg(func.distinct(MasterEntry.subject)),
            func.count(func.distinct(MasterEntry.subject)),
        )
        .where(*filters)
        .group_by(MasterEntry.venue_code, MasterEntry.day, MasterEntry.period)
        .having(func.count(func.distinct(MasterEntry.subject)) > 1)
    )

    bookings = [
        {"venue": row[0], "day": row[1], "period": row[2], "subjects": row[3]}
        for row in result.all()
    ]
    return {"data": bookings}


# ── Dynamic path routes ─────────────────────────────────────────────

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


@router.delete("/{timetable_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_timetable(
    timetable_id: uuid.UUID,
    current_user: User = Depends(require_permission("timetable.upload")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a master timetable and all its entries."""
    service = MasterTimetableService(db)
    deleted = await service.delete_timetable(timetable_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Timetable not found")


# ── POST routes (no path conflict) ─────────────────────────────────

@router.post("/preview", response_model=TimetablePreviewResponse)
async def preview_timetable(
    file: UploadFile = File(...),
    semester_id: uuid.UUID = Query(...),
    level: Optional[int] = Query(None, description="Level to parse (e.g. 100-400 for UG, 500+ for PG). Omit to parse all levels."),
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
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(sync_venues_from_codes, result["venue_codes"])

    return {"message": result["message"]}


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
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(sync_venues_from_codes, result["venue_codes"])

    return {"message": result["message"]}


# ── Entry-level CRUD (sub-path with {entry_id}) ────────────────────

@router.get("/entries/{entry_id}", response_model=dict)
async def get_entry_detail(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single timetable entry by ID with enriched details (course, lecturer, department, venue)."""
    service = PersonalTimetableService(db)
    data = await service.get_entry_detail(entry_id)
    if not data:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"data": MasterEntryDetailResponse(**data).model_dump()}


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
