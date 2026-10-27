from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User, UserRole
from app.schemas.graduation import (
    GraduationCandidateResponse,
    GraduationCandidateUpdate,
    GraduationListResponse,
    GraduationSubmissionDetailResponse,
    GraduationSubmissionResponse,
)
from app.services.graduation_service import GraduationService

router = APIRouter()


@router.post(
    "/submissions",
    response_model=GraduationSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_submission(
    file: UploadFile = File(...),
    student_category: str = Form(...),
    academic_year: str = Form(...),
    programme_id: Optional[UUID] = Form(None),
    programme_text: Optional[str] = Form(None),
    declared_count: int = Form(...),
    current_user: User = Depends(require_permission("graduation.submit")),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.department_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department context required.",
        )

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a CSV file.",
        )

    service = GraduationService(db)
    content = await file.read()

    from app.schemas.graduation import GraduationSubmissionCreate
    create_data = GraduationSubmissionCreate(
        student_category=student_category,
        academic_year=academic_year,
        programme_id=programme_id,
        programme_text=programme_text,
        declared_count=declared_count,
    )

    try:
        submission = await service.create_submission(
            data=create_data,
            file_content=content,
            filename=file.filename,
            department_id=current_user.department_id,
            created_by_id=current_user.id,
        )
        return GraduationSubmissionResponse.model_validate(submission)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.get("/submissions", response_model=GraduationListResponse)
async def list_submissions(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("graduation.view")),
    db: AsyncSession = Depends(get_db),
):
    service = GraduationService(db)

    dept_id = None
    if current_user.role == UserRole.DEPARTMENT:
        dept_id = current_user.department_id

    skip = (page - 1) * page_size
    submissions, counts = await service.list_submissions(
        department_id=dept_id,
        status=status_filter,
        skip=skip,
        limit=page_size,
    )

    return GraduationListResponse(
        data=[GraduationSubmissionResponse.model_validate(s) for s in submissions],
        meta={"page": page, "pageSize": page_size, "counts": counts},
    )


@router.get(
    "/submissions/{submission_id}",
    response_model=GraduationSubmissionDetailResponse,
)
async def get_submission(
    submission_id: UUID,
    current_user: User = Depends(require_permission("graduation.view")),
    db: AsyncSession = Depends(get_db),
):
    service = GraduationService(db)
    submission = await service.get_submission(submission_id)

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )

    return GraduationSubmissionDetailResponse(
        **GraduationSubmissionResponse.model_validate(submission).model_dump(),
        candidates=[
            GraduationCandidateResponse.model_validate(c)
            for c in submission.candidates
        ],
    )


@router.patch(
    "/candidates/{candidate_id}",
    response_model=GraduationCandidateResponse,
)
async def update_candidate(
    candidate_id: UUID,
    data: GraduationCandidateUpdate,
    current_user: User = Depends(require_permission("graduation.review")),
    db: AsyncSession = Depends(get_db),
):
    service = GraduationService(db)
    candidate = await service.update_candidate(candidate_id, data)

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
        )

    return GraduationCandidateResponse.model_validate(candidate)


@router.post("/submissions/{submission_id}/validate", response_model=GraduationSubmissionResponse)
async def validate_submission(
    submission_id: UUID,
    current_user: User = Depends(require_permission("graduation.review")),
    db: AsyncSession = Depends(get_db),
):
    service = GraduationService(db)

    try:
        submission = await service.validate_submission(submission_id, current_user.id)
        return GraduationSubmissionResponse.model_validate(submission)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        )


@router.post("/submissions/{submission_id}/return", response_model=GraduationSubmissionResponse)
async def return_submission(
    submission_id: UUID,
    comment: str = Form(...),
    current_user: User = Depends(require_permission("graduation.review")),
    db: AsyncSession = Depends(get_db),
):
    if not comment.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add a review comment before returning this entry.",
        )

    service = GraduationService(db)

    try:
        submission = await service.return_submission(
            submission_id, current_user.id, comment.strip()
        )
        return GraduationSubmissionResponse.model_validate(submission)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        )


@router.get("/export")
async def export_graduation(
    current_user: User = Depends(require_permission("graduation.view")),
    db: AsyncSession = Depends(get_db),
):
    service = GraduationService(db)

    dept_id = None
    if current_user.role == UserRole.DEPARTMENT:
        dept_id = current_user.department_id

    csv_content = await service.export_csv(department_id=dept_id)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="graduation-data.csv"'},
    )
