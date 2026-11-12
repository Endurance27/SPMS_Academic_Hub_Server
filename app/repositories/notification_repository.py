import uuid
from typing import List, Optional

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notification import Notification
from app.models.supporting import NotificationRead
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db: AsyncSession):
        super().__init__(Notification, db)

    async def get_user_notifications(
        self, user_id: uuid.UUID, unread_only: bool = False, skip: int = 0, limit: int = 50
    ) -> tuple[list, int]:
        """Get notifications for a user - includes direct messages and broadcasts"""
        from app.models.user import User
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if not user:
            return [], 0

        conditions = []
        conditions.append(Notification.recipient_id == user_id)

        if user.role:
            conditions.append(
                and_(
                    Notification.audience_role == user.role.value,
                    Notification.audience_department_id.is_(None)
                )
            )

        if user.department_id:
            conditions.append(Notification.audience_department_id == user.department_id)

        if user.role and user.department_id:
            conditions.append(
                and_(
                    Notification.audience_role == user.role.value,
                    Notification.audience_department_id == user.department_id
                )
            )

        where_clause = or_(*conditions) if len(conditions) > 1 else conditions[0]

        base_query = select(Notification).where(where_clause)

        if unread_only:
            read_ids_subquery = select(NotificationRead.notification_id).where(
                NotificationRead.user_id == user_id
            )
            base_query = base_query.where(~Notification.id.in_(read_ids_subquery))

        count_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar()

        query = base_query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        query = query.options(selectinload(Notification.reads))

        result = await self.db.execute(query)
        notifications = list(result.scalars().all())

        for notification in notifications:
            read_record = None
            for read in notification.reads:
                if read.user_id == user_id:
                    read_record = read
                    break

            notification.is_read = read_record is not None
            notification.read_at = read_record.read_at if read_record else None

        return notifications, total

    async def mark_as_read(self, notification_ids: List[uuid.UUID], user_id: uuid.UUID) -> None:
        """Mark notifications as read for a specific user"""
        for notification_id in notification_ids:
            # Check if already read
            existing = await self.db.execute(
                select(NotificationRead).where(
                    and_(
                        NotificationRead.notification_id == notification_id,
                        NotificationRead.user_id == user_id
                    )
                )
            )
            if not existing.scalar_one_or_none():
                # Create read record
                read_record = NotificationRead(
                    notification_id=notification_id,
                    user_id=user_id
                )
                self.db.add(read_record)

        await self.db.commit()

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """Get count of unread notifications for a user"""
        from app.models.user import User
        from sqlalchemy import or_

        # Get user info
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if not user:
            return 0

        # Build conditions for visible notifications
        conditions = []
        conditions.append(Notification.recipient_id == user_id)

        if user.role:
            conditions.append(
                and_(
                    Notification.audience_role == user.role.value,
                    Notification.audience_department_id.is_(None)
                )
            )

        if user.department_id:
            conditions.append(Notification.audience_department_id == user.department_id)

        if user.role and user.department_id:
            conditions.append(
                and_(
                    Notification.audience_role == user.role.value,
                    Notification.audience_department_id == user.department_id
                )
            )

        # Subquery for read notifications
        read_ids_subquery = select(NotificationRead.notification_id).where(
            NotificationRead.user_id == user_id
        )

        # Count notifications that match conditions but are not in read_ids
        result = await self.db.execute(
            select(func.count(Notification.id))
            .where(
                and_(
                    or_(*conditions) if len(conditions) > 1 else conditions[0],
                    ~Notification.id.in_(read_ids_subquery)
                )
            )
        )
        return result.scalar()
