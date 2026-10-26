from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.profile import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    PasswordChangeRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    SessionListResponse,
    SessionResponse,
)
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/me", tags=["Profile"])


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user profile"""
    return current_user


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile"""
    service = ProfileService(db)
    return await service.update_profile(current_user.id, data)


@router.post("/photo")
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload profile photo (PNG, JPEG, or WebP, max 2MB)"""
    service = ProfileService(db)
    photo_url = await service.upload_photo(current_user.id, file)
    return {"data": {"photo_url": photo_url}}


@router.delete("/photo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete profile photo"""
    service = ProfileService(db)
    await service.delete_photo(current_user.id)


@router.post("/password")
async def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password"""
    service = ProfileService(db)
    await service.change_password(current_user.id, data)
    return {"message": "Password changed successfully."}


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List active sessions for the current user"""
    service = ProfileService(db)
    sessions = await service.get_sessions(current_user.id)
    return SessionListResponse(
        data=[SessionResponse.model_validate(s) for s in sessions]
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a specific session"""
    service = ProfileService(db)
    await service.revoke_session(current_user.id, session_id)


@router.post("/sessions/revoke-others")
async def revoke_other_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all sessions except the current one"""
    service = ProfileService(db)
    count = await service.revoke_other_sessions(current_user.id)
    return {"message": f"{count} session(s) revoked."}


@router.get("/notification-preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get notification preferences"""
    service = ProfileService(db)
    prefs = await service.get_notification_preferences(current_user.id)
    return prefs


@router.put("/notification-preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    data: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update notification preferences"""
    service = ProfileService(db)
    return await service.update_notification_preferences(current_user.id, data)
