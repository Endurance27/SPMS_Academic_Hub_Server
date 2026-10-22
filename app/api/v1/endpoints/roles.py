import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.role import PermissionResponse, RoleCreate, RoleResponse, RoleUpdate
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["Roles & Permissions"])


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    current_user: User = Depends(require_permission("role.create")),
    db: AsyncSession = Depends(get_db),
):
    """Create new role (Admin only)"""
    role_service = RoleService(db)
    role = await role_service.create_role(data, current_user.id)
    return role


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(require_permission("role.view")),
    db: AsyncSession = Depends(get_db),
):
    """List all roles"""
    role_service = RoleService(db)
    roles = await role_service.role_repo.get_all()
    return roles


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: uuid.UUID,
    current_user: User = Depends(require_permission("role.view")),
    db: AsyncSession = Depends(get_db),
):
    """Get role details"""
    role_service = RoleService(db)
    role = await role_service.role_repo.get_with_permissions(role_id)

    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    return role


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: uuid.UUID,
    data: RoleUpdate,
    current_user: User = Depends(require_permission("role.update")),
    db: AsyncSession = Depends(get_db),
):
    """Update role"""
    role_service = RoleService(db)
    role = await role_service.update_role(role_id, data)
    return role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: uuid.UUID,
    current_user: User = Depends(require_permission("role.delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete role"""
    role_service = RoleService(db)
    await role_service.delete_role(role_id)
    return {"message": "Role deleted successfully"}


@router.get("/permissions/all", response_model=List[PermissionResponse])
async def list_permissions(
    current_user: User = Depends(require_permission("role.view")),
    db: AsyncSession = Depends(get_db),
):
    """List all available permissions"""
    role_service = RoleService(db)
    permissions = await role_service.get_all_permissions()
    return permissions
