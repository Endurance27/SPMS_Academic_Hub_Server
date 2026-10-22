from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, get_redis
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
)
from app.services.auth_service import AuthService
from app.services.two_factor_service import TwoFactorService

router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer()


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Login endpoint"""
    auth_service = AuthService(db, redis)

    # Authenticate user
    user, requires_2fa, is_first_time = await auth_service.authenticate_user(
        credentials.email, credentials.password
    )

    if requires_2fa:
        # Create session because 2FA is required
        ip_address = request.client.host
        user_agent = request.headers.get("user-agent", "")

        # Store a pending flag for the /2fa/verify endpoint to check
        await redis.setex(f"pending_2fa:{user.id}", 300, "1")  # 5 minutes

        # Create the session and return tokens, but flag that 2FA is still needed
        session_response = await auth_service.create_session(
            user, ip_address, user_agent, is_first_time
        )
        session_response.requires_2fa = True
        return session_response
    else:
        # Return a response indicating no access
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Login is only permitted for users with 2FA enabled.",
        )


@router.post("/2fa/verify", response_model=LoginResponse)
async def verify_2fa(
    request: Request,
    data: TwoFactorVerifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Verify 2FA code and complete login"""
    two_fa_service = TwoFactorService(db, redis)
    auth_service = AuthService(db, redis)

    # Check if 2FA is pending
    is_pending = await redis.get(f"pending_2fa:{user.id}")
    if not is_pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No pending 2FA verification"
        )

    # Verify code
    verified = False
    if user.two_factor_method == "totp":
        verified = await two_fa_service.verify_totp(user, data.code)
    elif user.two_factor_method == "sms":
        verified = await two_fa_service.verify_sms_code(user, data.code)

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid verification code"
        )

    # Remove pending flag
    await redis.delete(f"pending_2fa:{user.id}")

    # Create session
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "")

    return await auth_service.create_session(user, ip_address, user_agent)


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Setup TOTP 2FA"""
    two_fa_service = TwoFactorService(db, redis)

    secret, qr_code, backup_codes = await two_fa_service.setup_totp(user)

    return TwoFactorSetupResponse(secret=secret, qr_code=qr_code, backup_codes=backup_codes)


@router.post("/2fa/enable")
async def enable_2fa(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Enable 2FA after setup"""
    two_fa_service = TwoFactorService(db, redis)
    await two_fa_service.enable_2fa(user)
    return {"message": "2FA enabled successfully"}


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Logout endpoint"""
    auth_service = AuthService(db, redis)
    await auth_service.logout(credentials.credentials, user.id)
    return {"message": "Logged out successfully"}
