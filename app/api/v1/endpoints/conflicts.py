from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.semester import Semester
from app.models.user import User
from app.schemas.conflict import ConflictResponse
from app.services.conflict_service import ConflictService

from sqlalchemy import select

router = APIRouter()


@router.get("", response_model=ConflictResponse)
async def get_conflicts(
    semester_id: Optional[UUID] = Query(None),
    current_user: User = Depends(require_permission("conflicts.view")),
    db: AsyncSession = Depends(get_db),
):
    sid = semester_id
    if not sid:
        result = await db.execute(
            select(Semester.id).where(Semester.is_active == True)
        )
        sid = result.scalar_one_or_none()

    if not sid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active semester found",
        )

    service = ConflictService(db)
    data = await service.get_conflicts(sid)
    return ConflictResponse(**data)
