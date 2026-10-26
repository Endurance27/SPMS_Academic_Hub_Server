import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    actor_name: str
    actor_role: str
    action: str
    category: str
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    summary: str
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    revision: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    data: List[AuditLogResponse]
    meta: Optional[dict] = None
