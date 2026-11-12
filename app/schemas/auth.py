import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    requires_2fa: bool = False
    is_first_time: bool = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TwoFactorSetupResponse(BaseModel):
    secret: str
    qr_code: str
    backup_codes: list[str]


class TwoFactorVerifyRequest(BaseModel):
    code: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=1, max_length=255)
    student_number: str = Field(..., min_length=1, max_length=50)
    programme_id: uuid.UUID
    level: int = Field(..., ge=100, le=900)


class AcceptInvitationRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8)
    name: Optional[str] = None


class InvitationInfoResponse(BaseModel):
    email: str
    name: str
    role: str


class DepartmentSummary(BaseModel):
    id: uuid.UUID
    name: str
    code: str

    class Config:
        from_attributes = True


class ProgrammeSummary(BaseModel):
    id: uuid.UUID
    name: str
    code: str

    class Config:
        from_attributes = True


class UserMeResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: str
    status: str
    department_id: Optional[uuid.UUID] = None
    programme_id: Optional[uuid.UUID] = None
    level: Optional[int] = None
    student_category: Optional[str] = None
    student_number: Optional[str] = None
    staff_id: Optional[str] = None
    rank: Optional[str] = None
    phone: Optional[str] = None
    office: Optional[str] = None
    photo_url: Optional[str] = None
    title: Optional[str] = None
    two_factor_enabled: bool = False
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    department: Optional[DepartmentSummary] = None
    programme: Optional[ProgrammeSummary] = None
    permissions: List[str] = []

    class Config:
        from_attributes = True
