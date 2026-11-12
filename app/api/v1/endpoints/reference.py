from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.programme import Programme
from app.models.semester import Semester
from app.models.settings import InstitutionSettings
from app.models.user import User

router = APIRouter()

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

PERIODS = [
    {
        "index": i,
        "start": f"{7 + i:02d}:30",
        "end": f"{8 + i:02d}:20",
        "label": f"{7 + i}:30 – {8 + i}:20",
    }
    for i in range(12)
]

_PG_WEEKDAY_SLOTS = [
    {"index": 0, "start": "17:30", "end": "19:30", "label": "17:30 – 19:30"},
    {"index": 1, "start": "19:30", "end": "21:30", "label": "19:30 – 21:30"},
]
_PG_WEEKEND_SLOTS = [
    {"index": 0, "start": "07:30", "end": "09:30", "label": "07:30 – 09:30"},
    {"index": 1, "start": "09:30", "end": "11:30", "label": "09:30 – 11:30"},
    {"index": 2, "start": "11:30", "end": "13:30", "label": "11:30 – 13:30"},
    {"index": 3, "start": "14:00", "end": "16:00", "label": "14:00 – 16:00"},
    {"index": 4, "start": "16:00", "end": "18:00", "label": "16:00 – 18:00"},
    {"index": 5, "start": "18:00", "end": "20:00", "label": "18:00 – 20:00"},
]
PG_PERIODS = {
    "weekday": _PG_WEEKDAY_SLOTS,
    "weekend": _PG_WEEKEND_SLOTS,
}


@router.get("")
async def get_reference_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Semester).order_by(Semester.academic_year.desc(), Semester.number.desc())
    )
    semesters = result.scalars().all()

    levels_result = await db.execute(
        select(func.unnest(Programme.levels)).distinct()
    )
    levels = sorted(row[0] for row in levels_result.all() if row[0] is not None)

    settings_result = await db.execute(select(InstitutionSettings).limit(1))
    settings = settings_result.scalar_one_or_none()
    current_semester_id = str(settings.active_semester_id) if settings and settings.active_semester_id else None

    return {
        "data": {
            "weekdays": WEEKDAYS,
            "days": ALL_DAYS,
            "periods": PERIODS,
            "pgPeriods": PG_PERIODS,
            "levels": levels,
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
