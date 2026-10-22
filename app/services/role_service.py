import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Permission, Role, role_permissions
from app.repositories.role_repository import PermissionRepository, RoleRepository
from app.schemas.role import RoleUpdate


class RoleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.role_repo = RoleRepository(db)
        self.permission_repo = PermissionRepository(db)

    async def create_role(self, data, created_by_id: uuid.UUID) -> Role:
        """Create new role with permissions (async-safe)"""
        # ✅ Check if role code already exists
        existing = await self.role_repo.get_by_code(data.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Role code already exists"
            )

        # ✅ Create role
        role_data = {
            "name": data.name,
            "code": data.code,
            "description": data.description,
            "is_admin_role": data.is_admin_role,
            "created_by_id": created_by_id,
            "is_system_role": False,
        }

        role = Role(**role_data)
        self.db.add(role)
        await self.db.flush()  # Generates role.id

        # ✅ Safely insert into role_permissions manually
        if data.permission_ids:
            stmt = insert(role_permissions).values(
                [{"role_id": role.id, "permission_id": pid} for pid in data.permission_ids]
            )
            await self.db.execute(stmt)

        # ✅ Commit and reload role with permissions
        await self.db.commit()

        result = await self.db.execute(
            select(Role).options(selectinload(Role.permissions)).where(Role.id == role.id)
        )
        created_role = result.scalars().first()

        return created_role

    async def update_role(self, role_id: uuid.UUID, data: RoleUpdate) -> Role:
        """Update role and permissions"""
        role = await self.role_repo.get_with_permissions(role_id)

        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        if role.is_system_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify system role"
            )

        # Update basic fields
        update_data = data.dict(exclude_unset=True, exclude={"permission_ids"})
        if update_data:
            await self.role_repo.update(role_id, update_data)

        # Update permissions if provided
        if data.permission_ids is not None:
            permissions = await self.permission_repo.get_by_ids(data.permission_ids)
            role.permissions = permissions
            await self.db.commit()

        await self.db.refresh(role)
        return role

    async def delete_role(self, role_id: uuid.UUID) -> bool:
        """Delete role"""
        role = await self.role_repo.get_by_id(role_id)

        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        if role.is_system_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete system role"
            )

        return await self.role_repo.delete(role_id)

    async def get_all_permissions(self) -> List[Permission]:
        """Get all permissions"""
        return await self.permission_repo.get_all()
