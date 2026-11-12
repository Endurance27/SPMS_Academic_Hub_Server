from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User

router = APIRouter()

TABLES_TO_TRUNCATE = [
    "notification_reads",
    "notifications",
    "attendance_records",
    "attendance_sessions",
    "graduation_candidates",
    "graduation_submissions",
    "student_import_rows",
    "student_imports",
    "course_registrations",
    "assessment_invigilators",
    "assessments",
    "schedule_items",
    "slot_requests",
    "master_entries",
    "master_timetables",
    "timetable_uploads",
    "course_cohorts",
    "courses",
    "programmes",
    "department_settings",
    "sessions",
    "invitations",
    "password_resets",
    "notification_preferences",
    "audit_logs",
    "user_roles",
    "users",
    "departments",
    "semesters",
    "venues",
    "role_permissions",
    "roles",
    "role_templates",
    "institution_settings",
]


@router.post("/reset")
async def reset_demo(
    current_user: User = Depends(require_permission("settings.manage")),
    db: AsyncSession = Depends(get_db),
):
    if not getattr(settings, "DEMO_MODE", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo reset is only available in demo mode",
        )

    for table in TABLES_TO_TRUNCATE:
        await db.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
    await db.commit()

    return {"data": {"message": "Demo workspace has been reset successfully"}}
