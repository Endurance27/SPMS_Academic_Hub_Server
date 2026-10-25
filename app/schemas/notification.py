import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.models.notification import NotificationCategory, NotificationPriority


class NotificationCreate(BaseModel):
    recipient_id: Optional[uuid.UUID] = None
    title: str
    detail: str
    page: Optional[str] = None
    category: NotificationCategory
    priority: NotificationPriority = NotificationPriority.MEDIUM
    audience_role: Optional[str] = None
    audience_department_id: Optional[uuid.UUID] = None
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None


class NotificationResponse(BaseModel):
    id: uuid.UUID
    recipient_id: Optional[uuid.UUID]
    title: str
    detail: str
    page: Optional[str]
    category: NotificationCategory
    priority: NotificationPriority
    audience_role: Optional[str]
    audience_department_id: Optional[uuid.UUID]
    entity_type: Optional[str]
    entity_id: Optional[uuid.UUID]
    created_at: datetime

    # Computed fields (not in model directly)
    is_read: bool = False
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationMarkRead(BaseModel):
    notification_ids: List[uuid.UUID]
