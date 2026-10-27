# SPMS Academic Hub Server -- API Endpoints Reference

> **Version:** 1.0  
> **Generated:** 2026-10-26  
> **Base URL:** `/api/{version}` (currently `/api/v1.0.0`, configured via `API_VERSION` env var)

---

## Architectural Overview

| Concern | Detail |
|---------|--------|
| **Base URL** | All routes are served under `/api/v1.0.0` (configurable via `API_VERSION` env var). |
| **Authentication** | Bearer token (JWT) in the `Authorization` header. Obtain tokens via `/api/v1/auth/login`. |
| **Authorization** | Role-Based Access Control (RBAC). Each endpoint declares a required permission via `require_permission("...")`. Super admins implicitly hold every permission. |
| **Pagination** | Standard list responses accept `page` (1-based) and `page_size` query parameters. Responses include a `meta` object with pagination info. Some admin endpoints use `skip`/`limit` or `per_page`/`page`. |
| **Entity IDs** | All entity IDs are UUIDs (v4). |
| **Dates** | ISO 8601 format (`YYYY-MM-DDTHH:MM:SS`). |
| **Error format** | `{"detail": "..."}` with appropriate HTTP status code. |
| **User Roles** | `super`, `department`, `lecturer`, `student` |

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Password Management](#2-password-management)
3. [Profile](#3-profile)
4. [Users](#4-users)
5. [Admin](#5-admin)
6. [Roles & Permissions](#6-roles--permissions)
7. [Role Templates](#7-role-templates)
8. [Departments](#8-departments)
9. [Programmes](#9-programmes)
10. [Courses](#10-courses)
11. [Venues](#11-venues)
12. [Semesters](#12-semesters)
13. [Timetables (Master)](#13-timetables-master)
14. [Slot Requests](#14-slot-requests)
15. [Schedule](#15-schedule)
16. [Personal Timetable](#16-personal-timetable)
17. [Conflicts](#17-conflicts)
18. [Faculty](#18-faculty)
19. [Staff](#19-staff)
20. [Students](#20-students)
21. [Sections](#21-sections)
22. [Lecturer](#22-lecturer)
23. [Registration](#23-registration)
24. [Imports](#24-imports)
25. [Attendance](#25-attendance)
26. [Assessments](#26-assessments)
27. [Graduation](#27-graduation)
28. [Dashboards](#28-dashboards)
29. [Reports](#29-reports)
30. [Audit](#30-audit)
31. [Notifications](#31-notifications)
32. [Settings](#32-settings)
33. [Reference Data](#33-reference-data)
34. [Demo](#34-demo)

---

## 1. Authentication

Prefix: `/api/v1/auth`

### POST `/api/v1/auth/login`

Login endpoint. Returns access and refresh tokens.

- **Permission:** Public (no auth required)
- **Request Body** (`LoginRequest`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `email` | EmailStr | Yes | |
| `password` | string | Yes | |

- **Response** (`LoginResponse`):

| Field | Type | Notes |
|-------|------|-------|
| `access_token` | string | JWT access token |
| `refresh_token` | string | JWT refresh token |
| `token_type` | string | Always `"bearer"` |
| `requires_2fa` | boolean | `true` if 2FA verification needed |
| `is_first_time` | boolean | `true` on first login |

---

### POST `/api/v1/auth/register`

Student self-registration. Creates a new student account.

- **Permission:** Public (no auth required)
- **Request Body** (`RegisterRequest`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `email` | EmailStr | Yes | |
| `password` | string | Yes | min_length=6 |
| `name` | string | Yes | min_length=1, max_length=255 |
| `student_number` | string | Yes | min_length=1, max_length=50 |
| `programme_id` | UUID | Yes | |
| `level` | int | Yes | 100-900 |

- **Response** (`LoginResponse`): Same as login response.
- **Status:** 201 Created

---

### POST `/api/v1/auth/refresh`

Rotate refresh token and issue new access token.

- **Permission:** Public (no auth required)
- **Request Body** (`RefreshTokenRequest`):

| Field | Type | Required |
|-------|------|----------|
| `refresh_token` | string | Yes |

- **Response** (`LoginResponse`): Same as login response.

---

### GET `/api/v1/auth/me`

Get current user profile with permissions and related data.

- **Permission:** Authenticated user
- **Response** (`UserMeResponse`):

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `email` | string | |
| `name` | string | |
| `role` | string | `super`, `department`, `lecturer`, `student` |
| `status` | string | |
| `department_id` | UUID? | |
| `programme_id` | UUID? | |
| `level` | int? | |
| `student_category` | string? | |
| `student_number` | string? | |
| `staff_id` | string? | |
| `rank` | string? | |
| `phone` | string? | |
| `office` | string? | |
| `photo_url` | string? | |
| `title` | string? | |
| `two_factor_enabled` | boolean | |
| `last_login_at` | datetime? | |
| `created_at` | datetime? | |
| `department` | object? | `{id, name, code}` |
| `programme` | object? | `{id, name, code}` |
| `permissions` | string[] | List of permission codes |

---

### POST `/api/v1/auth/logout`

Logout and invalidate current token.

- **Permission:** Authenticated user
- **Headers:** `Authorization: Bearer <token>`
- **Response:** `{"message": "Logged out successfully"}`

---

### POST `/api/v1/auth/2fa/verify`

Verify 2FA code and complete login.

- **Permission:** Authenticated user (pending 2FA)
- **Request Body** (`TwoFactorVerifyRequest`):

| Field | Type | Required |
|-------|------|----------|
| `code` | string | Yes |

- **Response** (`LoginResponse`): Same as login response.

---

### POST `/api/v1/auth/2fa/setup`

Setup TOTP 2FA for current user.

- **Permission:** Authenticated user
- **Response** (`TwoFactorSetupResponse`):

| Field | Type | Notes |
|-------|------|-------|
| `secret` | string | TOTP secret key |
| `qr_code` | string | QR code data URL |
| `backup_codes` | string[] | One-time backup codes |

---

### POST `/api/v1/auth/2fa/enable`

Enable 2FA after setup.

- **Permission:** Authenticated user
- **Response:** `{"message": "2FA enabled successfully"}`

---

### POST `/api/v1/auth/2fa/disable`

Disable 2FA.

- **Permission:** Authenticated user
- **Response:** `{"message": "2FA disabled successfully"}`

---

### POST `/api/v1/auth/accept-invitation`

Accept an invitation and activate the account.

- **Permission:** Public (no auth required)
- **Request Body** (`AcceptInvitationRequest`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `token` | string | Yes | Invitation token |
| `password` | string | Yes | min_length=8 |
| `name` | string? | No | Override display name |

- **Response** (`LoginResponse`): Same as login response.

---

### GET `/api/v1/auth/invitation/{token}`

Get invitation details for the activation screen.

- **Permission:** Public (no auth required)
- **Path Parameters:**

| Param | Type |
|-------|------|
| `token` | string |

- **Response** (`InvitationInfoResponse`):

| Field | Type |
|-------|------|
| `email` | string |
| `name` | string |
| `role` | string |

---

## 2. Password Management

Prefix: `/api/v1/password`

### POST `/api/v1/password/forgot`

Initiate password reset -- sends a 6-digit code to email.

- **Permission:** Public (no auth required)
- **Request Body** (`ForgotPasswordRequest`):

| Field | Type | Required |
|-------|------|----------|
| `email` | EmailStr | Yes |

- **Response:** `{"message": "If the email exists, a reset code has been sent", "expires_in_minutes": 15}`

---

### POST `/api/v1/password/verify-code`

Verify the 6-digit code and return a reset token.

- **Permission:** Public (no auth required)
- **Request Body** (`ForgotPasswordVerifyCode`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `email` | EmailStr | Yes | |
| `code` | string | Yes | Exactly 6 characters |

- **Response:** `{"token": "...", "message": "Code verified successfully"}`

---

### POST `/api/v1/password/reset`

Reset password using token from verified code.

- **Permission:** Public (no auth required)
- **Request Body** (`ResetPasswordRequest`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `token` | string | Yes | |
| `new_password` | string | Yes | min 8 chars, must contain upper+lower+digit |

- **Response:** `{"message": "Password reset successfully..."}`

---

### POST `/api/v1/password/change`

Change password (requires old password). User must be authenticated.

- **Permission:** Authenticated user
- **Request Body** (`ChangePasswordRequest`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `old_password` | string | Yes | |
| `new_password` | string | Yes | min 8 chars, must contain upper+lower+digit |

- **Response:** `{"message": "Password changed successfully"}`

---

## 3. Profile

Prefix: `/api/v1/me`

### GET `/api/v1/me/profile`

Get current user profile.

- **Permission:** Authenticated user
- **Response** (`ProfileResponse`):

| Field | Type |
|-------|------|
| `id` | UUID |
| `email` | string |
| `name` | string |
| `role` | string |
| `phone` | string? |
| `office` | string? |
| `photo_url` | string? |
| `title` | string? |

---

### PATCH `/api/v1/me/profile`

Update current user profile.

- **Permission:** Authenticated user
- **Request Body** (`ProfileUpdateRequest`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string? | No | min 1, max 255 |
| `phone` | string? | No | max 20 |
| `office` | string? | No | max 100 |

- **Response** (`ProfileResponse`): Same as GET profile.

---

### POST `/api/v1/me/photo`

Upload profile photo (PNG, JPEG, or WebP, max 2MB).

- **Permission:** Authenticated user
- **Request Body:** `multipart/form-data` with `file` field
- **Response:** `{"data": {"photo_url": "..."}}`

---

### DELETE `/api/v1/me/photo`

Delete profile photo.

- **Permission:** Authenticated user
- **Status:** 204 No Content

---

### POST `/api/v1/me/password`

Change password.

- **Permission:** Authenticated user
- **Request Body** (`PasswordChangeRequest`):

| Field | Type | Required |
|-------|------|----------|
| `current_password` | string | Yes |
| `new_password` | string | Yes (min 8 chars) |
| `confirm_password` | string | Yes |

- **Response:** `{"message": "Password changed successfully."}`

---

### GET `/api/v1/me/sessions`

List active sessions for the current user.

- **Permission:** Authenticated user
- **Response** (`SessionListResponse`):

| Field | Type | Notes |
|-------|------|-------|
| `data` | SessionResponse[] | |

`SessionResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `user_agent` | string? |
| `ip_address` | string? |
| `location` | string? |
| `created_at` | datetime? |
| `last_seen_at` | datetime? |
| `is_current` | boolean |

---

### DELETE `/api/v1/me/sessions/{session_id}`

Revoke a specific session.

- **Permission:** Authenticated user
- **Path Parameters:** `session_id` (UUID)
- **Status:** 204 No Content

---

### POST `/api/v1/me/sessions/revoke-others`

Revoke all sessions except the current one.

- **Permission:** Authenticated user
- **Response:** `{"message": "N session(s) revoked."}`

---

### GET `/api/v1/me/notification-preferences`

Get notification preferences.

- **Permission:** Authenticated user
- **Response** (`NotificationPreferencesResponse`):

| Field | Type | Default |
|-------|------|---------|
| `schedule_notifications` | boolean | true |
| `assessment_notifications` | boolean | true |
| `attendance_notifications` | boolean | true |
| `graduation_notifications` | boolean | true |
| `email_notifications` | boolean | true |
| `in_app_notifications` | boolean | true |

---

### PUT `/api/v1/me/notification-preferences`

Update notification preferences.

- **Permission:** Authenticated user
- **Request Body** (`NotificationPreferencesUpdate`): All fields are optional booleans (same fields as response).
- **Response** (`NotificationPreferencesResponse`): Same as GET response.

---

## 4. Users

Prefix: `/api/v1/users`

### GET `/api/v1/users/me`

Get current user info.

- **Permission:** Authenticated user
- **Response** (`UserResponse`):

| Field | Type |
|-------|------|
| `id` | UUID |
| `email` | string |
| `first_name` | string |
| `last_name` | string |
| `phone_number` | string? |
| `role` | UserRole |
| `is_active` | boolean |
| `two_factor_enabled` | boolean |
| `last_login` | datetime? |

---

### PATCH `/api/v1/users/update`

Update user info.

- **Permission:** Authenticated user
- **Request Body** (`UserProfileUpdate`):

| Field | Type | Required |
|-------|------|----------|
| `first_name` | string? | No |
| `last_name` | string? | No |
| `phone_number` | string? | No |

- **Response** (`UserResponse`): Same as above.

---

## 5. Admin

Prefix: `/api/v1/admin`

### GET `/api/v1/admin/users`

Get all users with filtering and pagination.

- **Permission:** `users.manage`
- **Query Parameters:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `per_page` | int | 20 | |
| `page` | int | 1 | |
| `name` | string? | null | Filter by name |
| `role` | UserRole? | null | Filter by role |
| `is_active` | boolean? | null | Filter by active status |
| `last_login` | datetime? | null | Filter by last login |
| `phone_number` | string? | null | Filter by phone |
| `email` | string? | null | Filter by email |

- **Response** (`UsersListResponse`):

| Field | Type |
|-------|------|
| `items` | UserResponse[] |
| `pagination` | `{total, page, per_page, total_pages, has_next, has_prev}` |

---

### GET `/api/v1/admin/users/{user_id}`

Get a single user by ID.

- **Permission:** `users.manage`
- **Path Parameters:** `user_id` (UUID)
- **Response** (`UserResponse`): Same user fields as above.

---

### PATCH `/api/v1/admin/users/{user_id}`

Update user status (activate/deactivate).

- **Permission:** `users.manage`
- **Path Parameters:** `user_id` (UUID)
- **Request Body** (`UserStatusUpdate`):

| Field | Type | Required |
|-------|------|----------|
| `is_active` | boolean? | No |

- **Response** (`UserResponse`)

---

### PATCH `/api/v1/admin/users/{user_id}/role`

Update a user's role.

- **Permission:** `users.manage`
- **Path Parameters:** `user_id` (UUID)
- **Request Body** (`UserRoleUpdate`):

| Field | Type | Required |
|-------|------|----------|
| `role` | UserRole? | No |

- **Response** (`UserResponse`)

---

### GET `/api/v1/admin/audit-logs`

Get audit logs (admin).

- **Permission:** `audit.view`
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `skip` | int | 0 |
| `limit` | int | 100 |

- **Response:** Array of audit log objects.

---

## 6. Roles & Permissions

Prefix: `/api/v1/roles`

### POST `/api/v1/roles`

Create a new role.

- **Permission:** `roles.manage`
- **Request Body** (`RoleCreate`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | |
| `code` | string | Yes | |
| `description` | string? | No | |
| `is_admin_role` | boolean | No | default false |
| `permission_ids` | UUID[] | No | default [] |

- **Response** (`RoleResponse`):

| Field | Type |
|-------|------|
| `id` | UUID |
| `name` | string |
| `code` | string |
| `description` | string? |
| `is_admin_role` | boolean |
| `is_system_role` | boolean |
| `is_active` | boolean |
| `created_at` | datetime |
| `permissions` | PermissionResponse[] |

- **Status:** 201 Created

---

### GET `/api/v1/roles`

List all roles.

- **Permission:** `roles.manage`
- **Response:** `RoleResponse[]`

---

### GET `/api/v1/roles/{role_id}`

Get role details.

- **Permission:** `roles.manage`
- **Path Parameters:** `role_id` (UUID)
- **Response** (`RoleResponse`)

---

### PATCH `/api/v1/roles/{role_id}`

Update role.

- **Permission:** `roles.manage`
- **Path Parameters:** `role_id` (UUID)
- **Request Body** (`RoleUpdate`):

| Field | Type | Required |
|-------|------|----------|
| `name` | string? | No |
| `description` | string? | No |
| `permission_ids` | UUID[]? | No |
| `is_active` | boolean? | No |

- **Response** (`RoleResponse`)

---

### DELETE `/api/v1/roles/{role_id}`

Delete role.

- **Permission:** `roles.manage`
- **Path Parameters:** `role_id` (UUID)
- **Status:** 204 No Content

---

### GET `/api/v1/roles/permissions/all`

List all available permissions.

- **Permission:** `roles.manage`
- **Response** (`PermissionResponse[]`):

| Field | Type |
|-------|------|
| `id` | UUID |
| `name` | string |
| `code` | string |
| `description` | string? |
| `module` | string |
| `is_active` | boolean |
| `created_at` | datetime |

---

## 7. Role Templates

Prefix: `/api/v1/role-templates`

### GET `/api/v1/role-templates`

List all role templates.

- **Permission:** `roles.manage`
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `page` | int | 1 |
| `page_size` | int | 25 (max 100) |

- **Response** (`RoleTemplateListResponse`):

| Field | Type |
|-------|------|
| `data` | RoleTemplateResponse[] |
| `meta` | `{page, page_size}` |

`RoleTemplateResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `name` | string |
| `role` | string |
| `permissions` | string[] |
| `created_at` | datetime? |
| `updated_at` | datetime? |

---

### POST `/api/v1/role-templates`

Create a role template.

- **Permission:** `roles.manage`
- **Request Body** (`RoleTemplateCreate`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | max 255 |
| `role` | string | Yes | max 20 |
| `permissions` | string[] | No | default [] |

- **Response** (`RoleTemplateResponse`)
- **Status:** 201 Created

---

### GET `/api/v1/role-templates/{template_id}`

Get a role template by ID.

- **Permission:** `roles.manage`
- **Path Parameters:** `template_id` (UUID)
- **Response** (`RoleTemplateResponse`)

---

### PATCH `/api/v1/role-templates/{template_id}`

Update a role template.

- **Permission:** `roles.manage`
- **Path Parameters:** `template_id` (UUID)
- **Request Body** (`RoleTemplateUpdate`):

| Field | Type | Required |
|-------|------|----------|
| `name` | string? | No |
| `permissions` | string[]? | No |

- **Response** (`RoleTemplateResponse`)

---

### DELETE `/api/v1/role-templates/{template_id}`

Delete a role template.

- **Permission:** `roles.manage`
- **Path Parameters:** `template_id` (UUID)
- **Status:** 204 No Content

---

## 8. Departments

Prefix: `/api/v1/departments`

### GET `/api/v1/departments`

List departments.

- **Permission:** `departments.view`
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `search` | string? | null |
| `page` | int | 1 |
| `page_size` | int | 25 (max 100) |

- **Response** (`DepartmentListResponse`):

| Field | Type |
|-------|------|
| `data` | DepartmentResponse[] |
| `meta` | `{page, page_size}` |

`DepartmentResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `name` | string |
| `code` | string |
| `school` | string? |
| `email` | string |
| `phone` | string? |
| `tone` | DepartmentTone? |
| `subject_prefixes` | string[] |
| `created_at` | datetime |
| `updated_at` | datetime |

---

### POST `/api/v1/departments`

Create a new department.

- **Permission:** `departments.manage`
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `generate_temp_password` | boolean | false |

- **Request Body** (`DepartmentCreate`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | max 255 |
| `code` | string | Yes | max 50 |
| `school` | string? | No | default "SPMS" |
| `email` | string | Yes | max 255 |
| `phone` | string? | No | |
| `tone` | DepartmentTone? | No | default BLUE |
| `subject_prefixes` | string[]? | No | default [] |

- **Response** (`DepartmentResponse`)
- **Status:** 201 Created

---

### GET `/api/v1/departments/{department_id}`

Get department details.

- **Permission:** `departments.view`
- **Path Parameters:** `department_id` (UUID)
- **Response** (`DepartmentDetailResponse`):

Extends `DepartmentResponse` with:

| Field | Type |
|-------|------|
| `programmes_count` | int |
| `courses_count` | int |
| `lecturers_count` | int |
| `students_count` | int |
| `admin_account` | object? |

---

### PATCH `/api/v1/departments/{department_id}`

Update department.

- **Permission:** `departments.manage`
- **Path Parameters:** `department_id` (UUID)
- **Request Body** (`DepartmentUpdate`): All fields optional (same fields as DepartmentCreate).
- **Response** (`DepartmentResponse`)

---

### DELETE `/api/v1/departments/{department_id}`

Delete department.

- **Permission:** `departments.manage`
- **Path Parameters:** `department_id` (UUID)
- **Query Parameters:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `force` | boolean | false | Force delete even if has children |
| `lecturers` | string | "disable" | What to do with lecturers |

- **Status:** 204 No Content

---

### POST `/api/v1/departments/{department_id}/resend-invitation`

Resend invitation to department admin.

- **Permission:** `departments.manage`
- **Path Parameters:** `department_id` (UUID)
- **Response:** `{"message": "Invitation resent successfully", "email": "..."}`

---

## 9. Programmes

Prefix: `/api/v1/programmes`

### GET `/api/v1/programmes`

List programmes.

- **Permission:** `programmes.view`
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `department_id` | UUID? | null (scoped to user's department for DEPARTMENT role) |
| `page` | int | 1 |
| `page_size` | int | 25 (max 100) |

- **Response** (`ProgrammeListResponse`):

| Field | Type |
|-------|------|
| `data` | ProgrammeResponse[] |
| `meta` | `{page, page_size}` |

`ProgrammeResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `code` | string |
| `name` | string |
| `department_id` | UUID |
| `levels` | int[] |
| `category` | ProgrammeCategory |
| `created_at` | datetime |
| `updated_at` | datetime |

---

### POST `/api/v1/programmes`

Create programme.

- **Permission:** `programmes.manage`
- **Request Body** (`ProgrammeCreate`):

| Field | Type | Required |
|-------|------|----------|
| `code` | string | Yes |
| `name` | string | Yes |
| `department_id` | UUID | Yes |
| `levels` | int[] | Yes (min 1) |
| `category` | ProgrammeCategory | Yes |

- **Response** (`ProgrammeResponse`)
- **Status:** 201 Created

---

### GET `/api/v1/programmes/{programme_id}`

Get programme by ID.

- **Permission:** `programmes.view`
- **Path Parameters:** `programme_id` (UUID)
- **Response** (`ProgrammeResponse`)

---

### PATCH `/api/v1/programmes/{programme_id}`

Update programme.

- **Permission:** `programmes.manage`
- **Path Parameters:** `programme_id` (UUID)
- **Request Body** (`ProgrammeUpdate`):

| Field | Type | Required |
|-------|------|----------|
| `code` | string? | No |
| `name` | string? | No |
| `levels` | int[]? | No |
| `category` | ProgrammeCategory? | No |

- **Response** (`ProgrammeResponse`)

---

### DELETE `/api/v1/programmes/{programme_id}`

Delete programme.

- **Permission:** `programmes.manage`
- **Path Parameters:** `programme_id` (UUID)
- **Query Parameters:** `force` (boolean, default false)
- **Status:** 204 No Content

---

## 10. Courses

Prefix: `/api/v1/courses`

### GET `/api/v1/courses`

List courses (scoped by role).

- **Permission:** `courses.view`
- **Query Parameters:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `department_id` | UUID? | null | Auto-set for DEPARTMENT role |
| `lecturer_id` | UUID? | null | Auto-set for LECTURER role |
| `programme_id` | UUID? | null | |
| `level` | int? | null | |
| `search` | string? | null | |
| `page` | int | 1 | |
| `page_size` | int | 25 (max 100) | |

- **Response** (`CourseListResponse`):

| Field | Type |
|-------|------|
| `data` | CourseResponse[] |
| `meta` | `{page, page_size, ...}` |

`CourseResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `code` | string |
| `title` | string |
| `department_id` | UUID |
| `type` | CourseType |
| `credit_hours` | int |
| `mode` | CourseMode |
| `student_count` | int |
| `lecturer_id` | UUID? |
| `cohorts` | CourseCohort[] |
| `created_at` | datetime |
| `updated_at` | datetime |

`CourseCohort`:

| Field | Type |
|-------|------|
| `programme_id` | UUID |
| `level` | int |

---

### POST `/api/v1/courses`

Create course.

- **Permission:** `courses.manage`
- **Request Body** (`CourseCreate`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `code` | string | Yes | max 50 |
| `title` | string | Yes | max 255 |
| `department_id` | UUID | Yes | |
| `type` | CourseType | Yes | |
| `credit_hours` | int | Yes | 1-6 |
| `mode` | CourseMode | No | default IN_PERSON |
| `student_count` | int | Yes | min 1 |
| `lecturer_id` | UUID? | No | |
| `cohorts` | CourseCohort[] | Yes | min 1 item |

- **Response** (`CourseResponse`)
- **Status:** 201 Created

---

### GET `/api/v1/courses/{course_id}`

Get course by ID.

- **Permission:** `courses.view`
- **Path Parameters:** `course_id` (UUID)
- **Response** (`CourseResponse`)

---

### PATCH `/api/v1/courses/{course_id}`

Update course.

- **Permission:** `courses.manage`
- **Path Parameters:** `course_id` (UUID)
- **Request Body** (`CourseUpdate`): All fields optional (title, type, credit_hours, mode, student_count, lecturer_id, cohorts).
- **Response** (`CourseResponse`)

---

### DELETE `/api/v1/courses/{course_id}`

Delete course.

- **Permission:** `courses.manage`
- **Path Parameters:** `course_id` (UUID)
- **Query Parameters:** `force` (boolean, default false)
- **Status:** 204 No Content

---

### GET `/api/v1/courses/{course_id}/students`

Get enrolled students for a course.

- **Permission:** `courses.view`
- **Path Parameters:** `course_id` (UUID)
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `page` | int | 1 |
| `page_size` | int | 25 (max 100) |

- **Response:**

```json
{
  "data": [
    {
      "id": "UUID",
      "name": "string",
      "email": "string",
      "student_number": "string",
      "programme": "string?",
      "level": "int"
    }
  ],
  "meta": {"page": 1, "page_size": 25}
}
```

---

## 11. Venues

Prefix: `/api/v1/venues`

### GET `/api/v1/venues`

List venues.

- **Permission:** `venues.view`
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `venue_type` | string? | null |
| `status` | string? | null |
| `search` | string? | null |
| `page` | int | 1 |
| `page_size` | int | 25 (max 100) |

- **Response** (`VenueListResponse`):

| Field | Type |
|-------|------|
| `data` | VenueResponse[] |
| `meta` | `{page, page_size}` |

`VenueResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `code` | string? |
| `building` | string |
| `room_number` | string |
| `location` | string? |
| `gps_address` | string? |
| `latitude` | string? |
| `longitude` | string? |
| `capacity` | int? |
| `type` | VenueType |
| `is_shared` | boolean |
| `status` | VenueStatus |
| `created_at` | datetime |
| `updated_at` | datetime |

---

### POST `/api/v1/venues`

Create venue.

- **Permission:** `venues.manage`
- **Request Body** (`VenueCreate`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `code` | string? | No | |
| `building` | string | Yes | max 100 |
| `room_number` | string | Yes | max 50 |
| `location` | string? | No | |
| `gps_address` | string? | No | |
| `latitude` | string? | No | |
| `longitude` | string? | No | |
| `capacity` | int? | No | |
| `type` | VenueType | Yes | |
| `is_shared` | boolean | No | default false |
| `status` | VenueStatus | No | default AVAILABLE |

- **Response** (`VenueResponse`)
- **Status:** 201 Created

---

### GET `/api/v1/venues/{venue_id}`

Get venue by ID.

- **Permission:** `venues.view`
- **Path Parameters:** `venue_id` (UUID)
- **Response** (`VenueResponse`)

---

### PATCH `/api/v1/venues/{venue_id}`

Update venue.

- **Permission:** `venues.manage`
- **Path Parameters:** `venue_id` (UUID)
- **Request Body** (`VenueUpdate`): All fields optional.
- **Response** (`VenueResponse`)

---

### DELETE `/api/v1/venues/{venue_id}`

Delete venue.

- **Permission:** `venues.manage`
- **Path Parameters:** `venue_id` (UUID)
- **Status:** 204 No Content

---

### POST `/api/v1/venues/{venue_id}/unavailable`

Mark venue as unavailable.

- **Permission:** `venues.manage`
- **Path Parameters:** `venue_id` (UUID)
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `reason` | string | Yes |
| `until` | datetime? | No |

- **Response** (`VenueResponse`)

---

### POST `/api/v1/venues/{venue_id}/available`

Mark venue as available.

- **Permission:** `venues.manage`
- **Path Parameters:** `venue_id` (UUID)
- **Response** (`VenueResponse`)

---

## 12. Semesters

Prefix: `/api/v1/semesters`

### GET `/api/v1/semesters`

List all semesters.

- **Permission:** Authenticated user
- **Response** (`SemesterListResponse`):

| Field | Type |
|-------|------|
| `data` | SemesterResponse[] |

`SemesterResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `academic_year` | string |
| `number` | int |
| `label` | string |
| `start_date` | datetime |
| `end_date` | datetime |
| `teaching_start` | datetime? |
| `teaching_end` | datetime? |
| `registration_deadline` | datetime? |
| `graduation_deadline` | datetime? |
| `is_active` | boolean |
| `created_at` | datetime |
| `updated_at` | datetime |

---

### POST `/api/v1/semesters`

Create semester.

- **Permission:** `settings.institution`
- **Request Body** (`SemesterCreate`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `academic_year` | string | Yes | e.g. "2026/27" |
| `number` | int | Yes | 1 or 2 |
| `label` | string | Yes | max 50 |
| `start_date` | datetime | Yes | |
| `end_date` | datetime | Yes | |
| `teaching_start` | datetime? | No | |
| `teaching_end` | datetime? | No | |
| `registration_deadline` | datetime? | No | |
| `graduation_deadline` | datetime? | No | |
| `is_active` | boolean | No | default false |

- **Response** (`SemesterResponse`)
- **Status:** 201 Created

---

### GET `/api/v1/semesters/{semester_id}`

Get semester by ID.

- **Permission:** Authenticated user
- **Path Parameters:** `semester_id` (UUID)
- **Response** (`SemesterResponse`)

---

### PATCH `/api/v1/semesters/{semester_id}`

Update semester.

- **Permission:** `settings.institution`
- **Path Parameters:** `semester_id` (UUID)
- **Request Body** (`SemesterUpdate`): All fields optional.
- **Response** (`SemesterResponse`)

---

### POST `/api/v1/semesters/{semester_id}/activate`

Activate a semester (sets it as the current active semester).

- **Permission:** `settings.institution`
- **Path Parameters:** `semester_id` (UUID)
- **Response** (`SemesterResponse`)

---

## 13. Timetables (Master)

Prefix: `/api/v1/timetables`

### GET `/api/v1/timetables`

List uploaded master timetables.

- **Permission:** `timetable.view`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `semester_id` | UUID | Yes |

- **Response** (`TimetableListResponse`):

| Field | Type |
|-------|------|
| `data` | object[] |

---

### GET `/api/v1/timetables/entries`

Get master timetable entries.

- **Permission:** `timetable.view`
- **Query Parameters:**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `semester_id` | UUID | Yes | |
| `level` | int? | No | |
| `venue` | string? | No | Venue code |
| `subjects` | string? | No | Comma-separated |
| `day` | int? | No | Day index |

- **Response** (`TimetableEntriesResponse`):

| Field | Type |
|-------|------|
| `data` | object[] |
| `meta` | object |

---

### POST `/api/v1/timetables/preview`

Preview master timetable upload. Accepts Excel (.xlsx) or CSV file.

- **Permission:** `timetable.upload`
- **Content-Type:** `multipart/form-data`
- **Query Parameters:**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `semester_id` | UUID | Yes | |
| `level` | int? | No | 100-400; omit to parse all levels |

- **Form Data:** `file` (UploadFile, .xlsx or .csv)
- **Response** (`TimetablePreviewResponse`):

| Field | Type |
|-------|------|
| `preview_id` | string |
| `entries` | object[] |
| `issues` | object[] |
| `summary` | object |
| `replaces` | object? |
| `affected_requests` | object[] |

---

### POST `/api/v1/timetables/publish`

Publish previewed master timetable.

- **Permission:** `timetable.upload`
- **Request Body** (`TimetablePublishRequest`):

| Field | Type | Required |
|-------|------|----------|
| `preview_id` | string | Yes |

- **Response:** `{"message": "..."}`

---

### POST `/api/v1/timetables/department/preview`

Preview department timetable upload.

- **Permission:** `timetable.department_upload`
- **Content-Type:** `multipart/form-data`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `semester_id` | UUID | Yes |
| `department_id` | UUID | Yes |

- **Form Data:** `file` (UploadFile, .xlsx or .csv)
- **Response** (`DepartmentTimetablePreviewResponse`):

| Field | Type |
|-------|------|
| `preview_id` | string |
| `entries` | object[] |
| `conflicts` | object[] |
| `summary` | object |

---

### POST `/api/v1/timetables/department/publish`

Publish previewed department timetable.

- **Permission:** `timetable.department_upload`
- **Request Body** (`TimetablePublishRequest`):

| Field | Type | Required |
|-------|------|----------|
| `preview_id` | string | Yes |

- **Response:** `{"message": "..."}`

---

### GET `/api/v1/timetables/template`

Download sample CSV template.

- **Permission:** Public (no auth required)
- **Response:** CSV file download (`master-timetable-template.csv`)

---

### GET `/api/v1/timetables/export`

Export master timetable as CSV.

- **Permission:** `timetable.view`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `semester_id` | UUID | Yes |
| `level` | int? | No |

- **Response:** CSV file download

---

### GET `/api/v1/timetables/history`

Get timetable upload history.

- **Permission:** `timetable.view`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `semester_id` | UUID | Yes |

- **Response:** `{"data": [...]}`

---

### POST `/api/v1/timetables/entries`

Create a new master timetable entry.

- **Permission:** `timetable.edit`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `semester_id` | UUID | Yes |
| `level` | int | Yes |
| `day` | int | Yes |
| `period` | int | Yes |
| `subject` | string | Yes |
| `venue_code` | string | Yes |

- **Response:** `{"data": {"id": "UUID", "subject": "...", "venue_code": "..."}}`
- **Status:** 201 Created

---

### PATCH `/api/v1/timetables/entries/{entry_id}`

Update a master timetable entry.

- **Permission:** `timetable.edit`
- **Path Parameters:** `entry_id` (UUID)
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `subject` | string? | No |
| `venue_code` | string? | No |
| `is_free` | boolean? | No |

- **Response:** `{"data": {"id": "UUID", "subject": "...", "venue_code": "...", "is_free": bool}}`

---

### DELETE `/api/v1/timetables/entries/{entry_id}`

Delete a master timetable entry.

- **Permission:** `timetable.edit`
- **Path Parameters:** `entry_id` (UUID)
- **Status:** 204 No Content

---

### GET `/api/v1/timetables/double-bookings`

Find cells with multiple subjects (excluding shared venues).

- **Permission:** `timetable.view`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `semester_id` | UUID | Yes |

- **Response:** `{"data": [{"venue": "...", "day": 0, "period": 0, "subjects": ["..."]}]}`

---

## 14. Slot Requests

Prefix: `/api/v1/slot-requests`

### GET `/api/v1/slot-requests/free-slots`

Get FREE slots for scheduling.

- **Permission:** `schedule.view`
- **Query Parameters:**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `semester_id` | UUID | Yes | |
| `level` | int? | No | |
| `venue` | string? | No | Venue code |
| `view` | string | No | default "free" |

- **Response:** Free slot data object

---

### POST `/api/v1/slot-requests/check`

Check for clashes before submitting a slot request.

- **Permission:** `schedule.request`
- **Request Body** (`SlotRequestCreate`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `course_id` | UUID | Yes | |
| `semester_id` | UUID | Yes | |
| `level` | int | Yes | |
| `day` | int | Yes | |
| `venue_code` | string | Yes | |
| `start_period` | int | Yes | |
| `period_count` | int | Yes | 1-3 |

- **Response** (`SlotRequestCheckResponse`):

| Field | Type |
|-------|------|
| `clashes` | object[] |
| `blocking` | boolean |

---

### POST `/api/v1/slot-requests`

Submit slot request.

- **Permission:** `schedule.request`
- **Request Body** (`SlotRequestCreate`): Same as check endpoint.
- **Response** (`SlotRequestResponse`):

| Field | Type |
|-------|------|
| `id` | UUID |
| `course_id` | UUID |
| `department_id` | UUID |
| `requested_by_id` | UUID |
| `semester_id` | UUID |
| `level` | int |
| `day` | int |
| `venue_code` | string |
| `start_period` | int |
| `period_count` | int |
| `status` | string |
| `review_comment` | string? |
| `reviewed_by_id` | UUID? |
| `reviewed_at` | string? |
| `schedule_item_id` | UUID? |
| `clashes` | object[] |
| `competing` | object[] |

- **Status:** 201 Created

---

### GET `/api/v1/slot-requests`

List slot requests.

- **Permission:** `schedule.view`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `semester_id` | UUID | Yes |
| `status` | string? | No |
| `department_id` | UUID? | No |

- **Response** (`SlotRequestListResponse`):

| Field | Type |
|-------|------|
| `data` | SlotRequestResponse[] |
| `meta` | object |

---

### DELETE `/api/v1/slot-requests/{request_id}`

Withdraw a pending slot request.

- **Permission:** `schedule.withdraw`
- **Path Parameters:** `request_id` (UUID)
- **Status:** 204 No Content

---

### POST `/api/v1/slot-requests/{request_id}/approve`

Approve slot request.

- **Permission:** `schedule.approve`
- **Path Parameters:** `request_id` (UUID)
- **Query Parameters:** `comment` (string?, optional)
- **Response** (`SlotRequestResponse`)

---

### POST `/api/v1/slot-requests/{request_id}/return`

Return slot request (request revision).

- **Permission:** `schedule.approve`
- **Path Parameters:** `request_id` (UUID)
- **Query Parameters:** `comment` (string, required)
- **Response** (`SlotRequestResponse`)

---

### POST `/api/v1/slot-requests/{request_id}/override`

Override slot request despite clashes.

- **Permission:** `conflicts.override`
- **Path Parameters:** `request_id` (UUID)
- **Query Parameters:** `reason` (string, required)
- **Response** (`SlotRequestResponse`)

---

## 15. Schedule

Prefix: `/api/v1/schedule`

### GET `/api/v1/schedule`

List schedule items.

- **Permission:** `schedule.view`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `semester_id` | UUID | Yes |
| `department_id` | UUID? | No |
| `level` | int? | No |
| `venue_type` | string? | No |
| `search` | string? | No |
| `status` | string? | No |

- **Response** (`ScheduleItemListResponse`):

| Field | Type |
|-------|------|
| `data` | ScheduleItemResponse[] |
| `meta` | object |

`ScheduleItemResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `semester_id` | UUID |
| `course_id` | UUID |
| `department_id` | UUID |
| `day` | int |
| `start_period` | int? |
| `period_count` | int? |
| `start` | string? |
| `end` | string? |
| `venue_code` | string |
| `lecturer_id` | UUID? |
| `mode` | string |
| `status` | string |
| `source` | string |

---

### POST `/api/v1/schedule`

Create manual schedule item.

- **Permission:** `schedule.manage`
- **Request Body** (`ScheduleItemCreate`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `semester_id` | UUID | Yes | |
| `course_id` | UUID | Yes | |
| `day` | int | Yes | 0-4 (Mon-Fri) |
| `start` | string? | No | Time string |
| `end` | string? | No | Time string |
| `start_period` | int? | No | Period index |
| `period_count` | int? | No | 1-3 |
| `venue_code` | string | Yes | |
| `lecturer_id` | UUID? | No | |
| `mode` | string | No | default "in-person" |
| `groups` | object[] | No | default [] |

- **Response** (`ScheduleItemResponse`)
- **Status:** 201 Created

---

### GET `/api/v1/schedule/{item_id}`

Get schedule item by ID.

- **Permission:** `schedule.view`
- **Path Parameters:** `item_id` (UUID)
- **Response** (`ScheduleItemResponse`)

---

### PATCH `/api/v1/schedule/{item_id}`

Update schedule item.

- **Permission:** `schedule.manage`
- **Path Parameters:** `item_id` (UUID)
- **Request Body** (`ScheduleItemUpdate`): All fields optional.
- **Response** (`ScheduleItemResponse`)

---

### DELETE `/api/v1/schedule/{item_id}`

Delete schedule item.

- **Permission:** `schedule.manage`
- **Path Parameters:** `item_id` (UUID)
- **Status:** 204 No Content

---

### POST `/api/v1/schedule/publish`

Publish pending schedule items.

- **Permission:** `schedule.manage`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `ids` | UUID[]? | No |
| `course_code` | string? | No |

- **Response:** `{"message": "N courses published"}`

---

### GET `/api/v1/schedule/final`

Get final published timetable.

- **Permission:** `schedule.view`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `semester_id` | UUID | Yes |
| `level` | int? | No |

- **Response** (`ScheduleItemListResponse`)

---

### GET `/api/v1/schedule/final/export`

Export final timetable as CSV.

- **Permission:** `schedule.view`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `semester_id` | UUID | Yes |
| `level` | int? | No |

- **Response:** CSV file download

---

## 16. Personal Timetable

Prefix: `/api/v1/me/timetable`

### GET `/api/v1/me/timetable`

Get personal timetable for current user (lecturer or student).

- **Permission:** Authenticated user (lecturer, student, or super)
- **Query Parameters:**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `semester_id` | UUID? | No | |
| `week_of` | string? | No | Date string |
| `include` | string? | No | "department" or "lecturer" |

- **Response** (`PersonalTimetableResponse`):

| Field | Type |
|-------|------|
| `items` | TimetableItem[] |
| `assessments` | PersonalAssessment[] |
| `stats` | TimetableStats |

`TimetableItem`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `course_code` | string |
| `course_title` | string |
| `day` | int |
| `start` | string? |
| `end` | string? |
| `venue_code` | string |
| `lecturer_name` | string? |
| `mode` | string? |
| `department_name` | string? |
| `tone` | string? |
| `status` | string? |
| `groups` | string[] |
| `assigned_to_me` | boolean |

`PersonalAssessment`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `course_code` | string |
| `course_title` | string |
| `assessment_type` | string |
| `date` | datetime? |
| `start_time` | string? |
| `end_time` | string? |
| `location` | string? |
| `status` | string |

`TimetableStats`:

| Field | Type |
|-------|------|
| `weekly_classes` | int |
| `classes_today` | int |
| `upcoming_assessments` | int |
| `registered_courses` | int |
| `teaching_groups` | int |

---

### GET `/api/v1/me/timetable/export`

Export personal timetable as CSV.

- **Permission:** Authenticated user (lecturer, student, or super)
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `semester_id` | UUID? | No |
| `format` | string | No (default "csv") |

- **Response:** CSV file download

---

## 17. Conflicts

Prefix: `/api/v1/conflicts`

### GET `/api/v1/conflicts`

Get scheduling conflicts (Conflict Centre).

- **Permission:** `conflicts.view`
- **Query Parameters:**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `semester_id` | UUID? | No | Falls back to active semester |

- **Response** (`ConflictResponse`):

| Field | Type |
|-------|------|
| `requests` | RequestWithClashes[] |
| `stats` | ConflictStats |
| `double_bookings` | DoubleBooking[] |

`RequestWithClashes`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `course_code` | string |
| `course_title` | string |
| `department_name` | string |
| `venue_code` | string |
| `day` | int |
| `start_period` | int |
| `period_count` | int |
| `status` | string |
| `slot_label` | string |
| `clashes` | ClashDetail[] |

`ClashDetail`:

| Field | Type |
|-------|------|
| `kind` | string |
| `severity` | string |
| `message` | string |
| `other_request_id` | UUID? |
| `other_schedule_item_id` | UUID? |

`ConflictStats`:

| Field | Type |
|-------|------|
| `with_danger` | int |
| `warnings_only` | int |
| `double_bookings` | int |

`DoubleBooking`:

| Field | Type |
|-------|------|
| `venue` | string |
| `day` | int |
| `period` | int |
| `subjects` | string[] |

---

## 18. Faculty

Prefix: `/api/v1/faculty`

### GET `/api/v1/faculty`

List faculty members.

- **Permission:** `staff.view`
- **Query Parameters:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `status` | string? | null | Filter by status |
| `search` | string? | null | |
| `department_id` | UUID? | null | Scoped for DEPARTMENT role |
| `page` | int | 1 | |
| `page_size` | int | 25 (max 100) | |

- **Response** (`FacultyListResponse`):

| Field | Type |
|-------|------|
| `data` | FacultyResponse[] |
| `meta` | `{page, pageSize, total}` |

`FacultyResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `name` | string |
| `email` | string |
| `rank` | StaffRank? |
| `staff_id` | string? |
| `department_id` | UUID? |
| `status` | UserStatus |
| `course_count` | int |
| `last_login_at` | datetime? |
| `created_at` | datetime |

---

### POST `/api/v1/faculty`

Create faculty member.

- **Permission:** `staff.manage`
- **Request Body** (`FacultyCreate`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | max 255 |
| `email` | string | Yes | max 255 |
| `rank` | StaffRank? | No | |
| `staff_id` | string? | No | max 50 |
| `department_id` | UUID? | No | Defaults to user's department |

- **Response** (`FacultyResponse`)
- **Status:** 201 Created

---

### PATCH `/api/v1/faculty/{faculty_id}`

Update faculty member.

- **Permission:** `staff.manage`
- **Path Parameters:** `faculty_id` (UUID)
- **Request Body** (`FacultyUpdate`):

| Field | Type | Required |
|-------|------|----------|
| `name` | string? | No |
| `rank` | StaffRank? | No |
| `phone` | string? | No |
| `office` | string? | No |

- **Response** (`FacultyResponse`)

---

### POST `/api/v1/faculty/{faculty_id}/disable`

Disable a faculty member.

- **Permission:** `staff.manage`
- **Path Parameters:** `faculty_id` (UUID)
- **Response:** `{"message": "... has been disabled."}`

---

### POST `/api/v1/faculty/{faculty_id}/resend-invitation`

Resend invitation to faculty member.

- **Permission:** `staff.manage`
- **Path Parameters:** `faculty_id` (UUID)
- **Response:** `{"message": "Invitation resent successfully.", "email": "..."}`

---

## 19. Staff

Prefix: `/api/v1/staff`

### GET `/api/v1/staff`

List staff members.

- **Permission:** `users.manage`
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `role` | string? | null |
| `status` | string? | null |
| `search` | string? | null |
| `page` | int | 1 |
| `page_size` | int | 25 (max 100) |

- **Response** (`StaffListResponse`):

| Field | Type |
|-------|------|
| `data` | StaffResponse[] |
| `meta` | `{page, pageSize, counts}` |

`StaffResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `name` | string |
| `email` | string |
| `role` | UserRole |
| `rank` | StaffRank? |
| `staff_id` | string? |
| `department_id` | UUID? |
| `department_name` | string? |
| `status` | UserStatus |
| `course_count` | int |
| `last_login_at` | datetime? |
| `created_at` | datetime |

---

### POST `/api/v1/staff`

Create staff member.

- **Permission:** `users.manage`
- **Request Body** (`StaffCreate`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | max 255 |
| `staff_id` | string? | No | max 50 |
| `email` | string | Yes | max 255 |
| `rank` | StaffRank? | No | |
| `department_id` | UUID? | No | |
| `role` | UserRole | No | default LECTURER |

- **Response** (`StaffResponse`)
- **Status:** 201 Created

---

### PATCH `/api/v1/staff/{staff_id}`

Update staff member.

- **Permission:** `users.manage`
- **Path Parameters:** `staff_id` (UUID)
- **Request Body** (`StaffUpdate`):

| Field | Type | Required |
|-------|------|----------|
| `name` | string? | No |
| `rank` | StaffRank? | No |
| `department_id` | UUID? | No |
| `phone` | string? | No |
| `office` | string? | No |

- **Response** (`StaffResponse`)

---

## 20. Students

Prefix: `/api/v1/students`

### GET `/api/v1/students`

List students.

- **Permission:** `students.view`
- **Query Parameters:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `department_id` | UUID? | null | Scoped for DEPARTMENT role |
| `programme_id` | UUID? | null | |
| `level` | int? | null | |
| `search` | string? | null | |
| `page` | int | 1 | |
| `page_size` | int | 25 (max 100) | |

- **Response** (`StudentListResponse`):

| Field | Type |
|-------|------|
| `data` | StudentResponse[] |
| `meta` | `{page, pageSize, total}` |

`StudentResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `name` | string |
| `email` | string |
| `student_number` | string? |
| `programme_id` | UUID? |
| `programme_name` | string? |
| `level` | int? |
| `student_category` | StudentCategory? |
| `status` | UserStatus |
| `created_at` | datetime |

---

### GET `/api/v1/students/cohorts`

List student cohorts (programme + level groups).

- **Permission:** `students.view`
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `department_id` | UUID? | null |

- **Response** (`CohortListResponse`):

| Field | Type |
|-------|------|
| `data` | CohortResponse[] |

`CohortResponse`:

| Field | Type |
|-------|------|
| `programme_id` | UUID |
| `programme_name` | string |
| `level` | int |
| `student_count` | int |

---

## 21. Sections

Prefix: `/api/v1/sections`

### GET `/api/v1/sections`

List sections.

- **Permission:** `students.manage`
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `programme_id` | UUID? | null |
| `level` | int? | null |
| `course_id` | UUID? | null |
| `page` | int | 1 |
| `page_size` | int | 25 (max 100) |

- **Response** (`SectionListResponse`):

| Field | Type |
|-------|------|
| `data` | SectionResponse[] |
| `meta` | `{page, pageSize}` |

`SectionResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `programme_id` | UUID |
| `level` | int |
| `name` | string |
| `course_id` | UUID? |
| `student_ids` | UUID[] |
| `student_count` | int |
| `created_at` | datetime |
| `updated_at` | datetime |

---

### GET `/api/v1/sections/{section_id}`

Get section by ID.

- **Permission:** `students.manage`
- **Path Parameters:** `section_id` (UUID)
- **Response** (`SectionResponse`)

---

### POST `/api/v1/sections`

Create section.

- **Permission:** `students.manage`
- **Request Body** (`SectionCreate`):

| Field | Type | Required |
|-------|------|----------|
| `programme_id` | UUID | Yes |
| `level` | int | Yes (min 100) |
| `name` | string | Yes (max 100) |
| `course_id` | UUID? | No |
| `student_ids` | UUID[]? | No |

- **Response** (`SectionResponse`)
- **Status:** 201 Created

---

### PATCH `/api/v1/sections/{section_id}`

Update section.

- **Permission:** `students.manage`
- **Path Parameters:** `section_id` (UUID)
- **Request Body** (`SectionUpdate`):

| Field | Type | Required |
|-------|------|----------|
| `name` | string? | No |
| `student_ids` | UUID[]? | No |

- **Response** (`SectionResponse`)

---

### DELETE `/api/v1/sections/{section_id}`

Delete section.

- **Permission:** `students.manage`
- **Path Parameters:** `section_id` (UUID)
- **Status:** 204 No Content

---

## 22. Lecturer

Prefix: `/api/v1/lecturer`

### GET `/api/v1/lecturer/courses`

Get courses assigned to the current lecturer.

- **Permission:** Authenticated user (LECTURER role only)
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `semester_id` | UUID? | No |

- **Response:**

```json
{
  "data": [
    {
      "id": "UUID",
      "code": "string",
      "title": "string",
      "department": "string?",
      "type": "string",
      "credit_hours": "int",
      "enrolled_count": "int",
      "weekly_contact_hours": "int"
    }
  ]
}
```

---

### GET `/api/v1/lecturer/students`

Get students registered for a lecturer's course.

- **Permission:** Authenticated user (LECTURER role only)
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `course_id` | UUID | Yes |

- **Response:**

```json
{
  "data": [
    {
      "id": "UUID",
      "name": "string",
      "email": "string",
      "student_number": "string",
      "programme": "string?",
      "level": "int"
    }
  ],
  "meta": {
    "course_code": "string",
    "course_title": "string",
    "total": "int"
  }
}
```

---

## 23. Registration

Prefix: `/api/v1`

### GET `/api/v1/me/registrations`

List current student's course registrations.

- **Permission:** `registration.self`
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `semester_id` | UUID? | null |
| `page` | int | 1 |
| `page_size` | int | 50 (max 100) |

- **Response** (`RegistrationListResponse`):

| Field | Type |
|-------|------|
| `data` | RegistrationResponse[] |
| `meta` | `{page, pageSize, counts, totalCredits}` |

`RegistrationResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `student_id` | UUID |
| `course_id` | UUID? |
| `course_code` | string? |
| `course_title` | string? |
| `custom_course_code` | string? |
| `custom_course_title` | string? |
| `semester_id` | UUID |
| `level` | int |
| `registration_type` | RegistrationType |
| `credits` | int |
| `status` | RegistrationStatus |
| `source` | string? |
| `created_at` | datetime |

---

### GET `/api/v1/registration/catalogue`

Get available courses catalogue for registration.

- **Permission:** `registration.self`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `semester_id` | UUID | Yes |

- **Response** (`CatalogueListResponse`):

| Field | Type |
|-------|------|
| `data` | CatalogueCourseResponse[] |

`CatalogueCourseResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `code` | string |
| `title` | string |
| `department_id` | UUID |
| `department_name` | string? |
| `course_type` | string |
| `credit_hours` | int |
| `mode` | string |
| `lecturer_name` | string? |
| `is_programme_match` | boolean |

---

### POST `/api/v1/me/registrations`

Register for a course.

- **Permission:** `registration.self`
- **Request Body** (`RegistrationCreate`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `course_id` | UUID? | No | One of course_id or custom fields |
| `custom_course_code` | string? | No | max 50 |
| `custom_course_title` | string? | No | max 255 |
| `semester_id` | UUID | Yes | |
| `level` | int | Yes | min 100 |
| `registration_type` | RegistrationType | Yes | |
| `credits` | int | Yes | 1-6 |

- **Response** (`RegistrationResponse`)
- **Status:** 201 Created

---

### DELETE `/api/v1/me/registrations/{registration_id}`

Drop a course registration.

- **Permission:** `registration.self`
- **Path Parameters:** `registration_id` (UUID)
- **Status:** 204 No Content

---

## 24. Imports

Prefix: `/api/v1/imports`

### POST `/api/v1/imports/students`

Import students from CSV file.

- **Permission:** `imports.manage`
- **Content-Type:** `multipart/form-data`
- **Form Data:**

| Field | Type | Required |
|-------|------|----------|
| `file` | UploadFile (.csv) | Yes |
| `student_category` | string | Yes |
| `academic_year` | string | Yes |
| `programme_id` | UUID? | No |
| `level` | int? | No |

- **Response** (`ImportResponse`):

| Field | Type |
|-------|------|
| `id` | UUID |
| `kind` | string |
| `department_id` | UUID |
| `course_id` | UUID? |
| `programme_id` | UUID? |
| `programme_text` | string? |
| `level_text` | string? |
| `student_category` | string? |
| `academic_year` | string? |
| `semester_id` | UUID? |
| `filename` | string |
| `file_url` | string? |
| `row_count` | int? |
| `created_count` | int |
| `updated_count` | int |
| `warning_count` | int |
| `error_count` | int |
| `status` | string |
| `created_by_id` | UUID |
| `created_at` | datetime |

- **Status:** 201 Created

---

### POST `/api/v1/imports/course-roster`

Import course roster from CSV file.

- **Permission:** `imports.manage`
- **Content-Type:** `multipart/form-data`
- **Form Data:**

| Field | Type | Required |
|-------|------|----------|
| `file` | UploadFile (.csv) | Yes |
| `course_id` | UUID | Yes |
| `student_category` | string | Yes |
| `academic_year` | string | Yes |
| `semester_id` | UUID | Yes |

- **Response** (`ImportResponse`): Same as student import response.
- **Status:** 201 Created

---

### GET `/api/v1/imports`

List imports.

- **Permission:** `imports.view`
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `kind` | string? | null |
| `page` | int | 1 |
| `page_size` | int | 25 (max 100) |

- **Response** (`ImportListResponse`):

| Field | Type |
|-------|------|
| `data` | ImportResponse[] |
| `meta` | `{page, pageSize}` |

---

### GET `/api/v1/imports/{import_id}`

Get import details.

- **Permission:** `imports.view`
- **Path Parameters:** `import_id` (UUID)
- **Response** (`ImportResponse`)

---

### GET `/api/v1/imports/{import_id}/rows`

Get import row details.

- **Permission:** `imports.view`
- **Path Parameters:** `import_id` (UUID)
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `page` | int | 1 |
| `page_size` | int | 100 (max 500) |

- **Response** (`ImportRowListResponse`):

| Field | Type |
|-------|------|
| `data` | ImportRowResponse[] |
| `meta` | `{page, pageSize}` |

`ImportRowResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `import_id` | UUID |
| `row_number` | int |
| `raw` | object? |
| `outcome` | string? |
| `message` | string? |

---

## 25. Attendance

Prefix: `/api/v1/attendance`

### GET `/api/v1/attendance/sessions`

List attendance sessions.

- **Permission:** `attendance.view`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `status` | string? | No |
| `course_id` | UUID? | No |
| `department_id` | UUID? | No |
| `date` | string? | No |

- **Response** (`AttendanceSessionListResponse`):

| Field | Type |
|-------|------|
| `data` | AttendanceSessionResponse[] |
| `meta` | object |

`AttendanceSessionResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `course_id` | UUID |
| `schedule_item_id` | UUID? |
| `lecturer_id` | UUID |
| `date` | string |
| `start_time` | string |
| `end_time` | string |
| `venue_code` | string? |
| `status` | string |
| `opened_at` | datetime? |
| `closed_at` | datetime? |
| `expected_count` | int |
| `present_count` | int |
| `late_count` | int |
| `absent_count` | int |
| `excused_count` | int |
| `rate` | float |

---

### POST `/api/v1/attendance/sessions`

Create attendance session.

- **Permission:** `attendance.record`
- **Request Body** (`AttendanceSessionCreate`):

| Field | Type | Required |
|-------|------|----------|
| `course_id` | UUID | Yes |
| `schedule_item_id` | UUID? | No |
| `date` | string | Yes |
| `start_time` | string | Yes |
| `end_time` | string | Yes |
| `venue_code` | string? | No |

- **Response** (`AttendanceSessionResponse`)
- **Status:** 201 Created

---

### POST `/api/v1/attendance/sessions/{session_id}/open`

Open attendance session for QR check-in.

- **Permission:** `attendance.record`
- **Path Parameters:** `session_id` (UUID)
- **Response** (`AttendanceSessionResponse`)

---

### GET `/api/v1/attendance/sessions/{session_id}/qr`

Get QR token for check-in.

- **Permission:** `attendance.record`
- **Path Parameters:** `session_id` (UUID)
- **Response:** QR token data object

---

### POST `/api/v1/attendance/check-in`

Student QR check-in.

- **Permission:** Authenticated user
- **Query Parameters:** `token` (string, required)
- **Response:** Check-in confirmation

---

### POST `/api/v1/attendance/sessions/{session_id}/close`

Close attendance session.

- **Permission:** `attendance.record`
- **Path Parameters:** `session_id` (UUID)
- **Response** (`AttendanceSessionResponse`)

---

### POST `/api/v1/attendance/records`

Create manual attendance record.

- **Permission:** `attendance.record`
- **Request Body** (`AttendanceRecordCreate`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `session_id` | UUID? | No | |
| `course_id` | UUID? | No | |
| `session_date` | string? | No | |
| `student_id` | UUID | Yes | |
| `status` | string | No | default "Present" |
| `note` | string? | No | |

- **Response** (`AttendanceRecordResponse`):

| Field | Type |
|-------|------|
| `id` | UUID |
| `session_id` | UUID |
| `course_id` | UUID |
| `student_id` | UUID |
| `status` | string |
| `source` | string |
| `recorded_at` | datetime |
| `note` | string? |

- **Status:** 201 Created

---

### POST `/api/v1/attendance/records/bulk`

Bulk create attendance records.

- **Permission:** `attendance.record`
- **Query Parameters:** `session_id` (UUID, required)
- **Request Body:** Array of record objects
- **Response:** Bulk creation result

---

### GET `/api/v1/attendance/records`

List attendance records.

- **Permission:** `attendance.view`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `course_id` | UUID? | No |
| `student_id` | UUID? | No |
| `from_date` | string? | No |
| `to_date` | string? | No |

- **Response:** Attendance records data

---

### PATCH `/api/v1/attendance/records/{record_id}`

Update an attendance record.

- **Permission:** `attendance.manage`
- **Path Parameters:** `record_id` (UUID)
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `record_status` | string? | No |
| `note` | string? | No |

- **Response:** `{"data": {"id": "UUID", "status": "...", "note": "..."}}`

---

### GET `/api/v1/attendance/export`

Export attendance records as CSV.

- **Permission:** `attendance.manage`
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `scope` | string | "department" |
| `department_id` | UUID? | null |
| `course_id` | UUID? | null |

- **Response:** CSV file download

---

## 26. Assessments

Prefix: `/api/v1/assessments`

### GET `/api/v1/assessments`

List assessments.

- **Permission:** `assessments.view`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `status` | string? | No |
| `scope` | string? | No |
| `course_id` | UUID? | No |
| `search` | string? | No |

- **Response** (`AssessmentListResponse`):

| Field | Type |
|-------|------|
| `data` | AssessmentResponse[] |
| `meta` | object |

`AssessmentResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `course_id` | UUID? |
| `course_code` | string |
| `course_title` | string |
| `department_id` | UUID |
| `assessment_type` | string |
| `delivery_mode` | string |
| `date` | string |
| `start_time` | string |
| `end_time` | string |
| `location` | string |
| `venue_code` | string? |
| `cohorts` | object[] |
| `status` | string |
| `scope` | string |
| `is_shared` | boolean |
| `created_by_id` | UUID |
| `created_by_role` | string |
| `review_comment` | string? |
| `reviewed_by_id` | UUID? |
| `reviewed_at` | datetime? |

---

### POST `/api/v1/assessments`

Create assessment.

- **Permission:** `assessments.submit`
- **Query Parameters:** `save_as_draft` (boolean, default false)
- **Request Body** (`AssessmentCreate`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `course_id` | UUID? | No | |
| `course_code` | string | Yes | |
| `course_title` | string | Yes | |
| `department_id` | UUID | Yes | |
| `assessment_type` | string | Yes | |
| `delivery_mode` | string | Yes | |
| `date` | string | Yes | |
| `start_time` | string | Yes | |
| `end_time` | string | Yes | |
| `location` | string | Yes | |
| `venue_code` | string? | No | |
| `cohorts` | object[] | No | default [] |
| `scope` | string | No | default "department" |
| `is_shared` | boolean | No | default false |

- **Response** (`AssessmentResponse`)
- **Status:** 201 Created

---

### GET `/api/v1/assessments/{assessment_id}`

Get assessment by ID.

- **Permission:** `assessments.view`
- **Path Parameters:** `assessment_id` (UUID)
- **Response** (`AssessmentResponse`)

---

### PATCH `/api/v1/assessments/{assessment_id}`

Update assessment.

- **Permission:** `assessments.manage`
- **Path Parameters:** `assessment_id` (UUID)
- **Request Body** (`AssessmentUpdate`): Optional fields (course_id, course_code, course_title, date, start_time, end_time, location, venue_code, cohorts).
- **Response** (`AssessmentResponse`)

---

### POST `/api/v1/assessments/{assessment_id}/submit`

Submit assessment for review.

- **Permission:** `assessments.submit`
- **Path Parameters:** `assessment_id` (UUID)
- **Response** (`AssessmentResponse`)

---

### POST `/api/v1/assessments/{assessment_id}/approve`

Approve assessment.

- **Permission:** `assessments.review`
- **Path Parameters:** `assessment_id` (UUID)
- **Response** (`AssessmentResponse`)

---

### POST `/api/v1/assessments/{assessment_id}/return`

Return assessment with comment.

- **Permission:** `assessments.review`
- **Path Parameters:** `assessment_id` (UUID)
- **Query Parameters:** `comment` (string, required)
- **Response** (`AssessmentResponse`)

---

### POST `/api/v1/assessments/{assessment_id}/cancel`

Cancel assessment.

- **Permission:** `assessments.manage`
- **Path Parameters:** `assessment_id` (UUID)
- **Response** (`AssessmentResponse`)

---

### PUT `/api/v1/assessments/{assessment_id}/invigilators`

Update assessment invigilators.

- **Permission:** `assessments.manage`
- **Path Parameters:** `assessment_id` (UUID)
- **Request Body:** Array of invigilator objects (`List[dict]`)
- **Response:** Updated invigilator data

---

### GET `/api/v1/assessments/export`

Export assessments as CSV.

- **Permission:** `assessments.view`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `status` | string? | No |
| `scope` | string? | No |

- **Response:** CSV file download

---

## 27. Graduation

Prefix: `/api/v1/graduation`

### POST `/api/v1/graduation/submissions`

Create graduation submission (upload CSV of candidates).

- **Permission:** `graduation.submit`
- **Content-Type:** `multipart/form-data`
- **Form Data:**

| Field | Type | Required |
|-------|------|----------|
| `file` | UploadFile (.csv) | Yes |
| `student_category` | string | Yes |
| `academic_year` | string | Yes |
| `programme_id` | UUID? | No |
| `programme_text` | string? | No |
| `declared_count` | int | Yes |

- **Response** (`GraduationSubmissionResponse`):

| Field | Type |
|-------|------|
| `id` | UUID |
| `department_id` | UUID |
| `department_name` | string? |
| `programme_id` | UUID? |
| `programme_text` | string? |
| `student_category` | string |
| `academic_year` | string |
| `declared_count` | int |
| `filename` | string |
| `file_url` | string? |
| `row_count` | int? |
| `status` | GraduationStatus |
| `review_comment` | string? |
| `reviewed_by_id` | UUID? |
| `reviewed_at` | datetime? |
| `created_by_id` | UUID |
| `created_at` | datetime |

- **Status:** 201 Created

---

### GET `/api/v1/graduation/submissions`

List graduation submissions.

- **Permission:** `graduation.view`
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `status` | string? | null |
| `page` | int | 1 |
| `page_size` | int | 25 (max 100) |

- **Response** (`GraduationListResponse`):

| Field | Type |
|-------|------|
| `data` | GraduationSubmissionResponse[] |
| `meta` | `{page, pageSize, counts}` |

---

### GET `/api/v1/graduation/submissions/{submission_id}`

Get submission details with candidates.

- **Permission:** `graduation.view`
- **Path Parameters:** `submission_id` (UUID)
- **Response** (`GraduationSubmissionDetailResponse`):

Extends `GraduationSubmissionResponse` with:

| Field | Type |
|-------|------|
| `candidates` | GraduationCandidateResponse[] |

`GraduationCandidateResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `submission_id` | UUID |
| `student_number` | string |
| `name` | string |
| `programme` | string? |
| `student_id` | UUID? |
| `academic_clearance` | boolean? |
| `financial_clearance` | boolean? |
| `issues` | string[] |

---

### PATCH `/api/v1/graduation/candidates/{candidate_id}`

Update graduation candidate clearance status.

- **Permission:** `graduation.review`
- **Path Parameters:** `candidate_id` (UUID)
- **Request Body** (`GraduationCandidateUpdate`):

| Field | Type | Required |
|-------|------|----------|
| `academic_clearance` | boolean? | No |
| `financial_clearance` | boolean? | No |

- **Response** (`GraduationCandidateResponse`)

---

### POST `/api/v1/graduation/submissions/{submission_id}/validate`

Validate a graduation submission.

- **Permission:** `graduation.review`
- **Path Parameters:** `submission_id` (UUID)
- **Response** (`GraduationSubmissionResponse`)

---

### POST `/api/v1/graduation/submissions/{submission_id}/return`

Return a graduation submission with comment.

- **Permission:** `graduation.review`
- **Path Parameters:** `submission_id` (UUID)
- **Form Data:** `comment` (string, required)
- **Response** (`GraduationSubmissionResponse`)

---

### GET `/api/v1/graduation/export`

Export graduation data as CSV.

- **Permission:** `graduation.view`
- **Response:** CSV file download

---

## 28. Dashboards

Prefix: `/api/v1/dashboard`

### GET `/api/v1/dashboard/super`

Get super admin dashboard metrics.

- **Permission:** `reports.view`
- **Response** (`SuperDashboardResponse`):

| Field | Type |
|-------|------|
| `departments` | int |
| `faculty` | int |
| `assessments` | int |
| `venues` | int |
| `open_slots` | int |
| `free_cells` | int |
| `pending_approvals` | int |
| `open_conflicts` | int |
| `sessions_today` | int |
| `live_sessions` | int |
| `assessments_today` | int |
| `ready_to_publish` | int |
| `departments_not_submitted` | object[] |
| `submission_window_closes_in_days` | int? |
| `next_sessions` | ScheduleItemSummary[] |

---

### GET `/api/v1/dashboard/department`

Get department dashboard metrics.

- **Permission:** `reports.view`
- **Response** (`DepartmentDashboardResponse`):

| Field | Type |
|-------|------|
| `course_offerings` | int |
| `faculty` | int |
| `active_students` | int |
| `schedule_requests` | int |
| `readiness` | ReadinessMetrics? |
| `central_slots_available` | int |
| `submission_window_closes_in_days` | int? |
| `attention` | AttentionItem[] |

---

### GET `/api/v1/dashboard/lecturer`

Get lecturer dashboard metrics.

- **Permission:** Authenticated user (LECTURER or SUPER)
- **Response** (`LecturerDashboardResponse`):

| Field | Type |
|-------|------|
| `classes_today` | int |
| `assigned_courses` | int |
| `students_reached` | int |
| `attendance_rate` | float |
| `attendance_trend` | float[] |
| `today_timeline` | TodayTimelineItem[] |
| `contact_hours` | float |
| `workload_percent` | float |
| `teaching_groups` | int |
| `recent_registers` | RecentRegister[] |
| `attendance_health` | AttendanceHealth? |
| `next_session_starts_in_minutes` | int? |

---

### GET `/api/v1/dashboard/student`

Get student dashboard metrics.

- **Permission:** Authenticated user (STUDENT or SUPER)
- **Response** (`StudentDashboardResponse`):

| Field | Type |
|-------|------|
| `classes_today` | int |
| `registered_courses` | int |
| `assessments_soon` | int |
| `attendance_rate` | float |
| `today` | TodayTimelineItem[] |

---

### GET `/api/v1/badges`

Get notification badges/counts for the current user.

- **Permission:** Authenticated user
- **Response** (`BadgesResponse`):

| Field | Type |
|-------|------|
| `approvals` | int |
| `conflict_centre` | int |
| `schedule_requests` | int |

---

## 29. Reports

Prefix: `/api/v1/reports`

### POST `/api/v1/reports`

Generate a report.

- **Permission:** `reports.generate`
- **Request Body** (`ReportCreate`):

| Field | Type | Required |
|-------|------|----------|
| `report_type` | string | Yes |
| `academic_year` | string? | No |
| `semester` | string? | No |
| `programme_id` | UUID? | No |
| `student_category` | string? | No |
| `date_from` | datetime? | No |
| `date_to` | datetime? | No |
| `format` | string | No (default "csv") |
| `department_id` | UUID? | No |

- **Response** (`ReportResponse`):

| Field | Type |
|-------|------|
| `id` | UUID |
| `report_type` | string |
| `academic_year` | string? |
| `semester` | string? |
| `status` | string |
| `file_url` | string? |
| `row_count` | int? |
| `created_at` | datetime? |

- **Status:** 201 Created

---

### GET `/api/v1/reports`

List reports.

- **Permission:** `reports.view`
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `page` | int | 1 |
| `page_size` | int | 25 (max 100) |

- **Response** (`ReportListResponse`):

| Field | Type |
|-------|------|
| `data` | ReportResponse[] |
| `meta` | `{page, page_size}` |

---

### GET `/api/v1/reports/{report_id}/download`

Download report as CSV.

- **Permission:** `reports.view`
- **Path Parameters:** `report_id` (UUID)
- **Response:** CSV file download

---

## 30. Audit

Prefix: `/api/v1/audit`

### GET `/api/v1/audit`

List audit logs.

- **Permission:** `audit.view`
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `category` | string? | null |
| `actor_id` | UUID? | null |
| `entity_type` | string? | null |
| `from_date` | datetime? | null |
| `to_date` | datetime? | null |
| `search` | string? | null |
| `page` | int | 1 |
| `page_size` | int | 25 (max 100) |

- **Response** (`AuditLogListResponse`):

| Field | Type |
|-------|------|
| `data` | AuditLogResponse[] |
| `meta` | `{page, pageSize, total, counts}` |

`AuditLogResponse`:

| Field | Type |
|-------|------|
| `id` | UUID |
| `user_id` | UUID |
| `actor_name` | string |
| `actor_role` | string |
| `action` | string |
| `category` | string |
| `entity_type` | string? |
| `entity_id` | UUID? |
| `department_id` | UUID? |
| `summary` | string |
| `before` | object? |
| `after` | object? |
| `reason` | string? |
| `ip_address` | string? |
| `user_agent` | string? |
| `revision` | int? |
| `created_at` | datetime? |

---

### GET `/api/v1/audit/export`

Export audit logs as CSV.

- **Permission:** `audit.view`
- **Query Parameters:**

| Param | Type | Required |
|-------|------|----------|
| `category` | string? | No |
| `from_date` | datetime? | No |
| `to_date` | datetime? | No |

- **Response:** CSV file download

---

## 31. Notifications

Prefix: `/api/v1/notifications`

### GET `/api/v1/notifications`

Get user notifications.

- **Permission:** Authenticated user
- **Query Parameters:**

| Param | Type | Default |
|-------|------|---------|
| `unread_only` | boolean | false |

- **Response** (`NotificationResponse[]`):

| Field | Type |
|-------|------|
| `id` | UUID |
| `recipient_id` | UUID? |
| `title` | string |
| `detail` | string |
| `page` | string? |
| `category` | NotificationCategory |
| `priority` | NotificationPriority |
| `audience_role` | string? |
| `audience_department_id` | UUID? |
| `entity_type` | string? |
| `entity_id` | UUID? |
| `created_at` | datetime |
| `is_read` | boolean |
| `read_at` | datetime? |

---

### GET `/api/v1/notifications/unread-count`

Get unread notification count.

- **Permission:** Authenticated user
- **Response:** `{"unread_count": int}`

---

### POST `/api/v1/notifications/mark-read`

Mark specific notifications as read.

- **Permission:** Authenticated user
- **Request Body** (`NotificationMarkRead`):

| Field | Type | Required |
|-------|------|----------|
| `notification_ids` | UUID[] | Yes |

- **Status:** 204 No Content

---

### POST `/api/v1/notifications/mark-all-read`

Mark all notifications as read.

- **Permission:** Authenticated user
- **Status:** 204 No Content

---

## 32. Settings

Prefix: `/api/v1/settings`

### GET `/api/v1/settings/institution`

Get institution-wide settings.

- **Permission:** `settings.institution`
- **Response** (`InstitutionSettingsResponse`):

| Field | Type | Default |
|-------|------|---------|
| `id` | UUID | |
| `organisation_name` | string | |
| `support_email` | string | |
| `office_location` | string? | |
| `timezone` | string | "Africa/Accra" |
| `active_semester_id` | UUID? | |
| `teaching_start` | string | "08:00" |
| `teaching_end` | string | "18:00" |
| `default_class_duration` | int | 60 |
| `capacity_tolerance` | int | 0 |
| `allow_weekends` | boolean | false |
| `require_conflict_approval` | boolean | false |
| `auto_publish_approved` | boolean | false |
| `require_graduation_approval` | boolean | false |
| `require_academic_clearance` | boolean | false |
| `require_financial_clearance` | boolean | false |
| `notify_schedule_changes` | boolean | true |
| `notify_graduation_submissions` | boolean | true |
| `notify_conflicts` | boolean | true |
| `email_channel` | boolean | true |
| `in_app_channel` | boolean | true |
| `require_admin_two_factor` | boolean | false |
| `session_timeout` | int | 30 |
| `audit_retention` | string | "1 year" |
| `created_at` | datetime? | |
| `updated_at` | datetime? | |

---

### PUT `/api/v1/settings/institution`

Update institution-wide settings.

- **Permission:** `settings.institution`
- **Request Body** (`InstitutionSettingsUpdate`): All fields optional (same fields as response).
- **Response** (`InstitutionSettingsResponse`)

---

### GET `/api/v1/settings/department`

Get department-specific settings.

- **Permission:** `settings.department`
- **Query Parameters:**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `department_id` | UUID? | No | Super admins can specify any; others use their own |

- **Response** (`DepartmentSettingsResponse`):

| Field | Type |
|-------|------|
| `id` | UUID |
| `department_id` | UUID |
| `department_name` | string |
| `department_code` | string |
| `support_email` | string? |
| `office_location` | string? |
| `timezone` | string? |
| `teaching_start` | string? |
| `teaching_end` | string? |
| `default_class_duration` | int? |
| `capacity_tolerance` | int? |
| `allow_weekends` | boolean? |
| `require_conflict_approval` | boolean? |
| `auto_publish_approved` | boolean? |
| `notify_schedule_changes` | boolean? |
| `notify_graduation_submissions` | boolean? |
| `notify_conflicts` | boolean? |
| `email_channel` | boolean? |
| `in_app_channel` | boolean? |
| `created_at` | datetime? |
| `updated_at` | datetime? |

---

### PUT `/api/v1/settings/department`

Update department-specific settings.

- **Permission:** `settings.department`
- **Query Parameters:** `department_id` (UUID?, optional for super admins)
- **Request Body** (`DepartmentSettingsUpdate`): All fields optional.
- **Response** (`DepartmentSettingsResponse`)

---

## 33. Reference Data

Prefix: `/api/v1/reference`

### GET `/api/v1/reference`

Get static reference data for the application (weekdays, periods, levels, semesters).

- **Permission:** Authenticated user
- **Response:**

```json
{
  "data": {
    "weekdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "periods": [
      {"index": 0, "start": "07:30", "end": "08:20", "label": "7:30 - 8:20"},
      ...
    ],
    "levels": [100, 200, 300, 400],
    "currentSemesterId": "UUID?",
    "semesters": [
      {
        "id": "UUID",
        "academicYear": "string",
        "number": "int",
        "label": "string",
        "startDate": "ISO date?",
        "endDate": "ISO date?",
        "registrationDeadline": "ISO date?",
        "graduationDeadline": "ISO date?",
        "isActive": "boolean"
      }
    ]
  }
}
```

---

## 34. Demo

Prefix: `/api/v1/admin/demo`

### POST `/api/v1/admin/demo/reset`

Reset demo workspace. Only available when `DEMO_MODE=true` in server config. Truncates all data tables.

- **Permission:** `settings.manage`
- **Response:** `{"data": {"message": "Demo workspace has been reset successfully"}}`

---

## Appendix: Permission Codes Reference

| Code | Description |
|------|-------------|
| `users.manage` | Manage user accounts (admin) |
| `roles.manage` | Manage roles and permissions |
| `departments.view` | View departments |
| `departments.manage` | Create/update/delete departments |
| `programmes.view` | View programmes |
| `programmes.manage` | Create/update/delete programmes |
| `courses.view` | View courses |
| `courses.manage` | Create/update/delete courses |
| `venues.view` | View venues |
| `venues.manage` | Create/update/delete venues |
| `timetable.view` | View master timetables |
| `timetable.upload` | Upload master timetables |
| `timetable.department_upload` | Upload department timetables |
| `timetable.edit` | Edit master timetable entries |
| `schedule.view` | View schedule items and slot requests |
| `schedule.request` | Submit slot requests |
| `schedule.withdraw` | Withdraw slot requests |
| `schedule.approve` | Approve/return slot requests |
| `schedule.manage` | Manage schedule items |
| `conflicts.view` | View conflict centre |
| `conflicts.override` | Override conflicts |
| `staff.view` | View faculty members |
| `staff.manage` | Manage faculty members |
| `students.view` | View students |
| `students.manage` | Manage students and sections |
| `registration.self` | Self-service course registration |
| `imports.view` | View import history |
| `imports.manage` | Import student/roster data |
| `attendance.view` | View attendance records |
| `attendance.record` | Record attendance |
| `attendance.manage` | Manage/update attendance records |
| `assessments.view` | View assessments |
| `assessments.submit` | Submit assessments |
| `assessments.review` | Review/approve assessments |
| `assessments.manage` | Manage assessments |
| `graduation.view` | View graduation submissions |
| `graduation.submit` | Submit graduation data |
| `graduation.review` | Review graduation submissions |
| `reports.view` | View dashboards and reports |
| `reports.generate` | Generate reports |
| `audit.view` | View audit logs |
| `settings.institution` | Manage institution settings/semesters |
| `settings.department` | Manage department settings |
| `settings.manage` | Manage system settings (demo, etc.) |
