import uuid
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: uuid.UUID) -> Optional[ModelType]:
        """Get a record by ID"""
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Get all records with pagination (async-safe)"""
        query = select(self.model)

        # ✅ Preload relationships to avoid MissingGreenlet
        if hasattr(self.model, "permissions"):
            query = query.options(selectinload(self.model.permissions))
        if hasattr(self.model, "created_by"):
            query = query.options(selectinload(self.model.created_by))

        # ✅ Apply filters safely
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)

        query = query.offset(skip).limit(limit)

        # ✅ Execute safely in async context
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, data: Dict[str, Any]) -> ModelType:
        """Create a new record"""
        instance = self.model(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def update(self, id: uuid.UUID, data: Dict[str, Any]) -> Optional[ModelType]:
        """Update a record"""
        instance = await self.get_by_id(id)
        if not instance:
            return None

        for key, value in data.items():
            if hasattr(instance, key) and value is not None:
                setattr(instance, key, value)

        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, id: uuid.UUID) -> bool:
        """Delete a record"""
        instance = await self.get_by_id(id)
        if not instance:
            return False

        await self.db.delete(instance)
        await self.db.flush()
        return True

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records"""
        query = select(func.count(self.model.id))

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)

        result = await self.db.execute(query)
        return result.scalar()
