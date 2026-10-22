import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone_number: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.phone_number == phone_number))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        await self.update(
            user_id,
            {
                "last_login": datetime.now(timezone.utc),
                "last_activity": datetime.now(timezone.utc),
                "failed_login_attempts": 0,
            },
        )

    async def increment_failed_attempts(self, user_id: uuid.UUID) -> None:
        user = await self.get_by_id(user_id)
        if user:
            await self.update(user_id, {"failed_login_attempts": user.failed_login_attempts + 1})

    async def lock_account(self, user_id: uuid.UUID, until: datetime) -> None:
        await self.update(user_id, {"locked_until": until})

    async def get_all(
        self, skip: int = 0, limit: int = 100, filters: Optional[dict] = None
    ) -> list[User]:
        query = select(User)

        if filters:
            if filters.get("role") is not None:
                role_value = getattr(filters["role"], "value", filters["role"])
                query = query.where(User.role == role_value)
            if filters.get("is_active") is not None:
                query = query.where(User.is_active == filters["is_active"])
            if filters.get("last_login") is not None:
                query = query.where(User.last_login >= filters["last_login"])
            if filters.get("phone_number") is not None:
                query = query.where(User.phone_number == filters["phone_number"])
            if filters.get("email") is not None:
                query = query.where(User.email == filters["email"])
            if filters.get("name") is not None:
                name = f"%{filters['name']}%"
                query = query.where(or_(User.first_name.ilike(name), User.last_name.ilike(name)))

        result = await self.db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def count(self, filters: Optional[dict] = None) -> int:
        query = select(func.count()).select_from(User)

        if filters:
            if filters.get("role") is not None:
                role_value = getattr(filters["role"], "value", filters["role"])
                query = query.where(User.role == role_value)
            if filters.get("is_active") is not None:
                query = query.where(User.is_active == filters["is_active"])
            if filters.get("last_login") is not None:
                query = query.where(User.last_login >= filters["last_login"])
            if filters.get("phone_number") is not None:
                query = query.where(User.phone_number == filters["phone_number"])
            if filters.get("email") is not None:
                query = query.where(User.email == filters["email"])
            if filters.get("name") is not None:
                name = f"%{filters['name']}%"
                query = query.where(or_(User.first_name.ilike(name), User.last_name.ilike(name)))

        result = await self.db.execute(query)
        return result.scalar_one()
