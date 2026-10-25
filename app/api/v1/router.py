from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    notifications,
    password,
    roles,
    users,
    departments,
    programmes,
    courses,
    venues,
    semesters,
    timetables,
    slot_requests,
    schedule,
    attendance,
    assessments,
)

api_router = APIRouter()

# Authentication
api_router.include_router(auth.router)
api_router.include_router(password.router)

# Roles & Permissions
api_router.include_router(roles.router)

# Notifications
api_router.include_router(notifications.router)

# Admin
api_router.include_router(admin.router)

# Users
api_router.include_router(users.router)

# Academic Structure
api_router.include_router(departments.router, prefix="/departments", tags=["Departments"])
api_router.include_router(programmes.router, prefix="/programmes", tags=["Programmes"])
api_router.include_router(courses.router, prefix="/courses", tags=["Courses"])
api_router.include_router(venues.router, prefix="/venues", tags=["Venues"])
api_router.include_router(semesters.router, prefix="/semesters", tags=["Semesters"])

# Scheduling
api_router.include_router(timetables.router, prefix="/timetables", tags=["Timetables"])
api_router.include_router(slot_requests.router, prefix="/slot-requests", tags=["Slot Requests"])
api_router.include_router(schedule.router, prefix="/schedule", tags=["Schedule"])

# Attendance
api_router.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])

# Assessments
api_router.include_router(assessments.router, prefix="/assessments", tags=["Assessments"])
