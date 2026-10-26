import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import SecurityService
from app.models.notification_preferences import NotificationPreferences
from app.models.session import Session
from app.models.user import User
from app.schemas.profile import (
    NotificationPreferencesUpdate,
    PasswordChangeRequest,
    ProfileUpdateRequest,
)


class ProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_profile(self, user_id: uuid.UUID, data: ProfileUpdateRequest) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def change_password(self, user_id: uuid.UUID, data: PasswordChangeRequest) -> None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if not SecurityService.verify_password(data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"fields": {"current_password": "Current password is incorrect."}},
            )

        if data.new_password != data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"fields": {"confirm_password": "Passwords do not match."}},
            )

        user.hashed_password = SecurityService.get_password_hash(data.new_password)
        await self.db.commit()

    async def upload_photo(self, user_id: uuid.UUID, file: UploadFile) -> str:
        allowed_types = {"image/png", "image/jpeg", "image/webp"}
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be PNG, JPEG, or WebP.",
            )

        contents = await file.read()
        if len(contents) > 2 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be 2MB or smaller.",
            )

        upload_dir = os.path.join(settings.UPLOAD_DIR, "photos")
        os.makedirs(upload_dir, exist_ok=True)

        ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
        filename = f"{user_id}.{ext}"
        filepath = os.path.join(upload_dir, filename)

        with open(filepath, "wb") as f:
            f.write(contents)

        photo_url = f"/uploads/photos/{filename}"

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.photo_url = photo_url
            await self.db.commit()

        return photo_url

    async def delete_photo(self, user_id: uuid.UUID) -> None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.photo_url:
            filepath = os.path.join(".", user.photo_url.lstrip("/"))
            if os.path.exists(filepath):
                os.remove(filepath)
            user.photo_url = None
            await self.db.commit()

    async def get_sessions(self, user_id: uuid.UUID) -> List[Session]:
        result = await self.db.execute(
            select(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .order_by(Session.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_session(self, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(Session).where(Session.id == session_id, Session.user_id == user_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        session.revoked_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def revoke_other_sessions(
        self, user_id: uuid.UUID, current_session_id: Optional[uuid.UUID] = None
    ) -> int:
        stmt = (
            update(Session)
            .where(
                Session.user_id == user_id,
                Session.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        if current_session_id:
            stmt = stmt.where(Session.id != current_session_id)

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def get_notification_preferences(self, user_id: uuid.UUID) -> NotificationPreferences:
        result = await self.db.execute(
            select(NotificationPreferences).where(NotificationPreferences.user_id == user_id)
        )
        prefs = result.scalar_one_or_none()
        if not prefs:
            prefs = NotificationPreferences(user_id=user_id)
            self.db.add(prefs)
            await self.db.commit()
            await self.db.refresh(prefs)
        return prefs

    async def update_notification_preferences(
        self, user_id: uuid.UUID, data: NotificationPreferencesUpdate
    ) -> NotificationPreferences:
        prefs = await self.get_notification_preferences(user_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(prefs, field, value)
        await self.db.commit()
        await self.db.refresh(prefs)
        return prefs
