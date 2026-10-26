import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import DepartmentSettings, InstitutionSettings
from app.schemas.settings import (
    DepartmentSettingsUpdate,
    InstitutionSettingsUpdate,
)


class SettingsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_institution_settings(self) -> InstitutionSettings:
        result = await self.db.execute(select(InstitutionSettings).limit(1))
        settings = result.scalar_one_or_none()
        if not settings:
            settings = InstitutionSettings(
                organisation_name="SPMS, University of Ghana",
                support_email="admin@ug.edu.gh",
            )
            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)
        return settings

    async def update_institution_settings(
        self, data: InstitutionSettingsUpdate
    ) -> InstitutionSettings:
        settings = await self.get_institution_settings()
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)
        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    async def get_department_settings(
        self, department_id: uuid.UUID
    ) -> Optional[DepartmentSettings]:
        result = await self.db.execute(
            select(DepartmentSettings).where(
                DepartmentSettings.department_id == department_id
            )
        )
        return result.scalar_one_or_none()

    async def update_department_settings(
        self, department_id: uuid.UUID, data: DepartmentSettingsUpdate
    ) -> Optional[DepartmentSettings]:
        settings = await self.get_department_settings(department_id)
        if not settings:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)
        await self.db.commit()
        await self.db.refresh(settings)
        return settings
