import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Permission, Role
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self, db: AsyncSession):
        super().__init__(Role, db)

    async def get_by_id(self, id: uuid.UUID) -> Optional[Role]:
        """Get a record by ID"""
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str):
        query = select(Role).options(selectinload(Role.permissions)).where(Role.code == code)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_with_permissions(self, role_id: uuid.UUID) -> Optional[Role]:
        """Get role with permissions loaded"""
        result = await self.db.execute(
            select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()

    async def get_admin_roles(self) -> List[Role]:
        """Get all admin roles"""
        result = await self.db.execute(
            select(Role).where(Role.is_admin_role == True).where(Role.is_active == True)
        )
        return list(result.scalars().all())


class PermissionRepository(BaseRepository[Permission]):
    def __init__(self, db: AsyncSession):
        super().__init__(Permission, db)

    async def get_by_code(self, code: str) -> Optional[Permission]:
        """Get permission by code"""
        result = await self.db.execute(select(Permission).where(Permission.code == code))
        return result.scalar_one_or_none()

    async def get_by_module(self, module: str) -> List[Permission]:
        """Get permissions by module"""
        result = await self.db.execute(
            select(Permission)
            .where(Permission.module == module)
            .where(Permission.is_active == True)
        )
        return list(result.scalars().all())

    async def get_by_ids(
        self, permission_ids: List[uuid.UUID], options: Optional[List] = None
    ) -> List[Permission]:
        """Get permissions by IDs"""
        query = select(self.model).where(self.model.id.in_(permission_ids))
        if options:
            for opt in options:
                query = query.options(opt)
        result = await self.db.execute(query)
        return result.scalars().all()
