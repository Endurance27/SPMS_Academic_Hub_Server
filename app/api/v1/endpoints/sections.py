from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.section import (
    SectionCreate,
    SectionListResponse,
    SectionResponse,
    SectionUpdate,
)
from app.services.section_service import SectionService

router = APIRouter()


@router.get("", response_model=SectionListResponse)
async def list_sections(
    programme_id: Optional[UUID] = Query(None),
    level: Optional[int] = Query(None),
    course_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("students.manage")),
    db: AsyncSession = Depends(get_db),
):
    service = SectionService(db)
    skip = (page - 1) * page_size

    sections = await service.list_sections(
        programme_id=programme_id,
        level=level,
        course_id=course_id,
        skip=skip,
        limit=page_size,
    )

    return SectionListResponse(
        data=[
            SectionResponse(
                id=s.id,
                programme_id=s.programme_id,
                level=s.level,
                name=s.name,
                course_id=s.course_id,
                student_ids=s.student_ids or [],
                student_count=len(s.student_ids or []),
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sections
        ],
        meta={"page": page, "pageSize": page_size},
    )


@router.get("/{section_id}", response_model=SectionResponse)
async def get_section(
    section_id: UUID,
    current_user: User = Depends(require_permission("students.manage")),
    db: AsyncSession = Depends(get_db),
):
    service = SectionService(db)
    section = await service.get_section(section_id)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
        )

    return SectionResponse(
        id=section.id,
        programme_id=section.programme_id,
        level=section.level,
        name=section.name,
        course_id=section.course_id,
        student_ids=section.student_ids or [],
        student_count=len(section.student_ids or []),
        created_at=section.created_at,
        updated_at=section.updated_at,
    )


@router.post("", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
async def create_section(
    data: SectionCreate,
    current_user: User = Depends(require_permission("students.manage")),
    db: AsyncSession = Depends(get_db),
):
    service = SectionService(db)
    section = await service.create_section(data)

    return SectionResponse(
        id=section.id,
        programme_id=section.programme_id,
        level=section.level,
        name=section.name,
        course_id=section.course_id,
        student_ids=section.student_ids or [],
        student_count=len(section.student_ids or []),
        created_at=section.created_at,
        updated_at=section.updated_at,
    )


@router.patch("/{section_id}", response_model=SectionResponse)
async def update_section(
    section_id: UUID,
    data: SectionUpdate,
    current_user: User = Depends(require_permission("students.manage")),
    db: AsyncSession = Depends(get_db),
):
    service = SectionService(db)
    section = await service.update_section(section_id, data)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
        )

    return SectionResponse(
        id=section.id,
        programme_id=section.programme_id,
        level=section.level,
        name=section.name,
        course_id=section.course_id,
        student_ids=section.student_ids or [],
        student_count=len(section.student_ids or []),
        created_at=section.created_at,
        updated_at=section.updated_at,
    )


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    section_id: UUID,
    current_user: User = Depends(require_permission("students.manage")),
    db: AsyncSession = Depends(get_db),
):
    service = SectionService(db)
    success = await service.delete_section(section_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
        )
