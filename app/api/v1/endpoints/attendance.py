import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.attendance import (
    AttendanceSessionCreate,
    AttendanceRecordCreate,
    AttendanceSessionResponse,
    AttendanceRecordResponse,
    AttendanceSessionListResponse
)
from app.services.attendance_service import AttendanceService

router = APIRouter()


@router.get("/sessions", response_model=AttendanceSessionListResponse)
async def list_sessions(
    status: Optional[str] = Query(None),
    course_id: Optional[uuid.UUID] = Query(None),
    department_id: Optional[uuid.UUID] = Query(None),
    date: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("attendance.view")),
    db: AsyncSession = Depends(get_db)
):
    """List attendance sessions"""
    service = AttendanceService(db)
    sessions, meta = await service.list_sessions(
        status=status,
        course_id=course_id,
        department_id=department_id,
        date=date,
        user=current_user
    )
    return AttendanceSessionListResponse(data=sessions, meta=meta)


@router.post("/sessions", response_model=AttendanceSessionResponse, status_code=201)
async def create_session(
    data: AttendanceSessionCreate,
    current_user: User = Depends(require_permission("attendance.record")),
    db: AsyncSession = Depends(get_db)
):
    """Create attendance session"""
    service = AttendanceService(db)
    return await service.create_session(data, current_user)


@router.post("/sessions/{session_id}/open", response_model=AttendanceSessionResponse)
async def open_session(
    session_id: uuid.UUID,
    current_user: User = Depends(require_permission("attendance.record")),
    db: AsyncSession = Depends(get_db)
):
    """Open attendance session for QR check-in"""
    service = AttendanceService(db)
    return await service.open_session(session_id, current_user)


@router.get("/sessions/{session_id}/qr")
async def get_qr_token(
    session_id: uuid.UUID,
    current_user: User = Depends(require_permission("attendance.record")),
    db: AsyncSession = Depends(get_db)
):
    """Get QR token for check-in"""
    service = AttendanceService(db)
    return await service.get_qr_token(session_id, current_user)


@router.post("/check-in")
async def check_in(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Student QR check-in"""
    service = AttendanceService(db)
    return await service.check_in(token, current_user)


@router.post("/sessions/{session_id}/close", response_model=AttendanceSessionResponse)
async def close_session(
    session_id: uuid.UUID,
    current_user: User = Depends(require_permission("attendance.record")),
    db: AsyncSession = Depends(get_db)
):
    """Close attendance session"""
    service = AttendanceService(db)
    return await service.close_session(session_id, current_user)


@router.post("/records", response_model=AttendanceRecordResponse, status_code=201)
async def create_record(
    data: AttendanceRecordCreate,
    current_user: User = Depends(require_permission("attendance.record")),
    db: AsyncSession = Depends(get_db)
):
    """Manual attendance record"""
    service = AttendanceService(db)
    return await service.create_record(data, current_user)


@router.post("/records/bulk")
async def bulk_create_records(
    session_id: uuid.UUID,
    records: list,
    current_user: User = Depends(require_permission("attendance.record")),
    db: AsyncSession = Depends(get_db)
):
    """Bulk attendance records"""
    service = AttendanceService(db)
    return await service.bulk_create_records(session_id, records, current_user)


@router.get("/records")
async def list_records(
    course_id: Optional[uuid.UUID] = Query(None),
    student_id: Optional[uuid.UUID] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("attendance.view")),
    db: AsyncSession = Depends(get_db)
):
    """List attendance records"""
    service = AttendanceService(db)
    return await service.list_records(course_id, student_id, from_date, to_date, current_user)


@router.patch("/records/{record_id}")
async def update_record(
    record_id: uuid.UUID,
    record_status: Optional[str] = None,
    note: Optional[str] = None,
    current_user: User = Depends(require_permission("attendance.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Update an attendance record"""
    from sqlalchemy.future import select
    from app.models.attendance import AttendanceRecord

    result = await db.execute(select(AttendanceRecord).where(AttendanceRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    if record_status is not None:
        record.status = record_status
    if note is not None:
        record.note = note

    await db.commit()
    await db.refresh(record)
    return {"data": {"id": str(record.id), "status": record.status, "note": record.note}}


@router.get("/export")
async def export_attendance(
    scope: Optional[str] = Query("department"),
    department_id: Optional[uuid.UUID] = Query(None),
    course_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(require_permission("attendance.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Export attendance records as CSV"""
    import io
    import csv
    from fastapi.responses import StreamingResponse
    from sqlalchemy.future import select
    from sqlalchemy.orm import selectinload
    from app.models.attendance import AttendanceRecord, AttendanceSession

    query = (
        select(AttendanceRecord)
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
        .options(
            selectinload(AttendanceRecord.student),
            selectinload(AttendanceRecord.session).selectinload(AttendanceSession.course),
        )
    )
    if scope == "department" and current_user.department_id:
        dept_id = department_id or current_user.department_id
        query = query.where(AttendanceSession.department_id == dept_id)
    if course_id:
        query = query.where(AttendanceRecord.course_id == course_id)

    query = query.order_by(AttendanceRecord.recorded_at.desc())
    result = await db.execute(query)
    records = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Course", "Student", "Date", "Status", "Source"])
    for r in records:
        course_code = r.session.course.code if r.session and r.session.course else r.course_id or ""
        student_name = r.student.name if r.student else ""
        date_str = r.recorded_at.strftime("%Y-%m-%d") if r.recorded_at else ""
        writer.writerow([course_code, student_name, date_str, r.status or "", r.source or ""])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance-register.csv"}
    )
