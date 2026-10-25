from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, Field


class SlotRequestCreate(BaseModel):
    course_id: UUID
    semester_id: UUID
    level: int
    day: int
    venue_code: str
    start_period: int
    period_count: int = Field(..., ge=1, le=3)


class SlotRequestResponse(BaseModel):
    id: UUID
    course_id: UUID
    department_id: UUID
    requested_by_id: UUID
    semester_id: UUID
    level: int
    day: int
    venue_code: str
    start_period: int
    period_count: int
    status: str
    review_comment: Optional[str]
    reviewed_by_id: Optional[UUID]
    reviewed_at: Optional[str]
    schedule_item_id: Optional[UUID]
    clashes: List[dict] = []
    competing: List[dict] = []

    class Config:
        from_attributes = True


class SlotRequestListResponse(BaseModel):
    data: List[SlotRequestResponse]
    meta: dict


class SlotRequestCheckResponse(BaseModel):
    clashes: List[dict]
    blocking: bool
