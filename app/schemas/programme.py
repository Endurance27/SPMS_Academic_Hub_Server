import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.programme import ProgrammeCategory


class ProgrammeBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    department_ids: List[uuid.UUID] = Field(..., min_length=1)
    levels: List[int] = Field(..., min_length=1)
    category: ProgrammeCategory

    @field_validator("department_ids")
    @classmethod
    def unique_department_ids(cls, v: List[uuid.UUID]) -> List[uuid.UUID]:
        if len(v) != len(set(v)):
            raise ValueError("Duplicate department IDs are not allowed")
        return v


class ProgrammeCreate(ProgrammeBase):
    pass


class ProgrammeUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    department_ids: Optional[List[uuid.UUID]] = Field(None, min_length=1)
    levels: Optional[List[int]] = Field(None, min_length=1)
    category: Optional[ProgrammeCategory] = None

    @field_validator("department_ids")
    @classmethod
    def unique_department_ids(cls, v: Optional[List[uuid.UUID]]) -> Optional[List[uuid.UUID]]:
        if v is not None and len(v) != len(set(v)):
            raise ValueError("Duplicate department IDs are not allowed")
        return v


class DepartmentBrief(BaseModel):
    id: uuid.UUID
    name: str
    code: str

    class Config:
        from_attributes = True


class ProgrammeResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    departments: List[DepartmentBrief]
    levels: List[int]
    category: ProgrammeCategory
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProgrammeListResponse(BaseModel):
    data: List[ProgrammeResponse]
    meta: Optional[dict] = None
