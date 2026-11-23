from uuid import UUID
from typing import Optional, List, Union
from pydantic import BaseModel, Field, field_validator

# Maps "HH:MM" time strings to 0-based period index (07:30 → 0, 08:30 → 1, ...)
_TIME_TO_PERIOD: dict[str, int] = {
    f"{7 + i:02d}:30": i for i in range(12)
}


class SlotRequestCreate(BaseModel):
    course_id: UUID
    semester_id: UUID
    level: int
    day: int = Field(..., ge=0, le=6, description="0 = Monday, 4 = Friday")
    venue_code: str
    start_period: Union[int, str] = Field(
        ...,
        description="Period index (0–11) or time string e.g. '07:30', '08:30'"
    )
    period_count: int = Field(..., ge=1, le=12, description="Number of consecutive periods (1–12)")

    @field_validator("start_period", mode="before")
    @classmethod
    def resolve_start_period(cls, v):
        """Accept either an integer period index or a time string like '07:30'."""
        if isinstance(v, int):
            if not (0 <= v <= 11):
                raise ValueError("start_period index must be between 0 and 11")
            return v
        if isinstance(v, str):
            # Normalise "7:30" → "07:30"
            parts = v.strip().split(":")
            if len(parts) == 2:
                normalised = f"{int(parts[0]):02d}:{parts[1]}"
                if normalised in _TIME_TO_PERIOD:
                    return _TIME_TO_PERIOD[normalised]
            raise ValueError(
                f"Unrecognised time '{v}'. "
                f"Use a period index (0–11) or one of: "
                f"{', '.join(sorted(_TIME_TO_PERIOD.keys()))}"
            )
        raise ValueError("start_period must be an integer index or a time string")


class SlotRequestResponse(BaseModel):
    id: UUID
    course_id: UUID
    meeting_link: Optional[str] = None
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
    schedule_item: Optional[dict] = None
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
