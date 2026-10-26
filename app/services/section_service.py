import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supporting import Section
from app.schemas.section import SectionCreate, SectionUpdate


class SectionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_sections(
        self,
        programme_id: Optional[uuid.UUID] = None,
        level: Optional[int] = None,
        course_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 25,
    ) -> List[Section]:
        query = select(Section)

        if programme_id:
            query = query.where(Section.programme_id == programme_id)
        if level:
            query = query.where(Section.level == level)
        if course_id:
            query = query.where(Section.course_id == course_id)

        query = query.offset(skip).limit(limit).order_by(Section.name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_section(self, section_id: uuid.UUID) -> Optional[Section]:
        result = await self.db.execute(
            select(Section).where(Section.id == section_id)
        )
        return result.scalar_one_or_none()

    async def create_section(self, data: SectionCreate) -> Section:
        section = Section(
            programme_id=data.programme_id,
            level=data.level,
            name=data.name,
            course_id=data.course_id,
            student_ids=data.student_ids or [],
        )
        self.db.add(section)
        await self.db.commit()
        await self.db.refresh(section)
        return section

    async def update_section(
        self, section_id: uuid.UUID, data: SectionUpdate
    ) -> Optional[Section]:
        section = await self.get_section(section_id)
        if not section:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(section, field, value)

        await self.db.commit()
        await self.db.refresh(section)
        return section

    async def delete_section(self, section_id: uuid.UUID) -> bool:
        section = await self.get_section(section_id)
        if not section:
            return False

        await self.db.delete(section)
        await self.db.commit()
        return True
