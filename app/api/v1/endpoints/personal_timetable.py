from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User, UserRole
from app.schemas.timetable_personal import PersonalMasterTimetableResponse
from app.services.personal_timetable_service import PersonalTimetableService

router = APIRouter()


@router.get("/master", response_model=PersonalMasterTimetableResponse)
async def get_personal_master_timetable(
    semester_id: Optional[UUID] = Query(None),
    course_codes: Optional[str] = Query(
        None,
        description="Comma-separated course codes to filter (e.g. DCIT101,DCIT133). "
        "If omitted, uses your registered courses.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in (UserRole.STUDENT, UserRole.SUPER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    codes: Optional[List[str]] = None
    if course_codes:
        codes = [c.strip() for c in course_codes.split(",") if c.strip()]

    category = None
    if current_user.student_category:
        category = current_user.student_category.value

    service = PersonalTimetableService(db)
    data = await service.get_student_master_timetable(
        user_id=current_user.id,
        programme_id=current_user.programme_id,
        level=current_user.level,
        student_category=category,
        semester_id=semester_id,
        course_codes=codes,
    )

    return PersonalMasterTimetableResponse(**data)


@router.get("/master/export")
async def export_personal_master_timetable(
    semester_id: Optional[UUID] = Query(None),
    course_codes: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in (UserRole.STUDENT, UserRole.SUPER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    codes: Optional[List[str]] = None
    if course_codes:
        codes = [c.strip() for c in course_codes.split(",") if c.strip()]

    category = None
    if current_user.student_category:
        category = current_user.student_category.value

    service = PersonalTimetableService(db)
    csv_content = await service.export_student_master_csv(
        user_id=current_user.id,
        programme_id=current_user.programme_id,
        level=current_user.level,
        student_category=category,
        semester_id=semester_id,
        course_codes=codes,
    )

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="my-master-timetable.csv"'},
    )
