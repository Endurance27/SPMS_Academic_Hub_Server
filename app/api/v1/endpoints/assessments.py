import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentUpdate,
    AssessmentResponse,
    AssessmentListResponse
)
from app.services.assessment_service import AssessmentService

router = APIRouter()


@router.get("", response_model=AssessmentListResponse)
async def list_assessments(
    status: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    course_id: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("assessments.view")),
    db: AsyncSession = Depends(get_db)
):
    """List assessments"""
    service = AssessmentService(db)
    assessments, meta = await service.list_assessments(
        status=status,
        scope=scope,
        course_id=course_id,
        search=search,
        user=current_user
    )
    return AssessmentListResponse(data=assessments, meta=meta)


@router.post("", response_model=AssessmentResponse, status_code=201)
async def create_assessment(
    data: AssessmentCreate,
    save_as_draft: bool = Query(False),
    current_user: User = Depends(require_permission("assessments.submit")),
    db: AsyncSession = Depends(get_db)
):
    """Create assessment"""
    service = AssessmentService(db)
    return await service.create_assessment(data, save_as_draft, current_user)


@router.get("/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: uuid.UUID,
    current_user: User = Depends(require_permission("assessments.view")),
    db: AsyncSession = Depends(get_db)
):
    """Get assessment by ID"""
    service = AssessmentService(db)
    assessment = await service.get_assessment(assessment_id, current_user)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


@router.patch("/{assessment_id}", response_model=AssessmentResponse)
async def update_assessment(
    assessment_id: uuid.UUID,
    data: AssessmentUpdate,
    current_user: User = Depends(require_permission("assessments.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Update assessment"""
    service = AssessmentService(db)
    return await service.update_assessment(assessment_id, data, current_user)


@router.post("/{assessment_id}/submit", response_model=AssessmentResponse)
async def submit_assessment(
    assessment_id: uuid.UUID,
    current_user: User = Depends(require_permission("assessments.submit")),
    db: AsyncSession = Depends(get_db)
):
    """Submit assessment for review"""
    service = AssessmentService(db)
    return await service.submit_assessment(assessment_id, current_user)


@router.post("/{assessment_id}/approve", response_model=AssessmentResponse)
async def approve_assessment(
    assessment_id: uuid.UUID,
    current_user: User = Depends(require_permission("assessments.review")),
    db: AsyncSession = Depends(get_db)
):
    """Approve assessment"""
    service = AssessmentService(db)
    return await service.approve_assessment(assessment_id, current_user)


@router.post("/{assessment_id}/return", response_model=AssessmentResponse)
async def return_assessment(
    assessment_id: uuid.UUID,
    comment: str,
    current_user: User = Depends(require_permission("assessments.review")),
    db: AsyncSession = Depends(get_db)
):
    """Return assessment with comment"""
    service = AssessmentService(db)
    return await service.return_assessment(assessment_id, comment, current_user)


@router.post("/{assessment_id}/cancel", response_model=AssessmentResponse)
async def cancel_assessment(
    assessment_id: uuid.UUID,
    current_user: User = Depends(require_permission("assessments.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Cancel assessment"""
    service = AssessmentService(db)
    return await service.cancel_assessment(assessment_id, current_user)


@router.put("/{assessment_id}/invigilators")
async def update_invigilators(
    assessment_id: uuid.UUID,
    invigilators: List[dict],
    current_user: User = Depends(require_permission("assessments.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Update assessment invigilators"""
    service = AssessmentService(db)
    return await service.update_invigilators(assessment_id, invigilators, current_user)


@router.get("/export")
async def export_assessments(
    status: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("assessments.view")),
    db: AsyncSession = Depends(get_db)
):
    """Export assessments as CSV"""
    import io
    import csv
    from fastapi.responses import StreamingResponse
    from sqlalchemy.future import select
    from app.models.assessment import Assessment

    query = select(Assessment)
    if status:
        query = query.where(Assessment.status == status)
    if current_user.department_id and scope != "central":
        query = query.where(Assessment.department_id == current_user.department_id)

    query = query.order_by(Assessment.date, Assessment.start_time)
    result = await db.execute(query)
    assessments = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Course", "Type", "Date", "Start", "End", "Location", "Status"])
    for a in assessments:
        writer.writerow([
            a.course_code or "",
            a.assessment_type or "",
            a.date.strftime("%Y-%m-%d") if a.date else "",
            a.start_time or "",
            a.end_time or "",
            a.location or a.venue_code or "",
            a.status.value if hasattr(a.status, 'value') else str(a.status),
        ])

    filename = "my-assessments.csv" if current_user.role.value == "student" else "assessments.csv"
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
