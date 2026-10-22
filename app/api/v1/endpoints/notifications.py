from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.notification import NotificationMarkRead, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user notifications"""
    notification_service = NotificationService(db)
    notifications = await notification_service.get_user_notifications(current_user.id, unread_only)
    return notifications


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
    await notification_service.mark_as_read(data.notification_ids)


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
        await notification_service.mark_as_read(notification_ids)
