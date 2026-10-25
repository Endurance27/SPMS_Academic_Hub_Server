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
