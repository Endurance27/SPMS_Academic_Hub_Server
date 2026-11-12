"""
Comprehensive permission definitions for SPMS Academic Hub
Based on backend.md section 5.17 and role capabilities
"""

from enum import Enum


class Permission(str, Enum):
    """All system permissions organized by module"""

    # Scheduling & Timetable
    SCHEDULE_MANAGE = "schedule.manage"
    SCHEDULE_APPROVE = "schedule.approve"
    SCHEDULE_REQUEST = "schedule.request"
    SCHEDULE_WITHDRAW = "schedule.withdraw"
    SCHEDULE_VIEW = "schedule.view"
    TIMETABLE_UPLOAD = "timetable.upload"
    TIMETABLE_VIEW = "timetable.view"
    TIMETABLE_EDIT = "timetable.edit"
    TIMETABLE_DEPARTMENT_UPLOAD = "timetable.department_upload"  # Department-specific uploads

    # Academic Structure
    DEPARTMENTS_MANAGE = "departments.manage"
    DEPARTMENTS_VIEW = "departments.view"
    PROGRAMMES_MANAGE = "programmes.manage"
    PROGRAMMES_VIEW = "programmes.view"
    COURSES_MANAGE = "courses.manage"
    COURSES_VIEW = "courses.view"

    # People & Access
    STAFF_MANAGE = "staff.manage"
    STAFF_VIEW = "staff.view"
    STUDENTS_MANAGE = "students.manage"
    STUDENTS_VIEW = "students.view"
    USERS_MANAGE = "users.manage"
    ROLES_MANAGE = "roles.manage"

    # Venues
    VENUES_MANAGE = "venues.manage"
    VENUES_VIEW = "venues.view"

    # Assessments
    ASSESSMENTS_MANAGE = "assessments.manage"
    ASSESSMENTS_REVIEW = "assessments.review"
    ASSESSMENTS_VIEW = "assessments.view"
    ASSESSMENTS_SUBMIT = "assessments.submit"

    # Attendance
    ATTENDANCE_MANAGE = "attendance.manage"
    ATTENDANCE_RECORD = "attendance.record"
    ATTENDANCE_VIEW = "attendance.view"

    # Graduation
    GRADUATION_SUBMIT = "graduation.submit"
    GRADUATION_REVIEW = "graduation.review"
    GRADUATION_VIEW = "graduation.view"

    # Course Registration
    REGISTRATION_MANAGE = "registration.manage"
    REGISTRATION_VIEW = "registration.view"
    REGISTRATION_SELF = "registration.self"

    # Imports
    IMPORTS_MANAGE = "imports.manage"
    IMPORTS_VIEW = "imports.view"

    # Reports
    REPORTS_VIEW = "reports.view"
    REPORTS_GENERATE = "reports.generate"

    # Audit
    AUDIT_VIEW = "audit.view"

    # Settings
    SETTINGS_MANAGE = "settings.manage"
    SETTINGS_INSTITUTION = "settings.institution"
    SETTINGS_DEPARTMENT = "settings.department"

    # Notifications
    NOTIFICATIONS_MANAGE = "notifications.manage"
    NOTIFICATIONS_VIEW = "notifications.view"

    # Conflict Centre
    CONFLICTS_VIEW = "conflicts.view"
    CONFLICTS_OVERRIDE = "conflicts.override"


# Permission modules for organization
PERMISSION_MODULES = {
    "scheduling": [
        Permission.SCHEDULE_MANAGE,
        Permission.SCHEDULE_APPROVE,
        Permission.SCHEDULE_REQUEST,
        Permission.SCHEDULE_WITHDRAW,
        Permission.SCHEDULE_VIEW,
        Permission.TIMETABLE_UPLOAD,
        Permission.TIMETABLE_VIEW,
        Permission.TIMETABLE_EDIT,
        Permission.TIMETABLE_DEPARTMENT_UPLOAD,
    ],
    "academics": [
        Permission.DEPARTMENTS_MANAGE,
        Permission.DEPARTMENTS_VIEW,
        Permission.PROGRAMMES_MANAGE,
        Permission.PROGRAMMES_VIEW,
        Permission.COURSES_MANAGE,
        Permission.COURSES_VIEW,
    ],
    "people": [
        Permission.STAFF_MANAGE,
        Permission.STAFF_VIEW,
        Permission.STUDENTS_MANAGE,
        Permission.STUDENTS_VIEW,
        Permission.USERS_MANAGE,
        Permission.ROLES_MANAGE,
    ],
    "venues": [
        Permission.VENUES_MANAGE,
        Permission.VENUES_VIEW,
    ],
    "assessments": [
        Permission.ASSESSMENTS_MANAGE,
        Permission.ASSESSMENTS_REVIEW,
        Permission.ASSESSMENTS_VIEW,
        Permission.ASSESSMENTS_SUBMIT,
    ],
    "attendance": [
        Permission.ATTENDANCE_MANAGE,
        Permission.ATTENDANCE_RECORD,
        Permission.ATTENDANCE_VIEW,
    ],
    "graduation": [
        Permission.GRADUATION_SUBMIT,
        Permission.GRADUATION_REVIEW,
        Permission.GRADUATION_VIEW,
    ],
    "registration": [
        Permission.REGISTRATION_MANAGE,
        Permission.REGISTRATION_VIEW,
        Permission.REGISTRATION_SELF,
    ],
    "imports": [
        Permission.IMPORTS_MANAGE,
        Permission.IMPORTS_VIEW,
    ],
    "reports": [
        Permission.REPORTS_VIEW,
        Permission.REPORTS_GENERATE,
    ],
    "audit": [
        Permission.AUDIT_VIEW,
    ],
    "settings": [
        Permission.SETTINGS_MANAGE,
        Permission.SETTINGS_INSTITUTION,
        Permission.SETTINGS_DEPARTMENT,
    ],
    "notifications": [
        Permission.NOTIFICATIONS_MANAGE,
        Permission.NOTIFICATIONS_VIEW,
    ],
    "conflicts": [
        Permission.CONFLICTS_VIEW,
        Permission.CONFLICTS_OVERRIDE,
    ],
}


