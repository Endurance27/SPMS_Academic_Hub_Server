from enum import Enum
from uuid import UUID
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, field_validator


class DeliveryMode(str, Enum):
    IN_PERSON = "in-person"
    VIRTUAL = "virtual"
    HYBRID = "hybrid"


class MasterEntryUpdate(BaseModel):
    subject: Optional[str] = None
    venue_code: Optional[str] = None
    is_free: Optional[bool] = None
    day: Optional[int] = None
    period: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    course_kind: Optional[str] = None
    programme: Optional[str] = None
    lecturer_name: Optional[str] = None
    course_title: Optional[str] = None
    delivery_mode: Optional[DeliveryMode] = None

    @field_validator("day")
    @classmethod
    def validate_day(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 <= v <= 6):
            raise ValueError("day must be 0-6 (Mon-Sun)")
        return v

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("period must be non-negative")
        return v


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
    warnings: List[Dict[str, Any]] = []
    summary: Dict[str, Any]


class TimetableListResponse(BaseModel):
    data: List[Dict[str, Any]]
    meta: Optional[Dict[str, Any]] = None


class TimetableEntriesResponse(BaseModel):
    data: List[Dict[str, Any]]
    meta: Dict[str, Any]
