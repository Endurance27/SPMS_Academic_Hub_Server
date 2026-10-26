import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ImportResponse(BaseModel):
    id: uuid.UUID
    kind: str
    department_id: uuid.UUID
    course_id: Optional[uuid.UUID] = None
    programme_id: Optional[uuid.UUID] = None
    programme_text: Optional[str] = None
    level_text: Optional[str] = None
    student_category: Optional[str] = None
    academic_year: Optional[str] = None
    semester_id: Optional[uuid.UUID] = None
    filename: str
    file_url: Optional[str] = None
    row_count: Optional[int] = None
    created_count: int = 0
    updated_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    status: str
    created_by_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ImportListResponse(BaseModel):
    data: List[ImportResponse]
    meta: Optional[dict] = None


class ImportRowResponse(BaseModel):
    id: uuid.UUID
    import_id: uuid.UUID
    row_number: int
    raw: Optional[Dict[str, Any]] = None
    outcome: Optional[str] = None
    message: Optional[str] = None

    class Config:
        from_attributes = True


class ImportRowListResponse(BaseModel):
    data: List[ImportRowResponse]
    meta: Optional[dict] = None
