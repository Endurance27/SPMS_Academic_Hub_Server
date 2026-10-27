from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.audit import AuditLogListResponse, AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    category: Optional[str] = Query(None),
    actor_id: Optional[UUID] = Query(None),
    entity_type: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("audit.view")),
    db: AsyncSession = Depends(get_db),
):
    service = AuditService(db)
    skip = (page - 1) * page_size

    logs, total = await service.list_logs(
        category=category,
        actor_id=actor_id,
        entity_type=entity_type,
        from_date=from_date,
        to_date=to_date,
        search=search,
        skip=skip,
        limit=page_size,
    )
    counts = await service.get_category_counts()

    return AuditLogListResponse(
        data=[AuditLogResponse.model_validate(log) for log in logs],
        meta={
            "page": page,
            "pageSize": page_size,
            "total": total,
            "counts": counts,
        },
    )


@router.get("/export")
async def export_audit_logs(
    category: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_permission("audit.view")),
    db: AsyncSession = Depends(get_db),
):
    service = AuditService(db)
    csv_content = await service.export_csv(
        category=category,
        from_date=from_date,
        to_date=to_date,
    )

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit-trail.csv"},
    )
