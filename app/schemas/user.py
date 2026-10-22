import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, validator

from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone_number: Optional[str] = None
    role: UserRole


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        return v


class UserStatusUpdate(BaseModel):
    is_active: Optional[bool] = None


class UserRoleUpdate(BaseModel):
    role: Optional[UserRole] = None


class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None


class UserInDB(UserBase):
    id: uuid.UUID
    is_active: bool
    is_verified: bool
    two_factor_enabled: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    phone_number: Optional[str]
    role: UserRole
    is_active: bool
    two_factor_enabled: bool
    last_login: Optional[datetime]

    class Config:
        from_attributes = True

class Pagination(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class UsersListResponse(BaseModel):
    items: List[UserResponse]
    pagination: Pagination
