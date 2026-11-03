import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SecurityService
from app.models.invitation import Invitation
from app.models.programme import Programme
from app.models.user import User, UserRole, UserStatus
from app.services.email_service import EmailService


class StudentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = EmailService()

    async def onboard_student(
        self,
        name: str,
        email: str,
        student_number: Optional[str] = None,
        programme_id: Optional[uuid.UUID] = None,
        level: Optional[int] = None,
        student_category: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
    ) -> tuple[User, str]:
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise ValueError("A user with this email already exists.")

        if student_number:
            existing_sn = await self.db.execute(
                select(User).where(User.student_number == student_number)
            )
            if existing_sn.scalar_one_or_none():
                raise ValueError("A student with this student number already exists.")

        temp_password = SecurityService.generate_role_temp_password("student", email)
        hashed_pw = SecurityService.get_password_hash(temp_password)

        student = User(
            email=email,
            hashed_password=hashed_pw,
            name=name,
            role=UserRole.STUDENT,
            status=UserStatus.INVITED,
            student_number=student_number or None,
            programme_id=programme_id,
            level=level,
            student_category=student_category,
            department_id=department_id,
            title=f"Level {level} Student" if level else "Student",
        )
        self.db.add(student)
        await self.db.flush()

        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invitation = Invitation(
            user_id=student.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        self.db.add(invitation)

        await self.db.commit()
        await self.db.refresh(student)

        programme_name = None
        if programme_id:
            prog_result = await self.db.execute(
                select(Programme.name).where(Programme.id == programme_id)
            )
            programme_name = prog_result.scalar_one_or_none()

        await self.email_service.send_invitation_email(
            to_email=email,
            user_name=name,
            role="student",
            invitation_token=raw_token,
            department_name=programme_name,
            temporary_password=temp_password,
        )

        return student, temp_password

    async def list_students(
        self,
        department_id: Optional[uuid.UUID] = None,
        programme_id: Optional[uuid.UUID] = None,
        level: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 25,
    ) -> tuple[List[dict], int]:
        query = (
            select(User, Programme.name.label("programme_name"))
            .outerjoin(Programme, Programme.id == User.programme_id)
            .where(User.role == UserRole.STUDENT)
        )

        if department_id:
            query = query.where(
                User.programme_id.in_(
                    select(Programme.id).where(Programme.department_id == department_id)
                )
            )
        if programme_id:
            query = query.where(User.programme_id == programme_id)
        if level:
            query = query.where(User.level == level)
        if search:
            query = query.where(
                User.name.ilike(f"%{search}%")
                | User.email.ilike(f"%{search}%")
                | User.student_number.ilike(f"%{search}%")
            )

        count_q = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_q)
        total = total_result.scalar() or 0

        query = query.offset(skip).limit(limit).order_by(User.name)
        result = await self.db.execute(query)
        rows = result.all()

        students = []
        for user, programme_name in rows:
            students.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "student_number": user.student_number,
                "programme_id": user.programme_id,
                "programme_name": programme_name,
                "level": user.level,
                "student_category": user.student_category,
                "status": user.status,
                "created_at": user.created_at,
            })

        return students, total

    async def get_cohorts(
        self,
        department_id: Optional[uuid.UUID] = None,
    ) -> List[dict]:
        query = (
            select(
                User.programme_id,
                Programme.name.label("programme_name"),
                User.level,
                func.count(User.id).label("student_count"),
            )
            .join(Programme, Programme.id == User.programme_id)
            .where(User.role == UserRole.STUDENT)
            .where(User.programme_id.isnot(None))
            .where(User.level.isnot(None))
            .group_by(User.programme_id, Programme.name, User.level)
            .order_by(Programme.name, User.level)
        )

        if department_id:
            query = query.where(Programme.department_id == department_id)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "programme_id": row.programme_id,
                "programme_name": row.programme_name,
                "level": row.level,
                "student_count": row.student_count,
            }
            for row in rows
        ]
