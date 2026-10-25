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

    async def get_by_phone(self, phone: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        await self.update(
            user_id,
            {
                "last_login_at": datetime.now(timezone.utc),
                "last_activity_at": datetime.now(timezone.utc),
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
        from app.models.user import UserStatus

        query = select(User)

        if filters:
            if filters.get("role") is not None:
                role_value = getattr(filters["role"], "value", filters["role"])
                query = query.where(User.role == role_value)
            if filters.get("status") is not None:
                query = query.where(User.status == filters["status"])
            if filters.get("is_active") is not None:
                # Map is_active to status
                status = UserStatus.ACTIVE if filters["is_active"] else UserStatus.DISABLED
                query = query.where(User.status == status)
            if filters.get("last_login_at") is not None:
                query = query.where(User.last_login_at >= filters["last_login_at"])
            if filters.get("phone") is not None:
                query = query.where(User.phone == filters["phone"])
            if filters.get("email") is not None:
                query = query.where(User.email == filters["email"])
            if filters.get("name") is not None:
                name = f"%{filters['name']}%"
                query = query.where(User.name.ilike(name))

        result = await self.db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def count(self, filters: Optional[dict] = None) -> int:
        from app.models.user import UserStatus

        query = select(func.count()).select_from(User)

        if filters:
            if filters.get("role") is not None:
                role_value = getattr(filters["role"], "value", filters["role"])
                query = query.where(User.role == role_value)
            if filters.get("status") is not None:
                query = query.where(User.status == filters["status"])
            if filters.get("is_active") is not None:
                status = UserStatus.ACTIVE if filters["is_active"] else UserStatus.DISABLED
                query = query.where(User.status == status)
            if filters.get("last_login_at") is not None:
                query = query.where(User.last_login_at >= filters["last_login_at"])
            if filters.get("phone") is not None:
                query = query.where(User.phone == filters["phone"])
            if filters.get("email") is not None:
                query = query.where(User.email == filters["email"])
            if filters.get("name") is not None:
                name = f"%{filters['name']}%"
                query = query.where(User.name.ilike(name))

        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_by_student_number(self, student_number: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.student_number == student_number))
        return result.scalar_one_or_none()

    async def get_by_staff_id(self, staff_id: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.staff_id == staff_id))
        return result.scalar_one_or_none()

    async def get_by_department(self, department_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[User]:
        result = await self.db.execute(
            select(User)
            .where(User.department_id == department_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_programme(self, programme_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[User]:
        result = await self.db.execute(
            select(User)
            .where(User.programme_id == programme_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_department(self, department_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(User).where(User.department_id == department_id)
        )
        return result.scalar_one()

    async def count_by_programme(self, programme_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(User).where(User.programme_id == programme_id)
        )
        return result.scalar_one()

    async def get_by_role(
        self, role: "UserRole", skip: int = 0, limit: int = 100
    ) -> list[User]:
        result = await self.db.execute(
            select(User).where(User.role == role).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_role(self, role: "UserRole") -> int:
        result = await self.db.execute(
            select(func.count()).select_from(User).where(User.role == role)
        )
        return result.scalar_one()
