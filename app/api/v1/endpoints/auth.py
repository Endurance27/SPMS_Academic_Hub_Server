import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db, get_redis
from app.core.security import SecurityService
from app.models.invitation import Invitation
from app.models.role import Role
from app.models.user import User, UserRole, UserStatus
from app.schemas.auth import (
    AcceptInvitationRequest,
    InvitationInfoResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    UserMeResponse,
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

    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "")

    if requires_2fa:
        await redis.setex(f"pending_2fa:{user.id}", 300, "1")

        session_response = await auth_service.create_session(
            user, ip_address, user_agent, is_first_time
        )
        session_response.requires_2fa = True
        return session_response
    else:
        return await auth_service.create_session(
            user, ip_address, user_agent, is_first_time
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


@router.post("/2fa/disable")
async def disable_2fa(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Disable 2FA"""
    if not user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled.",
        )
    two_fa_service = TwoFactorService(db, redis)
    await two_fa_service.disable_2fa(user)
    return {"message": "2FA disabled successfully"}


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


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Student self-registration"""
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository(db)

    existing = await user_repo.get_by_email(data.email.lower().strip())
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    existing_sn = await user_repo.get_by_student_number(data.student_number)
    if existing_sn:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this student number already exists.",
        )

    from app.models.programme import Programme

    result = await db.execute(select(Programme).where(Programme.id == data.programme_id))
    programme = result.scalar_one_or_none()
    if not programme:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid programme.",
        )

    user = User(
        email=data.email.lower().strip(),
        hashed_password=SecurityService.get_password_hash(data.password),
        name=data.name,
        role=UserRole.STUDENT,
        status=UserStatus.ACTIVE,
        programme_id=data.programme_id,
        department_id=programme.department_id,
        level=data.level,
        student_number=data.student_number,
        student_category="Undergraduate" if data.level <= 400 else "Postgraduate",
        title=f"Level {data.level} Student",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    auth_service = AuthService(db, redis)
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "")
    return await auth_service.create_session(user, ip_address, user_agent, is_first_time=True)


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    request: Request,
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Rotate refresh token and issue new access token"""
    try:
        payload = SecurityService.decode_token(data.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type.",
        )

    from app.repositories.user_repository import UserRepository
    import uuid as _uuid

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(_uuid.UUID(payload["sub"]))
    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    auth_service = AuthService(db, redis)
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "")
    return await auth_service.create_session(user, ip_address, user_agent)


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user profile with permissions and related data"""
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.department),
            selectinload(User.programme),
        )
        .where(User.id == current_user.id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    permissions = []
    if user.role == UserRole.SUPER:
        from app.utils.constants import get_all_permissions

        permissions = get_all_permissions()
    else:
        for role in user.roles:
            for perm in role.permissions:
                if perm.code not in permissions:
                    permissions.append(perm.code)

    dept_summary = None
    if user.department:
        dept_summary = {
            "id": user.department.id,
            "name": user.department.name,
            "code": user.department.code,
        }

    prog_summary = None
    if user.programme:
        prog_summary = {
            "id": user.programme.id,
            "name": user.programme.name,
            "code": user.programme.code,
        }

    return UserMeResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value if hasattr(user.role, "value") else user.role,
        status=user.status.value if hasattr(user.status, "value") else user.status,
        department_id=user.department_id,
        programme_id=user.programme_id,
        level=user.level,
        student_category=user.student_category.value if user.student_category else None,
        student_number=user.student_number,
        staff_id=user.staff_id,
        rank=user.rank.value if user.rank else None,
        phone=user.phone,
        office=user.office,
        photo_url=user.photo_url,
        title=user.title,
        two_factor_enabled=user.two_factor_enabled,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        department=dept_summary,
        programme=prog_summary,
        permissions=permissions,
    )


@router.post("/accept-invitation", response_model=LoginResponse)
async def accept_invitation(
    request: Request,
    data: AcceptInvitationRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Accept an invitation and activate the account"""
    token_hash = hashlib.sha256(data.token.encode()).hexdigest()

    result = await db.execute(
        select(Invitation)
        .options(selectinload(Invitation.user))
        .where(Invitation.token_hash == token_hash)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token.",
        )

    if invitation.accepted_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This invitation has already been accepted.",
        )

    if invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This invitation has expired.",
        )

    user = invitation.user
    user.hashed_password = SecurityService.get_password_hash(data.password)
    user.status = UserStatus.ACTIVE
    if data.name:
        user.name = data.name

    invitation.accepted_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)

    auth_service = AuthService(db, redis)
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "")
    return await auth_service.create_session(user, ip_address, user_agent, is_first_time=True)


@router.get("/invitation/{token}", response_model=InvitationInfoResponse)
async def get_invitation_info(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get invitation details for the activation screen"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    result = await db.execute(
        select(Invitation)
        .options(selectinload(Invitation.user))
        .where(Invitation.token_hash == token_hash)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token.",
        )

    if invitation.accepted_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This invitation has already been accepted.",
        )

    if invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This invitation has expired.",
        )

    user = invitation.user
    return InvitationInfoResponse(
        email=user.email,
        name=user.name,
        role=user.role.value if hasattr(user.role, "value") else user.role,
    )
