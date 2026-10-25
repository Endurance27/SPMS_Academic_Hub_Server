import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.slot_request import (
    SlotRequestCreate,
    SlotRequestCheckResponse,
    SlotRequestResponse,
    SlotRequestListResponse
)
from app.services.slot_request_service import SlotRequestService

router = APIRouter()


@router.get("/free-slots")
async def get_free_slots(
    semester_id: uuid.UUID = Query(...),
    level: Optional[int] = Query(None),
    venue: Optional[str] = Query(None),
    view: str = Query("free"),
    current_user: User = Depends(require_permission("schedule.view")),
    db: AsyncSession = Depends(get_db)
):
    """Get FREE slots for scheduling"""
    service = SlotRequestService(db)
    slots = await service.get_free_slots(
        semester_id=semester_id,
        level=level,
        venue_code=venue,
        view=view,
        user=current_user
    )
    return slots


@router.post("/check", response_model=SlotRequestCheckResponse)
async def check_slot_request(
    data: SlotRequestCreate,
    current_user: User = Depends(require_permission("schedule.request")),
    db: AsyncSession = Depends(get_db)
):
    """Check for clashes before submitting slot request"""
    service = SlotRequestService(db)
    clashes = await service.check_clashes(data, current_user)
    return {"clashes": clashes, "blocking": any(c.severity == "danger" for c in clashes)}


@router.post("", response_model=SlotRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_slot_request(
    data: SlotRequestCreate,
    current_user: User = Depends(require_permission("schedule.request")),
    db: AsyncSession = Depends(get_db)
):
    """Submit slot request"""
    service = SlotRequestService(db)

    # Check clashes first
    clashes = await service.check_clashes(data, current_user)
    if any(c.severity == "danger" for c in clashes):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CLASH_BLOCKED", "clashes": clashes}
        )

    request = await service.create_request(data, current_user)
    return request


@router.get("", response_model=SlotRequestListResponse)
async def list_slot_requests(
    status: Optional[str] = Query(None),
    semester_id: uuid.UUID = Query(...),
    department_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(require_permission("schedule.view")),
    db: AsyncSession = Depends(get_db)
):
    """List slot requests"""
    service = SlotRequestService(db)
    requests, meta = await service.list_requests(
        status=status,
        semester_id=semester_id,
        department_id=department_id,
        user=current_user
    )
    return SlotRequestListResponse(data=requests, meta=meta)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_slot_request(
    request_id: uuid.UUID,
    current_user: User = Depends(require_permission("schedule.withdraw")),
    db: AsyncSession = Depends(get_db)
):
    """Withdraw pending slot request"""
    service = SlotRequestService(db)
    await service.withdraw_request(request_id, current_user)


@router.post("/{request_id}/approve", response_model=SlotRequestResponse)
async def approve_slot_request(
    request_id: uuid.UUID,
    comment: Optional[str] = None,
    current_user: User = Depends(require_permission("schedule.approve")),
    db: AsyncSession = Depends(get_db)
):
    """Approve slot request"""
    service = SlotRequestService(db)
    result = await service.approve_request(request_id, comment, current_user)
    return result


@router.post("/{request_id}/return", response_model=SlotRequestResponse)
async def return_slot_request(
    request_id: uuid.UUID,
    comment: str,
    current_user: User = Depends(require_permission("schedule.approve")),
    db: AsyncSession = Depends(get_db)
):
    """Return slot request"""
    service = SlotRequestService(db)
    result = await service.return_request(request_id, comment, current_user)
    return result


@router.post("/{request_id}/override", response_model=SlotRequestResponse)
async def override_slot_request(
    request_id: uuid.UUID,
    reason: str,
    current_user: User = Depends(require_permission("conflicts.override")),
    db: AsyncSession = Depends(get_db)
):
    """Override slot request despite clashes"""
    service = SlotRequestService(db)
    result = await service.override_request(request_id, reason, current_user)
    return result
