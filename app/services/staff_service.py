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
from app.schemas.staff import StaffCreate, StaffUpdate
from app.services.email_service import EmailService


class StaffService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = EmailService()

    async def list_staff(
        self,
        role: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 25,
    ) -> tuple[List[dict], dict]:
        query = (
            select(
                User,
                func.count(Course.id).label("course_count"),
                Department.name.label("department_name"),
            )
            .outerjoin(Course, Course.lecturer_id == User.id)
            .outerjoin(Department, Department.id == User.department_id)
            .where(User.role != UserRole.STUDENT)
            .group_by(User.id, Department.name)
        )

        if role:
            query = query.where(User.role == role)
        if status:
            query = query.where(User.status == status)
        if search:
            query = query.where(
                User.name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%")
            )

        # Tab counts
        base_filter = User.role != UserRole.STUDENT
        admin_count = await self._count_by_role(
            [UserRole.SUPER, UserRole.DEPARTMENT], search
        )
        faculty_count = await self._count_by_role([UserRole.LECTURER], search)

        query = query.offset(skip).limit(limit).order_by(User.name)
        result = await self.db.execute(query)
        rows = result.all()

        staff_list = []
        for user, course_count, department_name in rows:
            staff_list.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "rank": user.rank,
                "staff_id": user.staff_id,
                "department_id": user.department_id,
                "department_name": department_name,
                "status": user.status,
                "course_count": course_count,
                "last_login_at": user.last_login_at,
                "created_at": user.created_at,
            })

        counts = {
            "Administrators": admin_count,
            "Faculty": faculty_count,
            "All": admin_count + faculty_count,
        }

        return staff_list, counts

    async def _count_by_role(
        self, roles: list, search: Optional[str] = None
    ) -> int:
        query = select(func.count()).select_from(User).where(User.role.in_(roles))
        if search:
            query = query.where(
                User.name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%")
            )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def create_staff(self, data: StaffCreate) -> User:
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

        temporary_password = SecurityService.generate_role_temp_password(
            "staff", data.staff_id
        )
        hashed_password = SecurityService.get_password_hash(temporary_password)

        user = User(
            email=data.email.lower().strip(),
            hashed_password=hashed_password,
            name=data.name,
            role=data.role,
            status=UserStatus.INVITED,
            department_id=data.department_id,
            staff_id=data.staff_id,
            rank=data.rank,
            title=data.rank.value if data.rank else data.role.value.title(),
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

        dept_name = None
        if user.department_id:
            dept_result = await self.db.execute(
                select(Department.name).where(Department.id == user.department_id)
            )
            dept_name = dept_result.scalar_one_or_none()

        role_str = data.role.value if hasattr(data.role, "value") else str(data.role)
        await self.email_service.send_invitation_email(
            to_email=user.email,
            user_name=user.name,
            role=role_str,
            invitation_token=raw_token,
            department_name=dept_name,
            temporary_password=temporary_password,
        )

        return user

    async def update_staff(
        self, staff_id: uuid.UUID, data: StaffUpdate
    ) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == staff_id, User.role != UserRole.STUDENT)
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
