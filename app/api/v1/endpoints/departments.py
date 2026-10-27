from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.models.user import User, UserRole
from app.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DepartmentDetailResponse,
    DepartmentListResponse
)
from app.services.department_service import DepartmentService

router = APIRouter()


def check_department_access(user: User, department_id: UUID) -> None:
    """Check if user can access the specified department"""
    if user.role == UserRole.SUPER:
        return
    if user.role in (UserRole.DEPARTMENT, UserRole.LECTURER):
        if user.department_id != department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this department"
            )
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied"
    )


@router.get("", response_model=DepartmentListResponse)
async def list_departments(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("departments.view")),
    db: AsyncSession = Depends(get_db)
):
    """List departments"""
    service = DepartmentService(db)
    skip = (page - 1) * page_size

    departments = await service.list_departments(search, skip, page_size)

    return DepartmentListResponse(
        data=departments,
        meta={"page": page, "page_size": page_size}
    )


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    data: DepartmentCreate,
    generate_temp_password: bool = Query(False),
    current_user: User = Depends(require_permission("departments.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Create a new department"""
    service = DepartmentService(db)

    try:
        department, temp_password = await service.create_department(
            data,
            current_user.id,
            generate_temp_password
        )

        # If temp password was generated, include it in response (only for demo)
        response_data = DepartmentResponse.model_validate(department)
        if temp_password:
            # In production, this would be sent via email
            response_data.model_dump()

        return response_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.get("/{department_id}", response_model=DepartmentDetailResponse)
async def get_department(
    department_id: UUID,
    current_user: User = Depends(require_permission("departments.view")),
    db: AsyncSession = Depends(get_db)
):
    """Get department details"""
    check_department_access(current_user, department_id)

    service = DepartmentService(db)
    department_data = await service.get_department(department_id)

    if not department_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    return DepartmentDetailResponse(
        id=department_data["department"].id,
        name=department_data["department"].name,
        code=department_data["department"].code,
        school=department_data["department"].school,
        email=department_data["department"].email,
        phone=department_data["department"].phone,
        tone=department_data["department"].tone,
        subject_prefixes=department_data["department"].subject_prefixes,
        created_at=department_data["department"].created_at,
        updated_at=department_data["department"].updated_at,
        programmes_count=department_data["programmes_count"],
        courses_count=department_data["courses_count"],
        lecturers_count=department_data["lecturers_count"],
        students_count=department_data["students_count"],
        admin_account=department_data["admin_account"]
    )


@router.patch("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: UUID,
    data: DepartmentUpdate,
    current_user: User = Depends(require_permission("departments.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Update department"""
    check_department_access(current_user, department_id)

    service = DepartmentService(db)

    try:
        department = await service.update_department(department_id, data)
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        return department
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: UUID,
    force: bool = Query(False),
    lecturers: str = Query("disable"),
    current_user: User = Depends(require_permission("departments.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Delete department"""
    service = DepartmentService(db)

    try:
        success = await service.delete_department(department_id, force, lecturers)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.post("/{department_id}/resend-invitation", response_model=dict)
async def resend_invitation(
    department_id: UUID,
    current_user: User = Depends(require_permission("departments.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Resend invitation to department admin"""
    service = DepartmentService(db)
    admin = await service.resend_invitation(department_id)

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department admin not found"
        )

    return {"message": "Invitation resent successfully", "email": admin.email}
