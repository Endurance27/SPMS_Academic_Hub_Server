import uuid
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository

from app.schemas.notification import NotificationCreate


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.notification_repo = NotificationRepository(db)

    async def create_notification(self, data: NotificationCreate) -> Notification:
        """Create notification"""
        notification_data = data.dict()
        notification = await self.notification_repo.create(notification_data)

        # TODO: Send real-time notification via WebSocket
        # TODO: Send email if priority is HIGH
        # TODO: Send SMS for urgent notifications

        return notification

    async def get_user_notifications(
        self, user_id: uuid.UUID, unread_only: bool = False
    ) -> List[Notification]:
        """Get user notifications"""
        return await self.notification_repo.get_user_notifications(user_id, unread_only)

    async def mark_as_read(self, notification_ids: List[uuid.UUID]) -> None:
        """Mark notifications as read"""
        await self.notification_repo.mark_as_read(notification_ids)

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """Get unread notification count"""
        return await self.notification_repo.get_unread_count(user_id)
