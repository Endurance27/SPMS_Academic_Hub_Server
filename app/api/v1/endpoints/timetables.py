import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.master_timetable import (
    TimetablePreviewResponse,
    TimetablePublishRequest,
    TimetableListResponse,
    TimetableEntriesResponse
)
from app.services.master_timetable_service import MasterTimetableService

router = APIRouter()


@router.get("", response_model=TimetableListResponse)
async def list_timetables(
    semester_id: uuid.UUID = Query(...),
    current_user: User = Depends(require_permission("timetable.view")),
    db: AsyncSession = Depends(get_db)
):
    """List uploaded master timetables"""
    service = MasterTimetableService(db)
    timetables = await service.list_timetables(semester_id)
    return TimetableListResponse(data=timetables)


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
    level: int = Query(...),
    current_user: User = Depends(require_permission("timetable.upload")),
    db: AsyncSession = Depends(get_db)
):
    """Preview master timetable upload"""
    service = MasterTimetableService(db)

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
        level=level,
        filename=file.filename
    )

    return result


@router.post("/publish", status_code=status.HTTP_200_OK)
async def publish_timetable(
    data: TimetablePublishRequest,
    current_user: User = Depends(require_permission("timetable.upload")),
    db: AsyncSession = Depends(get_db)
):
    """Publish master timetable"""
    service = MasterTimetableService(db)

    result = await service.publish_timetable(
        preview_id=data.preview_id,
        uploaded_by_id=current_user.id
    )

    return {"message": result}


@router.post("/department/preview", response_model=TimetablePreviewResponse)
async def preview_department_timetable(
    file: UploadFile = File(...),
    semester_id: uuid.UUID = Query(...),
    department_id: uuid.UUID = Query(...),
    current_user: User = Depends(require_permission("timetable.department_upload")),
    db: AsyncSession = Depends(get_db)
):
    """Preview department timetable upload"""
    service = MasterTimetableService(db)

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
    db: AsyncSession = Depends(get_db)
):
    """Publish department timetable"""
    service = MasterTimetableService(db)

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
