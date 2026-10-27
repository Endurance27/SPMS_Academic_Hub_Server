from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.venue import (
    VenueCreate,
    VenueUpdate,
    VenueResponse,
    VenueListResponse
)
from app.services.venue_service import VenueService

router = APIRouter()


@router.get("", response_model=VenueListResponse)
async def list_venues(
    venue_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("venues.view")),
    db: AsyncSession = Depends(get_db)
):
    service = VenueService(db)
    skip = (page - 1) * page_size
    venues = await service.list_venues(venue_type, status, search, skip, page_size)

    return VenueListResponse(
        data=venues,
        meta={"page": page, "page_size": page_size}
    )


@router.post("", response_model=VenueResponse, status_code=201)
async def create_venue(
    data: VenueCreate,
    current_user: User = Depends(require_permission("venues.manage")),
    db: AsyncSession = Depends(get_db)
):
    service = VenueService(db)
    try:
        return await service.create_venue(data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{venue_id}", response_model=VenueResponse)
async def get_venue(
    venue_id: UUID,
    current_user: User = Depends(require_permission("venues.view")),
    db: AsyncSession = Depends(get_db)
):
    service = VenueService(db)
    venue = await service.get_venue(venue_id)

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    return venue


@router.patch("/{venue_id}", response_model=VenueResponse)
async def update_venue(
    venue_id: UUID,
    data: VenueUpdate,
    current_user: User = Depends(require_permission("venues.manage")),
    db: AsyncSession = Depends(get_db)
):
    service = VenueService(db)
    venue = await service.update_venue(venue_id, data)

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    return venue


@router.delete("/{venue_id}", status_code=204)
async def delete_venue(
    venue_id: UUID,
    current_user: User = Depends(require_permission("venues.manage")),
    db: AsyncSession = Depends(get_db)
):
    service = VenueService(db)
    success = await service.delete_venue(venue_id)

    if not success:
        raise HTTPException(status_code=404, detail="Venue not found")


@router.post("/{venue_id}/unavailable", response_model=VenueResponse)
async def set_unavailable(
    venue_id: UUID,
    reason: str,
    until: Optional[datetime] = None,
    current_user: User = Depends(require_permission("venues.manage")),
    db: AsyncSession = Depends(get_db)
):
    service = VenueService(db)
    venue = await service.set_unavailable(venue_id, reason, until)

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    return venue


@router.post("/{venue_id}/available", response_model=VenueResponse)
async def set_available(
    venue_id: UUID,
    current_user: User = Depends(require_permission("venues.manage")),
    db: AsyncSession = Depends(get_db)
):
    service = VenueService(db)
    venue = await service.set_available(venue_id)

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    return venue
