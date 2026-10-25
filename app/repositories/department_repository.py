import uuid
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.models.user import User, UserRole
from app.models.programme import Programme
from app.models.course import Course
from app.repositories.base import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    def __init__(self, db: AsyncSession):
        super().__init__(Department, db)

    async def get_by_code(self, code: str) -> Optional[Department]:
        result = await self.db.execute(
            select(Department).where(Department.code == code)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Department]:
        result = await self.db.execute(
            select(Department).where(Department.name == name)
        )
        return result.scalar_one_or_none()

    async def list_with_counts(
        self,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Department]:
        query = select(Department)
        
        if search:
            query = query.where(
                (Department.name.ilike(f"%{search}%")) |
                (Department.code.ilike(f"%{search}%"))
            )
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_with_stats(self, department_id: uuid.UUID) -> Optional[dict]:
        """Get department with counts of related entities"""
        result = await self.db.execute(
            select(Department).where(Department.id == department_id)
        )
        department = result.scalar_one_or_none()
        
        if not department:
            return None
        
        # Count programmes
        programmes_result = await self.db.execute(
            select(func.count()).select_from(Programme).where(Programme.department_id == department_id)
        )
        programmes_count = programmes_result.scalar()
        
        # Count courses
        courses_result = await self.db.execute(
            select(func.count()).select_from(Course).where(Course.department_id == department_id)
        )
        courses_count = courses_result.scalar()
        
        # Count lecturers
        lecturers_result = await self.db.execute(
            select(func.count()).select_from(User).where(
                User.department_id == department_id,
                User.role == UserRole.LECTURER
            )
        )
        lecturers_count = lecturers_result.scalar()
        
        # Count students
        students_result = await self.db.execute(
            select(func.count()).select_from(User).where(
                User.department_id == department_id,
                User.role == UserRole.STUDENT
            )
        )
        students_count = students_result.scalar()
        
        # Get admin account
        admin_result = await self.db.execute(
            select(User).where(
                User.department_id == department_id,
                User.role == UserRole.DEPARTMENT
            )
        )
        admin = admin_result.scalar_one_or_none()
        
        return {
            "department": department,
            "programmes_count": programmes_count or 0,
            "courses_count": courses_count or 0,
            "lecturers_count": lecturers_count or 0,
            "students_count": students_count or 0,
            "admin_account": {
                "id": admin.id,
                "email": admin.email,
                "status": admin.status.value if admin else None
            } if admin else None
        }
