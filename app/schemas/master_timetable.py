from uuid import UUID
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class TimetablePublishRequest(BaseModel):
    preview_id: str


class TimetablePreviewResponse(BaseModel):
    preview_id: str
    entries: List[Dict[str, Any]]
    issues: List[Dict[str, Any]]
    summary: Dict[str, Any]
    replaces: Optional[Dict[str, Any]]
    affected_requests: List[Dict[str, Any]]


class DepartmentTimetablePreviewResponse(BaseModel):
    preview_id: str
    entries: List[Dict[str, Any]]
    conflicts: List[Dict[str, Any]]
    summary: Dict[str, Any]


class TimetableListResponse(BaseModel):
    data: List[Dict[str, Any]]


class TimetableEntriesResponse(BaseModel):
    data: List[Dict[str, Any]]
    meta: Dict[str, Any]
