from typing import List

from fastapi import Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.role import Role
from app.models.user import User, UserRole


class PermissionChecker:
    """Check user permissions"""

    @staticmethod
    async def has_permission(user: User, permission_code: str) -> bool:
        """Check if user has specific permission"""
        # Super admin has all permissions
        if user.role == UserRole.ADMINISTRATOR and not user.roles:
            return True

        # Check user's roles
        for role in user.roles:
            if not role.is_active:
                continue

            for permission in role.permissions:
                if permission.code == permission_code and permission.is_active:
                    return True

        return False

    @staticmethod
    async def require_permission(user: User, permission_code: str) -> None:
        """Require user to have permission or raise exception"""
        has_perm = await PermissionChecker.has_permission(user, permission_code)

        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission_code}",
            )

    @staticmethod
    async def has_any_permission(user: User, permission_codes: List[str]) -> bool:
        """Check if user has any of the specified permissions"""
        for code in permission_codes:
            if await PermissionChecker.has_permission(user, code):
                return True
        return False


def require_permission(permission_code: str):
    """Dependency factory that ensures a user has a specific permission"""

    async def permission_dependency(
        current_user: User = Depends(get_current_user), db=Depends(get_db)
    ):
        # ✅ Fetch user with roles + permissions eagerly loaded
        result = await db.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == current_user.id)
        )
        user = result.scalars().first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # ✅ Administrator bypass
        if user.role == UserRole.ADMINISTRATOR:
            return user

        # ✅ Check if user has the given permission
        has_perm = False
        for role in user.roles:
            for perm in role.permissions:
                if perm.code == permission_code:
                    has_perm = True
                    break

        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission_code}",
            )

        return user  # pass user to route

    return permission_dependency
