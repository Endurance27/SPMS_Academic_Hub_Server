from pydantic import BaseModel, EmailStr


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
    qr_code: str  # Base64 encoded QR code image
    backup_codes: list[str]


class TwoFactorVerifyRequest(BaseModel):
    code: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
