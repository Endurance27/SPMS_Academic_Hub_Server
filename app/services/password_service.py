import random
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SecurityService
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService


class PasswordService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.security = SecurityService()
        self.email_service = EmailService()

    def _generate_reset_code(self) -> str:
        """Generate 6-digit code"""
        return "".join([str(random.randint(0, 9)) for _ in range(6)])

    def _generate_reset_token(self) -> str:
        """Generate secure token"""
        return secrets.token_urlsafe(32)

    async def initiate_password_reset(self, email: str, ip_address: str, user_agent: str) -> bool:
        """Initiate password reset - send code to email"""
        # Find user
        user = await self.user_repo.get_by_email(email)

        if not user:
            # Don't reveal if email exists or not
            return True

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

        # Invalidate any existing unused tokens for this user
        await self.db.execute(
            text(
                """
                UPDATE password_reset_tokens 
                SET is_used = true 
                WHERE user_id = :user_id AND is_used = false
                """
            ),
            {"user_id": user.id},
        )
        await self.db.commit()

        # Generate code and token
        code = self._generate_reset_code()
        token = self._generate_reset_token()

        # Create reset token
        reset_token = PasswordResetToken(
            user_id=user.id,
            code=code,
            token=token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(minutes=15),  # 15 minutes expiry
            is_used=False,
        )

        self.db.add(reset_token)
        await self.db.commit()

        # Send email with code
        self.email_service.send_password_reset_code_email(
            to_email=user.email,
            user_name=f"{user.first_name} {user.last_name}",
            reset_code=code,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return True

    async def verify_reset_code(self, email: str, code: str) -> str:
        """Verify reset code and return token"""
        # Find user
        user = await self.user_repo.get_by_email(email)

        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")

        # Find valid reset token
        result = await self.db.execute(
            select(PasswordResetToken).where(
                and_(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.code == code,
                    PasswordResetToken.is_used == False,
                    PasswordResetToken.expires_at > datetime.utcnow(),
                )
            )
        )
        reset_token = result.scalar_one_or_none()

        if not reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code"
            )

        return reset_token.token

    async def reset_password(
        self, token: str, new_password: str, ip_address: str, user_agent: str
    ) -> User:
        """Reset password using token"""
        # Find valid reset token
        result = await self.db.execute(
            select(PasswordResetToken).where(
                and_(
                    PasswordResetToken.token == token,
                    PasswordResetToken.is_used == False,
                    PasswordResetToken.expires_at > datetime.utcnow(),
                )
            )
        )
        reset_token = result.scalar_one_or_none()

        if not reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token"
            )

        # Get user
        user = await self.user_repo.get_by_id(reset_token.user_id)

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Update password
        user.hashed_password = self.security.get_password_hash(new_password)

        # Reset failed login attempts
        user.failed_login_attempts = 0
        user.locked_until = None

        # Mark token as used
        reset_token.is_used = True
        reset_token.used_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(user)

        # Send confirmation email
        self.email_service.send_password_changed_notification_email(
            to_email=user.email,
            user_name=f"{user.first_name} {user.last_name}",
            ip_address=ip_address,
            user_agent=user_agent,
            change_type="reset",
        )

        return user

    async def change_password(
        self, user_id: int, old_password: str, new_password: str, ip_address: str, user_agent: str
    ) -> User:
        """Change password (requires old password)"""
        # Get user
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Verify old password
        if not self.security.verify_password(old_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect old password"
            )

        # Check if new password is same as old
        if self.security.verify_password(new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from old password",
            )

        # Update password
        user.hashed_password = self.security.get_password_hash(new_password)

        await self.db.commit()
        await self.db.refresh(user)

        # Send confirmation email
        self.email_service.send_password_changed_notification_email(
            to_email=user.email,
            user_name=f"{user.first_name} {user.last_name}",
            ip_address=ip_address,
            user_agent=user_agent,
            change_type="change",
        )

        return user
