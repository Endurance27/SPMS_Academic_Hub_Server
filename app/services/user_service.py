from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserProfileUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def get_current_user_info(self, current_user: User):
        user = await self.user_repo.get_by_id(current_user.id)
        return user

    async def update_user_info(self, current_user: User, user_data: UserProfileUpdate) -> User:
        update_data = user_data.dict(exclude_unset=True)

        updated = await self.user_repo.update(current_user.id, update_data)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return updated

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        return await self.user_repo.get_all_users(skip, limit)

    async def get_user_by_id(self, user_id: int) -> User:
        return await self.user_repo.get_by_id(user_id)
