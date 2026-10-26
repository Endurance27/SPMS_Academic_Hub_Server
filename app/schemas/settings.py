import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InstitutionSettingsResponse(BaseModel):
    id: uuid.UUID
    organisation_name: str
    support_email: str
    office_location: Optional[str] = None
    timezone: str = "Africa/Accra"
    active_semester_id: Optional[uuid.UUID] = None
    teaching_start: str = "08:00"
    teaching_end: str = "18:00"
    default_class_duration: int = 60
    capacity_tolerance: int = 0
    allow_weekends: bool = False
    require_conflict_approval: bool = False
    auto_publish_approved: bool = False
    require_graduation_approval: bool = False
    require_academic_clearance: bool = False
    require_financial_clearance: bool = False
    notify_schedule_changes: bool = True
    notify_graduation_submissions: bool = True
    notify_conflicts: bool = True
    email_channel: bool = True
    in_app_channel: bool = True
    require_admin_two_factor: bool = False
    session_timeout: int = 30
    audit_retention: str = "1 year"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InstitutionSettingsUpdate(BaseModel):
    organisation_name: Optional[str] = Field(None, min_length=1, max_length=255)
    support_email: Optional[str] = Field(None, min_length=1, max_length=255)
    office_location: Optional[str] = None
    timezone: Optional[str] = None
    active_semester_id: Optional[uuid.UUID] = None
    teaching_start: Optional[str] = None
    teaching_end: Optional[str] = None
    default_class_duration: Optional[int] = None
    capacity_tolerance: Optional[int] = None
    allow_weekends: Optional[bool] = None
    require_conflict_approval: Optional[bool] = None
    auto_publish_approved: Optional[bool] = None
    require_graduation_approval: Optional[bool] = None
    require_academic_clearance: Optional[bool] = None
    require_financial_clearance: Optional[bool] = None
    notify_schedule_changes: Optional[bool] = None
    notify_graduation_submissions: Optional[bool] = None
    notify_conflicts: Optional[bool] = None
    email_channel: Optional[bool] = None
    in_app_channel: Optional[bool] = None
    require_admin_two_factor: Optional[bool] = None
    session_timeout: Optional[int] = None
    audit_retention: Optional[str] = None


class DepartmentSettingsResponse(BaseModel):
    id: uuid.UUID
    department_id: uuid.UUID
    department_name: str
    department_code: str
    support_email: Optional[str] = None
    office_location: Optional[str] = None
    timezone: Optional[str] = None
    teaching_start: Optional[str] = None
    teaching_end: Optional[str] = None
    default_class_duration: Optional[int] = None
    capacity_tolerance: Optional[int] = None
    allow_weekends: Optional[bool] = None
    require_conflict_approval: Optional[bool] = None
    auto_publish_approved: Optional[bool] = None
    notify_schedule_changes: Optional[bool] = None
    notify_graduation_submissions: Optional[bool] = None
    notify_conflicts: Optional[bool] = None
    email_channel: Optional[bool] = None
    in_app_channel: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DepartmentSettingsUpdate(BaseModel):
    support_email: Optional[str] = None
    office_location: Optional[str] = None
    timezone: Optional[str] = None
    teaching_start: Optional[str] = None
    teaching_end: Optional[str] = None
    default_class_duration: Optional[int] = None
    capacity_tolerance: Optional[int] = None
    allow_weekends: Optional[bool] = None
    require_conflict_approval: Optional[bool] = None
    auto_publish_approved: Optional[bool] = None
    notify_schedule_changes: Optional[bool] = None
    notify_graduation_submissions: Optional[bool] = None
    notify_conflicts: Optional[bool] = None
    email_channel: Optional[bool] = None
    in_app_channel: Optional[bool] = None
