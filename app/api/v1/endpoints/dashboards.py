from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.models.user import User, UserRole
from app.schemas.dashboard import (
    BadgesResponse,
    DepartmentDashboardResponse,
    LecturerDashboardResponse,
    StudentDashboardResponse,
    SuperDashboardResponse,
)
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/dashboard/super", response_model=SuperDashboardResponse)
async def get_super_dashboard(
    current_user: User = Depends(require_permission("reports.view")),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    data = await service.get_super_dashboard()
    return SuperDashboardResponse(**data)


@router.get("/dashboard/department", response_model=DepartmentDashboardResponse)
async def get_department_dashboard(
    current_user: User = Depends(require_permission("reports.view")),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No department associated with this account",
        )
    service = DashboardService(db)
    data = await service.get_department_dashboard(current_user.department_id)
    return DepartmentDashboardResponse(**data)


@router.get("/dashboard/lecturer", response_model=LecturerDashboardResponse)
async def get_lecturer_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in (UserRole.LECTURER, UserRole.SUPER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    service = DashboardService(db)
    data = await service.get_lecturer_dashboard(current_user.id)
    return LecturerDashboardResponse(**data)


@router.get("/dashboard/student", response_model=StudentDashboardResponse)
async def get_student_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in (UserRole.STUDENT, UserRole.SUPER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    service = DashboardService(db)
    data = await service.get_student_dashboard(
        current_user.id,
        current_user.programme_id,
        current_user.level,
    )
    return StudentDashboardResponse(**data)


@router.get("/badges", response_model=BadgesResponse)
async def get_badges(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    data = await service.get_badges(current_user)
    return BadgesResponse(**data)
