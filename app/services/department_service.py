import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SecurityService
from app.models.department import Department
from app.models.invitation import Invitation
from app.models.role import RoleTemplate
from app.models.settings import DepartmentSettings
from app.models.user import User, UserRole, UserStatus
from app.repositories.department_repository import DepartmentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services.email_service import EmailService


class DepartmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.department_repo = DepartmentRepository(db)
        self.user_repo = UserRepository(db)
        self.email_service = EmailService()

    async def create_department(
        self, data: DepartmentCreate, created_by_id: uuid.UUID, generate_temp_password: bool = False
    ) -> tuple[Department, Optional[str]]:
        """Create a department with its admin account"""
        # Check if code or name already exists
        existing_by_code = await self.department_repo.get_by_code(data.code)
        if existing_by_code:
            raise ValueError("Department code already exists")

        existing_by_name = await self.department_repo.get_by_name(data.name)
        if existing_by_name:
            raise ValueError("Department name already exists")

        # Create department
        department = Department(
            name=data.name,
            code=data.code.upper(),
            school=data.school,
            email=data.email,
            phone=data.phone,
            tone=data.tone,
            subject_prefixes=data.subject_prefixes or [],
        )
        self.db.add(department)
        await self.db.flush()

        # Create department settings with defaults
        settings = DepartmentSettings(
            department_id=department.id,
            department_name=data.name,
            department_code=data.code.upper(),
            support_email=data.email,
            teaching_start="08:00",
            teaching_end="18:00",
            default_class_duration=60,
            capacity_tolerance=0,
            allow_weekends=False,
            require_conflict_approval=False,
            auto_publish_approved=False,
            notify_schedule_changes=True,
            notify_graduation_submissions=True,
            notify_conflicts=True,
            email_channel=True,
            in_app_channel=True,
        )
        self.db.add(settings)

        # Create department admin account
        temp_password = None
        if generate_temp_password:
            temp_password = SecurityService.generate_role_temp_password(
                "department", data.phone
            )
            initial_password = temp_password
        else:
            initial_password = "ChangeMe123!"  # Will be forced to change
        hashed_password = SecurityService.get_password_hash(initial_password)

        admin_user = User(
            email=data.email,
            hashed_password=hashed_password,
            name=data.name,
            role=UserRole.DEPARTMENT,
            status=UserStatus.INVITED,
            department_id=department.id,
            title="Department Administrator",
        )
        self.db.add(admin_user)
        await self.db.flush()

        # Create invitation record and send email
        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invitation = Invitation(
            user_id=admin_user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        self.db.add(invitation)

        await self.db.commit()
        await self.db.refresh(department)

        await self.email_service.send_invitation_email(
            to_email=data.email,
            user_name=data.name,
            role="department",
            invitation_token=raw_token,
            department_name=data.name,
            temporary_password=initial_password,
        )

        return department, temp_password

    async def get_department(self, department_id: uuid.UUID) -> Optional[dict]:
        """Get department with statistics"""
        return await self.department_repo.get_with_stats(department_id)

    async def list_departments(
        self, search: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> List[Department]:
        """List departments with optional search"""
        return await self.department_repo.list_with_counts(search, skip, limit)

    async def update_department(
        self, department_id: uuid.UUID, data: DepartmentUpdate
    ) -> Optional[Department]:
        """Update department"""
        department = await self.department_repo.get_by_id(department_id)
        if not department:
            return None

        # Check for duplicate code/name if changed
        if data.code and data.code != department.code:
            existing = await self.department_repo.get_by_code(data.code)
            if existing:
                raise ValueError("Department code already exists")

        if data.name and data.name != department.name:
            existing = await self.department_repo.get_by_name(data.name)
            if existing:
                raise ValueError("Department name already exists")

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        if update_data.get("code"):
            update_data["code"] = update_data["code"].upper()

        for field, value in update_data.items():
            setattr(department, field, value)

        await self.db.commit()
        await self.db.refresh(department)

        return department

    async def delete_department(
        self, department_id: uuid.UUID, force: bool = False, lecturers_action: str = "disable"
    ) -> bool:
        """Delete department with cascade handling"""
        department = await self.department_repo.get_by_id(department_id)
        if not department:
            return False

        # Check for approved slot requests if not force
        if not force:
            from app.models.slot_request import SlotRequest, SlotRequestStatus
            from app.models.schedule_item import ScheduleItem

            # Check for approved slot requests in active semester
            approved_requests = await self.db.execute(
                select(func.count())
                .select_from(SlotRequest)
                .where(
                    SlotRequest.department_id == department_id,
                    SlotRequest.status == SlotRequestStatus.APPROVED,
                )
            )
            if approved_requests.scalar() > 0:
                raise ValueError(
                    "Cannot delete department with approved slot requests. Use force=true to override."
                )

        # Handle lecturers
        if lecturers_action == "disable":
            await self.db.execute(
                select(User).where(
                    User.department_id == department_id, User.role == UserRole.LECTURER
                )
            )
            # Update would go here - for now just cascade

        # Disassociate or delete users before removing the department.
        # The users.department_id FK has no ON DELETE cascade, and the
        # department admin's email must be freed so it can be reused.
        department_users = (
            (await self.db.execute(select(User).where(User.department_id == department_id)))
            .scalars()
            .all()
        )

        for user in department_users:
            if user.role == UserRole.DEPARTMENT:
                await self.db.delete(user)
            elif user.role == UserRole.LECTURER and lecturers_action == "disable":
                user.status = UserStatus.DISABLED
                user.department_id = None
            else:
                user.department_id = None

        # Department will cascade delete programmes, courses, and disable admin
        await self.db.delete(department)
        await self.db.commit()

        return True

    async def resend_invitation(self, department_id: uuid.UUID) -> Optional[User]:
        """Resend invitation to department admin"""
        admin_result = await self.db.execute(
            select(User).where(
                User.department_id == department_id,
                User.role == UserRole.DEPARTMENT,
            )
        )
        admin = admin_result.scalar_one_or_none()

        if not admin:
            return None

        admin.status = UserStatus.INVITED

        # Expire any old invitations for this user
        old_invitations = await self.db.execute(
            select(Invitation).where(
                Invitation.user_id == admin.id,
                Invitation.accepted_at.is_(None),
            )
        )
        for old_inv in old_invitations.scalars().all():
            old_inv.expires_at = datetime.now(timezone.utc)

        # Create fresh invitation
        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invitation = Invitation(
            user_id=admin.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        self.db.add(invitation)

        await self.db.commit()
        await self.db.refresh(admin)

        department = await self.department_repo.get_by_id(department_id)
        await self.email_service.send_invitation_email(
            to_email=admin.email,
            user_name=admin.name,
            role="department",
            invitation_token=raw_token,
            department_name=department.name if department else None,
        )

        return admin
