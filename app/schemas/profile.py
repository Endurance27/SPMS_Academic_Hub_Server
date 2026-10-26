import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    office: Optional[str] = Field(None, max_length=100)


class ProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: str
    phone: Optional[str] = None
    office: Optional[str] = None
    photo_url: Optional[str] = None
    title: Optional[str] = None

    class Config:
        from_attributes = True


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str


class NotificationPreferencesResponse(BaseModel):
    schedule_notifications: bool = True
    assessment_notifications: bool = True
    attendance_notifications: bool = True
    graduation_notifications: bool = True
    email_notifications: bool = True
    in_app_notifications: bool = True

    class Config:
        from_attributes = True


class NotificationPreferencesUpdate(BaseModel):
    schedule_notifications: Optional[bool] = None
    assessment_notifications: Optional[bool] = None
    attendance_notifications: Optional[bool] = None
    graduation_notifications: Optional[bool] = None
    email_notifications: Optional[bool] = None
    in_app_notifications: Optional[bool] = None


class SessionResponse(BaseModel):
    id: uuid.UUID
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    is_current: bool = False

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    data: List[SessionResponse]
