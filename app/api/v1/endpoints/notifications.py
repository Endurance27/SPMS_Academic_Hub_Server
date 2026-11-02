from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.notification import NotificationListResponse, NotificationMarkRead, NotificationResponse
from app.schemas.pagination import PaginationMeta
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user notifications"""
    notification_service = NotificationService(db)
    skip = (page - 1) * page_size
    notifications, total = await notification_service.get_user_notifications(
        current_user.id, unread_only, skip, page_size
    )
    return NotificationListResponse(
        data=notifications,
        meta=PaginationMeta.build(page, page_size, total),
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get unread notification count"""
    notification_service = NotificationService(db)
    count = await notification_service.get_unread_count(current_user.id)
    return {"unread_count": count}


@router.post("/mark-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notifications_read(
    data: NotificationMarkRead,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark notifications as read"""
    notification_service = NotificationService(db)
    await notification_service.mark_as_read(data.notification_ids, current_user.id)


@router.post("/mark-all-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read"""
    notification_service = NotificationService(db)

    # Get all user's unread notifications
    notifications = await notification_service.get_user_notifications(
        current_user.id, unread_only=True
    )

    if notifications:
        notification_ids = [n.id for n in notifications]
        await notification_service.mark_as_read(notification_ids, current_user.id)
