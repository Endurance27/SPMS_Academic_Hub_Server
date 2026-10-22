import uuid
from typing import List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db: AsyncSession):
        super().__init__(Notification, db)

    async def get_user_notifications(
        self, user_id: uuid.UUID, unread_only: bool = False, limit: int = 50
    ) -> List[Notification]:
        """Get notifications for a user"""
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            query = query.where(Notification.is_read == False)

        query = query.order_by(Notification.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_as_read(self, notification_ids: List[uuid.UUID]) -> None:
        """Mark notifications as read"""
        from datetime import datetime

        await self.db.execute(
            update(Notification)
            .where(Notification.id.in_(notification_ids))
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await self.db.commit()

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """Get count of unread notifications"""
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count(Notification.id))
            .where(Notification.user_id == user_id)
            .where(Notification.is_read == False)
        )
        return result.scalar()
