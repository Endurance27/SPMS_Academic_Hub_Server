import base64
import io
import secrets
from typing import List, Tuple

import pyotp
import qrcode
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.rest import Client as TwilioClient

from app.core.config import settings
from app.models.user import User
from app.repositories.user_repository import UserRepository


class TwoFactorService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.user_repo = UserRepository(db)

        if settings.TWILIO_ACCOUNT_SID:
            self.twilio_client = TwilioClient(
                settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
            )
        else:
            self.twilio_client = None

    async def setup_totp(self, user: User) -> Tuple[str, str, List[str]]:
        """Setup TOTP 2FA and return secret, QR code, and backup codes"""
        # Generate secret
        secret = pyotp.random_base32()

        # Generate QR code
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email, issuer_name=settings.APP_NAME
        )

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

        # Generate backup codes
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]

        # Store backup codes in Redis
        await self.redis.setex(
            f"2fa_backup:{user.id}", 60 * 60 * 24 * 365, ",".join(backup_codes)  # 1 year
        )

        # Update user
        await self.user_repo.update(
            user.id, {"two_factor_secret": secret, "two_factor_method": "totp"}
        )

        return secret, qr_code_base64, backup_codes

    async def verify_totp(self, user: User, code: str) -> bool:
        """Verify TOTP code"""
        if not user.two_factor_secret:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA not set up")

        totp = pyotp.TOTP(user.two_factor_secret)

        # Verify code (with 30 second window)
        if totp.verify(code, valid_window=1):
            return True

        # Check backup codes
        backup_codes_str = await self.redis.get(f"2fa_backup:{user.id}")
        if backup_codes_str:
            backup_codes = backup_codes_str.split(",")
            if code.upper() in backup_codes:
                # Remove used backup code
                backup_codes.remove(code.upper())
                await self.redis.setex(
                    f"2fa_backup:{user.id}", 60 * 60 * 24 * 365, ",".join(backup_codes)
                )
                return True

        return False

    async def send_sms_code(self, user: User) -> bool:
        """Send SMS verification code"""
        if not self.twilio_client or not user.phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="SMS 2FA not available"
            )

        # Generate code
        code = secrets.token_hex(3)

        # Store code in Redis
        await self.redis.setex(f"2fa_sms:{user.id}", settings.OTP_EXPIRE_MINUTES * 60, code)

        # Send SMS
        try:
            self.twilio_client.messages.create(
                body=f"Your {settings.APP_NAME} verification code is: {code}",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=user.phone_number,
            )
            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send SMS: {str(e)}",
            )

    async def verify_sms_code(self, user: User, code: str) -> bool:
        """Verify SMS code"""
        stored_code = await self.redis.get(f"2fa_sms:{user.id}")

        if not stored_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired or not found"
            )

        if stored_code == code:
            await self.redis.delete(f"2fa_sms:{user.id}")
            return True

        return False

    async def enable_2fa(self, user: User) -> None:
        """Enable 2FA for user"""
        await self.user_repo.update(user.id, {"two_factor_enabled": True})

    async def disable_2fa(self, user: User) -> None:
        """Disable 2FA for user"""
        await self.user_repo.update(
            user.id,
            {"two_factor_enabled": False, "two_factor_secret": None, "two_factor_method": None},
        )

        # Clean up Redis data
        await self.redis.delete(f"2fa_backup:{user.id}")
        await self.redis.delete(f"2fa_sms:{user.id}")
