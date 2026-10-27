from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.semester import (
    SemesterCreate,
    SemesterUpdate,
    SemesterResponse,
    SemesterListResponse
)
from app.services.semester_service import SemesterService

router = APIRouter()


@router.get("", response_model=SemesterListResponse)
async def list_semesters(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = SemesterService(db)
    semesters = await service.list_semesters()
    return SemesterListResponse(data=semesters)


@router.post("", response_model=SemesterResponse, status_code=201)
async def create_semester(
    data: SemesterCreate,
    current_user: User = Depends(require_permission("settings.institution")),
    db: AsyncSession = Depends(get_db)
):
    service = SemesterService(db)
    return await service.create_semester(data)


@router.get("/{semester_id}", response_model=SemesterResponse)
async def get_semester(
    semester_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = SemesterService(db)
    semester = await service.get_semester(semester_id)
    if not semester:
        raise HTTPException(status_code=404, detail="Semester not found")
    return semester


@router.patch("/{semester_id}", response_model=SemesterResponse)
async def update_semester(
    semester_id: UUID,
    data: SemesterUpdate,
    current_user: User = Depends(require_permission("settings.institution")),
    db: AsyncSession = Depends(get_db)
):
    service = SemesterService(db)
    semester = await service.update_semester(semester_id, data)
    if not semester:
        raise HTTPException(status_code=404, detail="Semester not found")
    return semester


@router.post("/{semester_id}/activate", response_model=SemesterResponse)
async def activate_semester(
    semester_id: UUID,
    current_user: User = Depends(require_permission("settings.institution")),
    db: AsyncSession = Depends(get_db)
):
    service = SemesterService(db)
    semester = await service.activate_semester(semester_id)
    if not semester:
        raise HTTPException(status_code=404, detail="Semester not found")
    return semester
