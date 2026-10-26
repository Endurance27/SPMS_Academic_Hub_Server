from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.registration import (
    CatalogueListResponse,
    CatalogueCourseResponse,
    RegistrationCreate,
    RegistrationListResponse,
    RegistrationResponse,
)
from app.services.registration_service import RegistrationService

router = APIRouter()


@router.get("/me/registrations", response_model=RegistrationListResponse)
async def list_my_registrations(
    semester_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permission("registration.self")),
    db: AsyncSession = Depends(get_db),
):
    service = RegistrationService(db)
    skip = (page - 1) * page_size

    registrations, extra = await service.list_registrations(
        student_id=current_user.id,
        semester_id=semester_id,
        skip=skip,
        limit=page_size,
    )

    return RegistrationListResponse(
        data=[RegistrationResponse(**r) for r in registrations],
        meta={
            "page": page,
            "pageSize": page_size,
            "counts": extra["counts"],
            "totalCredits": extra["totalCredits"],
        },
    )


@router.get("/registration/catalogue", response_model=CatalogueListResponse)
async def get_catalogue(
    semester_id: UUID = Query(...),
    current_user: User = Depends(require_permission("registration.self")),
    db: AsyncSession = Depends(get_db),
):
    service = RegistrationService(db)
    courses = await service.get_catalogue(current_user, semester_id)

    return CatalogueListResponse(
        data=[CatalogueCourseResponse(**c) for c in courses],
    )


@router.post(
    "/me/registrations",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_registration(
    data: RegistrationCreate,
    current_user: User = Depends(require_permission("registration.self")),
    db: AsyncSession = Depends(get_db),
):
    service = RegistrationService(db)

    try:
        reg = await service.create_registration(current_user, data)
        return RegistrationResponse(
            id=reg.id,
            student_id=reg.student_id,
            course_id=reg.course_id,
            custom_course_code=reg.custom_course_code,
            custom_course_title=reg.custom_course_title,
            semester_id=reg.semester_id,
            level=reg.level,
            registration_type=reg.registration_type,
            credits=reg.credits,
            status=reg.status,
            source=reg.source,
            created_at=reg.created_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        )


@router.delete(
    "/me/registrations/{registration_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def drop_registration(
    registration_id: UUID,
    current_user: User = Depends(require_permission("registration.self")),
    db: AsyncSession = Depends(get_db),
):
    service = RegistrationService(db)

    try:
        success = await service.drop_registration(registration_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registration not found",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        )
