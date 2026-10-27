from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User, UserRole
from app.schemas.timetable_personal import PersonalTimetableResponse
from app.services.personal_timetable_service import PersonalTimetableService

router = APIRouter()


@router.get("", response_model=PersonalTimetableResponse)
async def get_personal_timetable(
    semester_id: Optional[UUID] = Query(None),
    week_of: Optional[str] = Query(None),
    include: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in (UserRole.LECTURER, UserRole.STUDENT, UserRole.SUPER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    service = PersonalTimetableService(db)

    if current_user.role == UserRole.LECTURER or (
        current_user.role == UserRole.SUPER and include == "lecturer"
    ):
        include_department = include == "department"
        data = await service.get_lecturer_timetable(
            current_user.id,
            current_user.department_id,
            semester_id,
            include_department,
        )
    else:
        data = await service.get_student_timetable(
            current_user.id,
            current_user.programme_id,
            current_user.level,
            semester_id,
        )

    return PersonalTimetableResponse(**data)


@router.get("/export")
async def export_personal_timetable(
    semester_id: Optional[UUID] = Query(None),
    format: str = Query("csv"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in (UserRole.LECTURER, UserRole.STUDENT, UserRole.SUPER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    service = PersonalTimetableService(db)
    csv_content = await service.export_timetable_csv(current_user, semester_id)

    role_label = current_user.role.value if current_user.role else "user"
    filename = f"my-timetable-{role_label}.csv"

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
