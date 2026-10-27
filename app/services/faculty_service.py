import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SecurityService
from app.models.course import Course
from app.models.department import Department
from app.models.invitation import Invitation
from app.models.user import User, UserRole, UserStatus
from app.schemas.faculty import FacultyCreate, FacultyUpdate
from app.services.email_service import EmailService


class FacultyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = EmailService()

    async def list_faculty(
        self,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 25,
    ) -> tuple[List[dict], int]:
        query = (
            select(
                User,
                func.count(Course.id).label("course_count"),
            )
            .outerjoin(Course, Course.lecturer_id == User.id)
            .where(User.role == UserRole.LECTURER)
            .group_by(User.id)
        )

        if department_id:
            query = query.where(User.department_id == department_id)
        if status:
            query = query.where(User.status == status)
        if search:
            query = query.where(
                User.name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%")
            )

        count_query = select(func.count()).select_from(
            select(User.id)
            .where(User.role == UserRole.LECTURER)
            .where(User.department_id == department_id if department_id else True)
            .subquery()
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.offset(skip).limit(limit).order_by(User.name)
        result = await self.db.execute(query)
        rows = result.all()

        faculty_list = []
        for user, course_count in rows:
            faculty_list.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "rank": user.rank,
                "staff_id": user.staff_id,
                "department_id": user.department_id,
                "status": user.status,
                "course_count": course_count,
                "last_login_at": user.last_login_at,
                "created_at": user.created_at,
            })

        return faculty_list, total

    async def create_faculty(
        self, data: FacultyCreate, department_id: uuid.UUID
    ) -> User:
        existing = await self.db.execute(
            select(User).where(User.email == data.email.lower().strip())
        )
        if existing.scalar_one_or_none():
            raise ValueError("An account with this email already exists.")

        if data.staff_id:
            existing_staff = await self.db.execute(
                select(User).where(User.staff_id == data.staff_id)
            )
            if existing_staff.scalar_one_or_none():
                raise ValueError("Staff ID already exists.")

        hashed_password = SecurityService.get_password_hash(
            SecurityService.generate_temp_password()
        )

        effective_dept_id = data.department_id or department_id

        user = User(
            email=data.email.lower().strip(),
            hashed_password=hashed_password,
            name=data.name,
            role=UserRole.LECTURER,
            status=UserStatus.INVITED,
            department_id=effective_dept_id,
            staff_id=data.staff_id,
            rank=data.rank,
            title=data.rank.value if data.rank else "Lecturer",
        )
        self.db.add(user)
        await self.db.flush()

        # Create invitation and send email
        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invitation = Invitation(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        self.db.add(invitation)

        await self.db.commit()
        await self.db.refresh(user)

        dept_result = await self.db.execute(
            select(Department.name).where(Department.id == effective_dept_id)
        )
        dept_name = dept_result.scalar_one_or_none()

        await self.email_service.send_invitation_email(
            to_email=user.email,
            user_name=user.name,
            role="lecturer",
            invitation_token=raw_token,
            department_name=dept_name,
        )

        return user

    async def update_faculty(
        self, faculty_id: uuid.UUID, data: FacultyUpdate
    ) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == faculty_id, User.role == UserRole.LECTURER)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def disable_faculty(self, faculty_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == faculty_id, User.role == UserRole.LECTURER)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None

        user.status = UserStatus.DISABLED
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def resend_invitation(self, faculty_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == faculty_id, User.role == UserRole.LECTURER)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None

        user.status = UserStatus.INVITED

        # Expire old invitations
        old_invitations = await self.db.execute(
            select(Invitation).where(
                Invitation.user_id == user.id,
                Invitation.accepted_at.is_(None),
            )
        )
        for old_inv in old_invitations.scalars().all():
            old_inv.expires_at = datetime.now(timezone.utc)

        # Create fresh invitation
        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invitation = Invitation(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        self.db.add(invitation)

        await self.db.commit()
        await self.db.refresh(user)

        dept_result = await self.db.execute(
            select(Department.name).where(Department.id == user.department_id)
        )
        dept_name = dept_result.scalar_one_or_none()

        await self.email_service.send_invitation_email(
            to_email=user.email,
            user_name=user.name,
            role="lecturer",
            invitation_token=raw_token,
            department_name=dept_name,
        )

        return user
