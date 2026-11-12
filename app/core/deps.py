import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_redis
from app.core.database import get_db
from app.core.security import SecurityService
from app.models.user import User, UserRole, UserStatus
from app.repositories.user_repository import UserRepository

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials

    # Check if token is blacklisted
    is_blacklisted = await redis.get(f"blacklist:{token}")
    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked"
        )

    # Decode token
    payload = SecurityService.decode_token(token)
    user_id_str: str = payload.get("sub")

    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
        )

    # Get user from database
    user_repo = UserRepository(db)
    try:
        user_id = uuid.UUID(user_id_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        )

    user = await user_repo.get_by_id(user_id)

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    # Check session in Redis
    session_key = f"session:{user_id}:{token}"
    session_data = await redis.get(session_key)

    if not session_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    return user


async def get_current_active_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require super admin role"""
    if current_user.role != UserRole.SUPER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    return current_user


async def get_current_department_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require department admin role"""
    if current_user.role != UserRole.DEPARTMENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    return current_user


async def get_current_lecturer(current_user: User = Depends(get_current_user)) -> User:
    """Require lecturer role"""
    if current_user.role != UserRole.LECTURER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    return current_user


async def get_current_student(current_user: User = Depends(get_current_user)) -> User:
    """Require student role"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    return current_user


async def require_department_access(
    current_user: User = Depends(get_current_user),
    department_id: Optional[uuid.UUID] = None
) -> None:
    """Ensure user can access the specified department - raises 403 if not"""
    if current_user.role == UserRole.SUPER:
        return
    if current_user.role == UserRole.DEPARTMENT:
        if department_id and current_user.department_id != department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this department"
            )
        return
    if current_user.role == UserRole.LECTURER:
        if department_id and current_user.department_id != department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this department"
            )
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied"
    )