# Role permission mappings based on backend.md section 2
ROLE_PERMISSIONS = {
    "super": [
        # Super admin has all permissions
        *[p.value for p in Permission],
    ],
    "department": [
        # Department admin permissions - full control over department's academic structure
        Permission.SCHEDULE_MANAGE.value,
        Permission.SCHEDULE_REQUEST.value,
        Permission.SCHEDULE_WITHDRAW.value,
        Permission.SCHEDULE_VIEW.value,
        Permission.TIMETABLE_UPLOAD.value,  # Upload department timetables
        Permission.TIMETABLE_VIEW.value,
        Permission.TIMETABLE_EDIT.value,    # Edit department timetable entries
        Permission.TIMETABLE_DEPARTMENT_UPLOAD.value,  # Department-specific uploads
        Permission.DEPARTMENTS_VIEW.value,  # View own department
        Permission.PROGRAMMES_MANAGE.value,
        Permission.PROGRAMMES_VIEW.value,
        Permission.COURSES_MANAGE.value,
        Permission.COURSES_VIEW.value,
        Permission.STAFF_MANAGE.value,      # Manage faculty
        Permission.STAFF_VIEW.value,
        Permission.STUDENTS_MANAGE.value,   # Import and manage students
        Permission.STUDENTS_VIEW.value,
        Permission.VENUES_VIEW.value,
        Permission.ASSESSMENTS_MANAGE.value,
        Permission.ASSESSMENTS_REVIEW.value,  # Review lecturer submissions
        Permission.ASSESSMENTS_VIEW.value,
        Permission.ASSESSMENTS_SUBMIT.value,
        Permission.ATTENDANCE_MANAGE.value,
        Permission.ATTENDANCE_VIEW.value,
        Permission.GRADUATION_SUBMIT.value,
        Permission.GRADUATION_VIEW.value,
        Permission.IMPORTS_MANAGE.value,    # CSV imports
        Permission.IMPORTS_VIEW.value,
        Permission.REPORTS_VIEW.value,
        Permission.SETTINGS_DEPARTMENT.value,
        Permission.NOTIFICATIONS_VIEW.value,
    ],
    "lecturer": [
        # Lecturer permissions - focused on their courses and students
        Permission.SCHEDULE_REQUEST.value,  # Can request slots for their courses
        Permission.TIMETABLE_VIEW.value,
        Permission.COURSES_VIEW.value,
        Permission.COURSES_MANAGE.value,    # Edit their own course details
        Permission.STAFF_VIEW.value,
        Permission.STUDENTS_VIEW.value,
        Permission.VENUES_VIEW.value,
        Permission.ASSESSMENTS_SUBMIT.value,
        Permission.ASSESSMENTS_VIEW.value,
        Permission.ATTENDANCE_RECORD.value,
        Permission.ATTENDANCE_VIEW.value,
        Permission.IMPORTS_MANAGE.value,    # For course roster imports
        Permission.IMPORTS_VIEW.value,
        Permission.REGISTRATION_VIEW.value,
        Permission.NOTIFICATIONS_VIEW.value,
    ],
    "student": [
        # Student permissions
        Permission.TIMETABLE_VIEW.value,
        Permission.COURSES_VIEW.value,
        Permission.ASSESSMENTS_VIEW.value,
        Permission.ATTENDANCE_VIEW.value,
        Permission.REGISTRATION_SELF.value,
        Permission.NOTIFICATIONS_VIEW.value,
    ],
}


def get_permissions_for_role(role: str) -> list[str]:
    """Get permission codes for a given role"""
    return ROLE_PERMISSIONS.get(role, [])


def get_all_permissions() -> list[str]:
    """Get all permission codes"""
    return [p.value for p in Permission]
