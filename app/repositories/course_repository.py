import uuid
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.user import UserRole
from app.repositories.base import BaseRepository


class CourseRepository(BaseRepository[Course]):
    def __init__(self, db: AsyncSession):
        super().__init__(Course, db)

    async def get_by_code(self, code: str) -> Optional[Course]:
        result = await self.db.execute(
            select(Course).where(Course.code == code)
        )
        return result.scalar_one_or_none()

    async def list_by_department(
        self,
        department_id: uuid.UUID,
        lecturer_id: Optional[uuid.UUID] = None,
        programme_id: Optional[uuid.UUID] = None,
        level: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Course]:
        query = select(Course).where(Course.department_id == department_id)
        
        if lecturer_id:
            query = query.where(Course.lecturer_id == lecturer_id)
        
        if search:
            query = query.where(
                (Course.code.ilike(f"%{search}%")) |
                (Course.title.ilike(f"%{search}%"))
            )
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_all(
        self,
        department_id: Optional[uuid.UUID] = None,
        lecturer_id: Optional[uuid.UUID] = None,
        programme_id: Optional[uuid.UUID] = None,
        level: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Course]:
        query = select(Course)
        
        if department_id:
            query = query.where(Course.department_id == department_id)
        if lecturer_id:
            query = query.where(Course.lecturer_id == lecturer_id)
        
        if search:
            query = query.where(
                (Course.code.ilike(f"%{search}%")) |
                (Course.title.ilike(f"%{search}%"))
            )
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_without_lecturer(self, department_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Course).where(
                Course.department_id == department_id,
                Course.lecturer_id.is_(None)
            )
        )
        return result.scalar() or 0
