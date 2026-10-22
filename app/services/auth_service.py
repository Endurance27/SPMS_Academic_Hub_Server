from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import SecurityService
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginResponse


class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.user_repo = UserRepository(db)
        self.security = SecurityService()

    async def authenticate_user(
        self, email: str, password: str
    ) -> Tuple[Optional[User], bool, bool]:
        """
        Authenticate user and return (user, requires_2fa, is_first_time)
        """
        user = await self.user_repo.get_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
            )

        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is locked. Please try again later.",
            )

        # Verify password
        if not self.security.verify_password(password, user.hashed_password):
            await self.user_repo.increment_failed_attempts(user.id)

            # Lock account after max attempts
            if user.failed_login_attempts + 1 >= settings.MAX_LOGIN_ATTEMPTS:
                lock_until = datetime.utcnow() + timedelta(
                    minutes=settings.LOCKOUT_DURATION_MINUTES
                )
                await self.user_repo.lock_account(user.id, lock_until)
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account locked due to too many failed attempts",
                )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
            )

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

        # Check if this is the first login before updating the timestamp
        is_first_time = user.last_login is None

        # Reset failed attempts
        await self.user_repo.update_last_login(user.id)

        # Check if 2FA is required
        requires_2fa = user.two_factor_enabled

        return user, requires_2fa, is_first_time

    async def create_session(
        self, user: User, ip_address: str, user_agent: str, is_first_time: bool = False
    ) -> LoginResponse:
        """Create user session and return tokens"""
        # Create tokens
        token_data = {"sub": str(user.id), "email": user.email, "role": user.role}
        access_token = self.security.create_access_token(token_data)
        refresh_token = self.security.create_refresh_token(token_data)

        # Store session in Redis
        session_key = f"session:{user.id}:{access_token}"
        session_data = {
            "user_id": user.id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow().isoformat(),
        }

        await self.redis.setex(
            session_key, timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES), str(session_data)
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            requires_2fa=False,
            is_first_time=is_first_time,
        )

    async def logout(self, token: str, user_id) -> None:
        """Logout user and invalidate session"""
        # Delete session
        session_key = f"session:{user_id}:{token}"
        await self.redis.delete(session_key)

        # Add token to blacklist
        token_exp = self.security.decode_token(token).get("exp")
        if token_exp:
            exp_seconds = token_exp - datetime.utcnow().timestamp()
            if exp_seconds > 0:
                await self.redis.setex(f"blacklist:{token}", int(exp_seconds), "1")
