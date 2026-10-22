import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.models.notification import NotificationPriority, NotificationType


class NotificationCreate(BaseModel):
    user_id: uuid.UUID
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    resource_type: Optional[str] = None
    resource_id: Optional[uuid.UUID] = None
    action_url: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    resource_type: Optional[str]
    resource_id: Optional[uuid.UUID]
    action_url: Optional[str]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationMarkRead(BaseModel):
    notification_ids: List[uuid.UUID]
