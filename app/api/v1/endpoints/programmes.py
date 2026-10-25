from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.models.user import User, UserRole
from app.schemas.programme import (
    ProgrammeCreate,
    ProgrammeUpdate,
    ProgrammeResponse,
    ProgrammeListResponse
)
from app.services.programme_service import ProgrammeService

router = APIRouter()


@router.get("", response_model=ProgrammeListResponse)
async def list_programmes(
    department_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("programmes.view")),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role == UserRole.DEPARTMENT:
        department_id = current_user.department_id

    service = ProgrammeService(db)
    skip = (page - 1) * page_size
    programmes = await service.list_programmes(department_id, skip, page_size)

    return ProgrammeListResponse(
        data=programmes,
        meta={"page": page, "page_size": page_size}
    )


@router.post("", response_model=ProgrammeResponse, status_code=201)
async def create_programme(
    data: ProgrammeCreate,
    current_user: User = Depends(require_permission("programmes.manage")),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role == UserRole.DEPARTMENT:
        if data.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Can only create programmes for own department")

    service = ProgrammeService(db)
    try:
        return await service.create_programme(data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{programme_id}", response_model=ProgrammeResponse)
async def get_programme(
    programme_id: UUID,
    current_user: User = Depends(require_permission("programmes.view")),
    db: AsyncSession = Depends(get_db)
):
    service = ProgrammeService(db)
    programme = await service.get_programme(programme_id)

    if not programme:
        raise HTTPException(status_code=404, detail="Programme not found")

    if current_user.role == UserRole.DEPARTMENT:
        if programme.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Access denied")

    return programme


@router.patch("/{programme_id}", response_model=ProgrammeResponse)
async def update_programme(
    programme_id: UUID,
    data: ProgrammeUpdate,
    current_user: User = Depends(require_permission("programmes.manage")),
    db: AsyncSession = Depends(get_db)
):
    service = ProgrammeService(db)
    programme = await service.get_programme(programme_id)

    if not programme:
        raise HTTPException(status_code=404, detail="Programme not found")

    if current_user.role == UserRole.DEPARTMENT:
        if programme.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Access denied")

    try:
        return await service.update_programme(programme_id, data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/{programme_id}", status_code=204)
async def delete_programme(
    programme_id: UUID,
    force: bool = Query(False),
    current_user: User = Depends(require_permission("programmes.manage")),
    db: AsyncSession = Depends(get_db)
):
    service = ProgrammeService(db)
    programme = await service.get_programme(programme_id)

    if not programme:
        raise HTTPException(status_code=404, detail="Programme not found")

    if current_user.role == UserRole.DEPARTMENT:
        if programme.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Access denied")

    try:
        await service.delete_programme(programme_id, force)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
