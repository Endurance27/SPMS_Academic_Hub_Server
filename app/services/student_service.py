import uuid
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.programme import Programme
from app.models.user import User, UserRole


class StudentService:
    def __init__(self, db: AsyncSession):
        self.db = db

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
