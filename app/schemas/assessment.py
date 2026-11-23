from datetime import datetime, date
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Valid enum values (must match the Python model and DB enum)
# ---------------------------------------------------------------------------

_VALID_ASSESSMENT_TYPES = {
    "Interim Assessment (IA)": "Interim Assessment (IA)",
    "Quiz": "Quiz",
    "Mid-semester examination": "Mid-semester examination",
    "Final examination": "Final examination",
    "Practical assessment": "Practical assessment",
    "Project presentation": "Project presentation",
}

_VALID_DELIVERY_MODES = {
    # Accept both the DB key and the human-readable label
    "IN_PERSON": "IN_PERSON",
    "In-person": "IN_PERSON",
    "in-person": "IN_PERSON",
    "ONLINE": "ONLINE",
    "Online": "ONLINE",
    "online": "ONLINE",
    "TAKE_HOME_ASSIGNMENT": "TAKE_HOME_ASSIGNMENT",
    "Take-home Assignment": "TAKE_HOME_ASSIGNMENT",
    "take-home assignment": "TAKE_HOME_ASSIGNMENT",
    "TERM_PAPER": "TERM_PAPER",
    "Term Paper": "TERM_PAPER",
    "term paper": "TERM_PAPER",
}

_VALID_SCOPES = {"central", "department", "faculty"}


class AssessmentCreate(BaseModel):
    course_id: Optional[UUID] = None
    course_code: str
    course_title: str
    department_id: UUID
    assessment_type: str
    delivery_mode: str
    date: str = Field(..., description="Assessment date — ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")
    start_time: str = Field(..., description="HH:MM")
    end_time: str = Field(..., description="HH:MM")
    location: str
    venue_code: Optional[str] = None
    cohorts: List[dict] = []
    scope: str = "department"
    is_shared: bool = False

    @field_validator("assessment_type")
    @classmethod
    def validate_assessment_type(cls, v: str) -> str:
        if v not in _VALID_ASSESSMENT_TYPES:
            valid = ", ".join(f'"{k}"' for k in _VALID_ASSESSMENT_TYPES)
            raise ValueError(f"Invalid assessment_type '{v}'. Valid values: {valid}")
        return _VALID_ASSESSMENT_TYPES[v]

    @field_validator("delivery_mode")
    @classmethod
    def validate_delivery_mode(cls, v: str) -> str:
        normalised = _VALID_DELIVERY_MODES.get(v) or _VALID_DELIVERY_MODES.get(v.strip())
        if not normalised:
            valid = '"In-person", "Online", "Take-home Assignment", "Term Paper"'
            raise ValueError(f"Invalid delivery_mode '{v}'. Valid values: {valid}")
        return normalised

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        if v.lower() not in _VALID_SCOPES:
            raise ValueError(f"Invalid scope '{v}'. Valid values: {', '.join(_VALID_SCOPES)}")
        return v.lower()

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Accept YYYY-MM-DD or ISO datetime strings and normalise to YYYY-MM-DD."""
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M"):
            try:
                datetime.strptime(v[:len(fmt) - fmt.count("%") + fmt.count("%") * 2], fmt)
                return v
            except ValueError:
                continue
        # Try native date parse as a last resort
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid date '{v}'. Use ISO format: YYYY-MM-DD")


class AssessmentUpdate(BaseModel):
    course_id: Optional[UUID] = None
    course_code: Optional[str] = None
    course_title: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    venue_code: Optional[str] = None
    cohorts: Optional[List[dict]] = None

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid date '{v}'. Use ISO format: YYYY-MM-DD")


class AssessmentResponse(BaseModel):
    id: UUID
    course_id: Optional[UUID]
    course_code: str
    course_title: str
    department_id: UUID
    assessment_type: str
    delivery_mode: str
    delivery_mode_label: Optional[str] = None
    date: str
    start_time: str
    end_time: str
    location: str
    venue_code: Optional[str]
    cohorts: List[dict]
    status: str
    scope: str
    is_shared: bool
    created_by_id: UUID
    created_by_role: str
    review_comment: Optional[str]
    reviewed_by_id: Optional[UUID]
    reviewed_at: Optional[str]

    class Config:
        from_attributes = True


class AssessmentListResponse(BaseModel):
    data: List[AssessmentResponse]
    meta: dict
