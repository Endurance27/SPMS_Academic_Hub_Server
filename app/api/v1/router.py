from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    assessments,
    attendance,
    audit,
    auth,
    conflicts,
    courses,
    dashboards,
    demo,
    departments,
    faculty,
    graduation,
    imports,
    lecturer,
    notifications,
    password,
    personal_timetable,
    profile,
    programmes,
    reference,
    registrations,
    reports,
    role_templates,
    roles,
    schedule,
    sections,
    semesters,
    settings,
    slot_requests,
    staff,
    students,
    timetables,
    users,
    venues,
)

api_router = APIRouter()

# Authentication & Profile
api_router.include_router(auth.router)
api_router.include_router(password.router)
api_router.include_router(profile.router)

# Roles & Permissions
api_router.include_router(roles.router)
api_router.include_router(role_templates.router, prefix="/role-templates", tags=["Role Templates"])

# Notifications
api_router.include_router(notifications.router)

# Admin
api_router.include_router(admin.router)
api_router.include_router(demo.router, prefix="/admin/demo", tags=["Demo"])

# Users
api_router.include_router(users.router)

# Reference Data
api_router.include_router(reference.router, prefix="/reference", tags=["Reference"])

# Settings
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])

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
api_router.include_router(personal_timetable.router, prefix="/me/timetable", tags=["Personal Timetable"])
api_router.include_router(conflicts.router, prefix="/conflicts", tags=["Conflict Centre"])

# People
api_router.include_router(faculty.router, prefix="/faculty", tags=["Faculty"])
api_router.include_router(staff.router, prefix="/staff", tags=["Staff"])
api_router.include_router(students.router, prefix="/students", tags=["Students"])
api_router.include_router(sections.router, prefix="/sections", tags=["Sections"])

# Lecturer
api_router.include_router(lecturer.router, tags=["Lecturer"])

# Course Registration & Imports
api_router.include_router(registrations.router, tags=["Registration"])
api_router.include_router(imports.router, prefix="/imports", tags=["Imports"])

# Attendance
api_router.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])

# Assessments
api_router.include_router(assessments.router, prefix="/assessments", tags=["Assessments"])

# Graduation
api_router.include_router(graduation.router, prefix="/graduation", tags=["Graduation"])

# Analytics & Reporting
api_router.include_router(dashboards.router, tags=["Dashboards"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])
