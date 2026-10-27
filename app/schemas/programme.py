import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.programme import ProgrammeCategory


class ProgrammeBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    department_id: uuid.UUID
    levels: List[int] = Field(..., min_items=1)
    category: ProgrammeCategory


class ProgrammeCreate(ProgrammeBase):
    pass


class ProgrammeUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    levels: Optional[List[int]] = Field(None, min_items=1)
    category: Optional[ProgrammeCategory] = None


class ProgrammeResponse(ProgrammeBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProgrammeListResponse(BaseModel):
    data: List[ProgrammeResponse]
    meta: Optional[dict] = None
