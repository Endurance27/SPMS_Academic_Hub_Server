from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.user import UserProfileUpdate, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: User = Depends(require_permission("user.view")),
    db: AsyncSession = Depends(get_db),
):
    user_service = UserService(db)
    user = await user_service.get_current_user_info(current_user)
    return user


@router.patch("/update", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_user_info(
    data: UserProfileUpdate,
    current_user: User = Depends(require_permission("user.update")),
    db: AsyncSession = Depends(get_db),
):
    user_service = UserService(db)
    user = await user_service.update_user_info(current_user, data)

    return user
