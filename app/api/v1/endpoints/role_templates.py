from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.role import RoleTemplate
from app.models.user import User
from app.schemas.role_template import (
    RoleTemplateCreate,
    RoleTemplateListResponse,
    RoleTemplateResponse,
    RoleTemplateUpdate,
)

router = APIRouter()


@router.get("", response_model=RoleTemplateListResponse)
async def list_role_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    """List all role templates"""
    skip = (page - 1) * page_size
    result = await db.execute(select(RoleTemplate).offset(skip).limit(page_size))
    templates = list(result.scalars().all())
    return RoleTemplateListResponse(
        data=[RoleTemplateResponse.model_validate(t) for t in templates],
        meta={"page": page, "page_size": page_size},
    )


@router.post("", response_model=RoleTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_role_template(
    data: RoleTemplateCreate,
    current_user: User = Depends(require_permission("roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Create a role template"""
    existing = await db.execute(select(RoleTemplate).where(RoleTemplate.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A role template with this name already exists.",
        )

    template = RoleTemplate(
        name=data.name,
        role=data.role,
        permissions=data.permissions,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return RoleTemplateResponse.model_validate(template)


@router.get("/{template_id}", response_model=RoleTemplateResponse)
async def get_role_template(
    template_id: UUID,
    current_user: User = Depends(require_permission("roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Get a role template by ID"""
    result = await db.execute(select(RoleTemplate).where(RoleTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role template not found")
    return RoleTemplateResponse.model_validate(template)


@router.patch("/{template_id}", response_model=RoleTemplateResponse)
async def update_role_template(
    template_id: UUID,
    data: RoleTemplateUpdate,
    current_user: User = Depends(require_permission("roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Update a role template"""
    result = await db.execute(select(RoleTemplate).where(RoleTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role template not found")

    if data.name is not None:
        dup = await db.execute(
            select(RoleTemplate).where(RoleTemplate.name == data.name, RoleTemplate.id != template_id)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A role template with this name already exists.",
            )
        template.name = data.name

    if data.permissions is not None:
        template.permissions = data.permissions

    await db.commit()
    await db.refresh(template)
    return RoleTemplateResponse.model_validate(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role_template(
    template_id: UUID,
    current_user: User = Depends(require_permission("roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a role template"""
    result = await db.execute(select(RoleTemplate).where(RoleTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role template not found")

    await db.delete(template)
    await db.commit()
