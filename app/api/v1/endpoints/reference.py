from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.semester import Semester
from app.models.settings import InstitutionSettings
from app.models.user import User

router = APIRouter()

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
LEVELS = [100, 200, 300, 400]

PERIODS = [
    {
        "index": i,
        "start": f"{7 + i:02d}:30",
        "end": f"{8 + i:02d}:20",
        "label": f"{7 + i}:30 – {8 + i}:20",
    }
    for i in range(12)
]


@router.get("")
async def get_reference_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Semester).order_by(Semester.academic_year.desc(), Semester.number.desc())
    )
    semesters = result.scalars().all()

    settings_result = await db.execute(select(InstitutionSettings).limit(1))
    settings = settings_result.scalar_one_or_none()
    current_semester_id = str(settings.active_semester_id) if settings and settings.active_semester_id else None

    return {
        "data": {
            "weekdays": WEEKDAYS,
            "periods": PERIODS,
            "levels": LEVELS,
            "currentSemesterId": current_semester_id,
            "semesters": [
                {
                    "id": str(s.id),
                    "academicYear": s.academic_year,
                    "number": s.number,
                    "label": s.label,
                    "startDate": s.start_date.isoformat() if s.start_date else None,
                    "endDate": s.end_date.isoformat() if s.end_date else None,
                    "registrationDeadline": s.registration_deadline.isoformat() if s.registration_deadline else None,
                    "graduationDeadline": s.graduation_deadline.isoformat() if s.graduation_deadline else None,
                    "isActive": s.is_active,
                }
                for s in semesters
            ],
        }
    }
