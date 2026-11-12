from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User, UserRole
from app.schemas.settings import (
    DepartmentSettingsResponse,
    DepartmentSettingsUpdate,
    InstitutionSettingsResponse,
    InstitutionSettingsUpdate,
)
from app.services.settings_service import SettingsService

router = APIRouter()


@router.get("/institution", response_model=InstitutionSettingsResponse)
async def get_institution_settings(
    current_user: User = Depends(require_permission("settings.institution")),
    db: AsyncSession = Depends(get_db),
):
    service = SettingsService(db)
    settings = await service.get_institution_settings()
    return settings


@router.put("/institution", response_model=InstitutionSettingsResponse)
async def update_institution_settings(
    data: InstitutionSettingsUpdate,
    current_user: User = Depends(require_permission("settings.institution")),
    db: AsyncSession = Depends(get_db),
):
    service = SettingsService(db)
    settings = await service.update_institution_settings(data)
    return settings


@router.get("/department", response_model=DepartmentSettingsResponse)
async def get_department_settings(
    department_id: Optional[UUID] = Query(None),
    current_user: User = Depends(require_permission("settings.department")),
    db: AsyncSession = Depends(get_db),
):
    resolved_id = department_id
    if current_user.role != UserRole.SUPER:
        resolved_id = current_user.department_id

    if not resolved_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department ID is required",
        )

    service = SettingsService(db)
    settings = await service.get_department_settings(resolved_id)
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department settings not found",
        )
    return settings


@router.put("/department", response_model=DepartmentSettingsResponse)
async def update_department_settings(
    data: DepartmentSettingsUpdate,
    department_id: Optional[UUID] = Query(None),
    current_user: User = Depends(require_permission("settings.department")),
    db: AsyncSession = Depends(get_db),
):
    resolved_id = department_id
    if current_user.role != UserRole.SUPER:
        resolved_id = current_user.department_id

    if not resolved_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department ID is required",
        )

    service = SettingsService(db)
    settings = await service.update_department_settings(resolved_id, data)
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department settings not found",
        )
    return settings
