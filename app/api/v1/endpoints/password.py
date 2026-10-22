from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.password import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordVerifyCode,
    ResetPasswordRequest,
)
from app.services.password_service import PasswordService

router = APIRouter(prefix="/password", tags=["Password Management"])


@router.post("/forgot")
async def forgot_password(
    request: Request, data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """
    Initiate password reset - Send 6-digit code to email
    """
    password_service = PasswordService(db)

    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")

    await password_service.initiate_password_reset(data.email, ip_address, user_agent)

    return {"message": "If the email exists, a reset code has been sent", "expires_in_minutes": 15}


@router.post("/verify-code")
async def verify_reset_code(data: ForgotPasswordVerifyCode, db: AsyncSession = Depends(get_db)):
    """
    Verify the 6-digit code and return reset token
    """
    password_service = PasswordService(db)

    token = await password_service.verify_reset_code(data.email, data.code)

    return {"token": token, "message": "Code verified successfully"}


@router.post("/reset")
async def reset_password(
    request: Request, data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """
    Reset password using token from verified code
    """
    password_service = PasswordService(db)

    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")

    await password_service.reset_password(data.token, data.new_password, ip_address, user_agent)

    return {"message": "Password reset successfully. You can now login with your new password."}


@router.post("/change")
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change password (requires old password)
    User must be authenticated
    """
    password_service = PasswordService(db)

    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")

    await password_service.change_password(
        current_user.id, data.old_password, data.new_password, ip_address, user_agent
    )

    return {"message": "Password changed successfully"}
