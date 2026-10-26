from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User, UserRole
from app.schemas.report import ReportCreate, ReportListResponse, ReportResponse
from app.services.report_service import ReportService

router = APIRouter()


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    data: ReportCreate,
    current_user: User = Depends(require_permission("reports.generate")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    department_id = data.department_id
    if current_user.role == UserRole.DEPARTMENT:
        department_id = current_user.department_id

    job = await service.generate_report(
        data.model_dump(),
        current_user.id,
        department_id,
    )
    return job


@router.get("", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("reports.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    department_id = None
    if current_user.role == UserRole.DEPARTMENT:
        department_id = current_user.department_id

    skip = (page - 1) * page_size
    reports = await service.list_reports(department_id, skip, page_size)

    return ReportListResponse(
        data=reports,
        meta={"page": page, "page_size": page_size},
    )


@router.get("/{report_id}/download")
async def download_report(
    report_id: UUID,
    current_user: User = Depends(require_permission("reports.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    job = await service.get_report(report_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if current_user.role == UserRole.DEPARTMENT and job.department_id != current_user.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this report",
        )

    department_id = None
    if current_user.role == UserRole.DEPARTMENT:
        department_id = current_user.department_id

    csv_content = await service.get_report_csv(report_id, department_id)
    if csv_content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report data not found",
        )

    filename = f"{job.report_type.lower().replace(' ', '-')}.csv"

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
