# SPMS Academic Hub — Backend Build Brief (for the implementing agent)

Written for: the agent who will build the backend for this React frontend.

## Context

The frontend in this repo is a complete university scheduling and academic-operations portal for the
School of Physical and Mathematical Sciences (SPMS), University of Ghana. Everything currently runs on
zustand stores persisted to `localStorage` (`ug-hub.*` keys) with mock data. Many screens show
hard-coded numbers, several workflows only create placeholder "records", and no rule is enforced
server-side. Your job is to build the backend that makes every screen real, so the frontend can swap
each store action for an API call.

Read these frontend files before you start; they are the source of truth for shapes and rules:

- `src/types/*.ts` — every current entity shape
- `src/stores/*.ts` — every current mutation (each becomes an endpoint)
- `src/lib/scheduling/conflicts.ts` — clash engine (port it verbatim to the server)
- `src/lib/timetable/parse.ts`, `grid.ts`, `venues.ts` — master timetable parsing, FREE-cell logic, venue capacities
- `src/app/portal-routes.tsx` — every page of every portal
- `src/stores/fixtures/*` and `src/lib/timetable/master-2026-27-s1.csv` — seed data

You choose the stack, database, hosting, file storage and email provider. Pick whatever you build
fastest and most reliably with. A relational database is the natural fit because the data is
heavily relational (departments → programmes → courses → cohorts → requests → classes).

---

## 1. Problems this system solves

1. **One master timetable for the whole school.** Academic Affairs publishes a master timetable per
   level (100–400) per semester. Every teaching cell is a (day, period, venue) with a subject or `FREE`.
2. **Fair allocation of FREE slots.** Departments compete for FREE cells. They submit slot requests,
   central administration approves or returns them, and approving one automatically returns competing
   requests for the same venue and time.
3. **Clash prevention.** Before a class is approved the system detects: venue already taken, slot not
   FREE, course offered at a different level, the same student cohort booked twice, the same lecturer
   booked twice, and venue too small.
4. **Published timetables for everyone.** Approved classes become the department's final timetable,
   each lecturer's teaching timetable and each student's personal timetable.
5. **Academic structure management.** Departments, programmes (with levels), courses, and the
   programme-level cohorts that take each course, including cross-department courses.
6. **People and access.** Super admins, department admins, lecturers and students, with onboarding
   via account generation, invitations, bulk CSV imports and self-registration.
7. **Assessment scheduling.** Lecturers and departments submit tests and exams, central admin
   schedules them, reviewers approve or return them, students see the published schedule.
8. **Attendance.** Lecturers run class sessions and record attendance (manual or QR); students see
   their history; admins monitor live, completed and missed sessions.
9. **Course registration and rosters.** Students register for courses; lecturers see and upload rosters.
10. **Graduation data.** Departments upload graduand lists; central admin validates or returns them.
11. **Oversight.** Notifications, dashboards with real metrics, reports, CSV exports, audit trail,
    institution and department settings.

---

## 2. Roles (user types) and what each can do

| Role key     | Portal                           | Scope                                                | Can do                                                                                                                                                                                                                                                                                                                   |
| ------------ | -------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `super`      | Super Admin `/super/*`           | Whole institution                                    | Everything: settings, calendar, venues, departments (+ their accounts), staff & roles, master timetable upload/edit, approve/return slot requests, conflict centre, assessments (create as Upcoming, review), attendance monitoring, graduation review, reports, audit trail                                             |
| `department` | Department Admin `/department/*` | One department (`departmentId`)                      | Programmes & courses CRUD, faculty invites, student imports, request FREE slots, withdraw pending requests, manage department class slots, final timetable, department assessments (create as Submitted, review lecturer submissions), department attendance, graduation upload, department reports, department settings |
| `lecturer`   | Faculty `/lecturer/*`            | Own courses (`course.lecturerId`) and own department | View own timetable, own courses, own students/rosters (+ roster upload), submit assessments, run attendance sessions and record attendance                                                                                                                                                                               |
| `student`    | Student `/student/*`             | Own record (`programmeId`, `level`)                  | View own timetable, register courses, view published assessments, view own attendance                                                                                                                                                                                                                                    |

All roles: login, logout, password reset, change password, profile, photo, 2FA, sessions,
notifications, notification preferences.

**Scoping is enforced on the server for every query and mutation.** The frontend today leaks data
(lecturers see every attendance record, students see every registration, anyone with a review
dialog can approve). The backend must filter by scope and reject out-of-scope writes with `403`.

---

## 3. API conventions (make these uniform so the frontend is easy to wire)

- Base path `/api/v1`. JSON everywhere except file upload (`multipart/form-data`) and file download.
- Field names in **camelCase**, matching `src/types`. Dates `YYYY-MM-DD`, times `HH:MM` (24h,
  zero-padded), timestamps ISO-8601 UTC.
- IDs are opaque strings (UUID). Return `id` on every entity.
- **Success:** `{ "data": <entity | entity[]>, "meta"?: { "page", "pageSize", "total" } }`.
- **Error:** `{ "error": { "code": "VALIDATION_ERROR" | "UNAUTHORIZED" | "FORBIDDEN" | "NOT_FOUND" | "CONFLICT" | "CLASH_BLOCKED", "message": "<human sentence>", "fields"?: { "<field>": "<message>" }, "details"?: any } }`.
  Reuse the exact human messages the frontend already shows (listed per feature below).
- HTTP status: 200 read/update, 201 create, 204 delete, 400 validation, 401 not signed in,
  403 out of scope, 404 missing, 409 duplicate/state conflict, 422 business rule blocked.
- **Lists:** `?page=1&pageSize=25&search=&sort=field&order=asc|desc` plus per-resource filters.
  Every list that the UI shows with tabs returns tab counts in `meta.counts` (e.g.
  `{ "Pending": 3, "Approved": 5, "Returned": 1, "All": 9 }`) so the UI does not compute them.
- **Exports:** `GET .../export?format=csv` returns `text/csv` with `Content-Disposition` filename.
- **Auth:** short-lived access token (Bearer) + rotating refresh token (httpOnly cookie or body).
  `GET /auth/me` returns the current user, which replaces `useAuthStore.user`.
- Every mutation writes an **audit log** entry and may emit **notifications** (sections 6.15, 6.16).
- Provide an OpenAPI document at `/api/v1/docs` generated from the code.

---

## 4. Fixed academic constants (expose via `GET /reference`)

Return one payload the frontend loads once:

- `weekdays`: `["Monday","Tuesday","Wednesday","Thursday","Friday"]` (index 0–4; add Sat/Sun as 5–6 when `allowWeekends` is on).
- `periods`: 12 periods, index 0–11, `start = (7+i):30`, `end = (8+i):20`, label `"7:30 – 8:20"`.
  e.g. `{ "index": 0, "start": "07:30", "end": "08:20", "label": "7:30 – 8:20" }` … `{ 11, "18:30", "19:20" }`.
- `levels`: `[100, 200, 300, 400]`.
- `semesters`: from the Semester table (label format `"2026/27 · Semester 1"`), plus `currentSemesterId`.
- Enums used in forms (section 5). Keep the period grid configurable in Settings but default to the above.

---

## 5. Entities, properties and enums

Every entity also has `createdAt`, `updatedAt`, and where noted `createdById`.

### 5.1 User

| field            | type                                                                                               | notes                                                                                                |
| ---------------- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| id               | string                                                                                             |                                                                                                      |
| email            | string, unique, lowercase                                                                          | login identifier                                                                                     |
| passwordHash     | string                                                                                             | never returned                                                                                       |
| role             | `"super" \| "department" \| "lecturer" \| "student"`                                               |                                                                                                      |
| name             | string                                                                                             |                                                                                                      |
| status           | `"invited" \| "active" \| "disabled"`                                                              | invited = has not set a password yet                                                                 |
| departmentId     | string?                                                                                            | required for `department` and `lecturer`                                                             |
| programmeId      | string?                                                                                            | required for `student`                                                                               |
| level            | number?                                                                                            | student level 100–400 (or 500+ for postgraduate)                                                     |
| studentCategory  | `"Undergraduate" \| "Postgraduate"`?                                                               | students                                                                                             |
| studentNumber    | string?, unique                                                                                    | e.g. `STU/CS/2024/0184`                                                                              |
| staffId          | string?, unique                                                                                    | e.g. `UG-SPMS-0142`                                                                                  |
| rank             | `"Professor" \| "Associate Professor" \| "Senior Lecturer" \| "Lecturer" \| "Assistant Lecturer"`? | staff                                                                                                |
| title            | string?                                                                                            | display title, e.g. "Department Administrator", "Level 300 Student" (derive for students from level) |
| phone, office    | string?                                                                                            |                                                                                                      |
| photoUrl         | string?                                                                                            | uploaded image URL                                                                                   |
| twoFactorEnabled | boolean                                                                                            |                                                                                                      |
| twoFactorSecret  | string?                                                                                            | never returned                                                                                       |
| roleTemplateId   | string?                                                                                            | admins (section 5.17)                                                                                |
| lastLoginAt      | timestamp?                                                                                         |                                                                                                      |

Computed in responses: `scope` (string) for backward compatibility with the UI —
department name for department/lecturer, programme name for student, `"Central administration"` for super.

### 5.2 NotificationPreferences (1:1 with User)

`scheduleNotifications`, `assessmentNotifications`, `attendanceNotifications`,
`graduationNotifications` (default true for super/department, false otherwise),
`emailNotifications`, `inAppNotifications` — all boolean, default true unless stated.

### 5.3 Session / tokens

- `Session { id, userId, userAgent, ipAddress, location?, createdAt, lastSeenAt, revokedAt? }`
- `PasswordResetToken { id, userId, tokenHash, expiresAt, usedAt? }`
- `Invitation { id, userId, tokenHash, expiresAt, acceptedAt?, sentAt }`

### 5.4 Department

`{ id, name (unique), code (unique, uppercase, e.g. "DCIT"), school (default "SPMS"), email, phone?, tone }`

- `tone` is the timetable colour: `"blue" | "violet" | "amber" | "green" | "rose"`. Seed: DCIT blue, MATH green, STAT violet, PHYS amber, CHEM rose, EASC amber.
- `subjectPrefixes: string[]` — subject codes in the master timetable that belong to this department (DCIT → `["DCIT","CSIT"]`; others → `[code]`).

### 5.5 Programme

`{ id, code (e.g. "BSc CS"), name (e.g. "BSc Computer Science"), departmentId, levels: number[], category: "Undergraduate" | "Postgraduate" }`

### 5.6 Course and CourseCohort

Course: `{ id, code (unique, uppercase, no spaces, e.g. "DCIT101"), title, departmentId, type: "Core" | "Elective", creditHours (1–6), mode: "online" | "in-person" | "hybrid" (default in-person), studentCount (≥1), lecturerId? }`
CourseCohort: `{ courseId, programmeId, level }` — composite key. Programmes may belong to other departments.
Response shape includes `cohorts: [{ programmeId, level }]` and `lecturer: { id, name, email } | null`.
Cohort key `"{programmeId}|{level}"`, label `"{programme.code} L{level}"`.

### 5.7 Semester (academic calendar)

`{ id, academicYear ("2026/27"), number (1|2), label ("2026/27 · Semester 1"), startDate, endDate, teachingStart?, teachingEnd?, registrationDeadline, graduationDeadline, isActive }`
Exactly one semester has `isActive = true`. Seed 2026/27 S1 (12 Aug – 19 Dec 2026, registration 28 Aug 2026, graduation 30 May 2027) and S2.

### 5.8 Venue

`{ id, code (normalised, unique, e.g. "JQB09", "GCB FF R1"), building, roomNumber, location, gpsAddress?, latitude?, longitude?, capacity?, type: "lecture_hall" | "laboratory" | "seminar_room" | "online" | "shared", isShared (true for "DEPT", "ONLINE"), status: "available" | "unavailable", unavailableReason?, unavailableUntil? }`
Seed from `src/lib/timetable/venues.ts` (≈45 venues with capacity, e.g. CC 600, NNB1 500, E10 120, LSR 40).
Venues referenced by an uploaded master timetable that do not exist are **auto-created** with
`capacity = null` and returned in the upload preview as warnings.

### 5.9 MasterTimetable, MasterEntry, TimetableUpload

- MasterTimetable: `{ id, semesterId, level, filename, uploadedById, uploadedAt, version }` — unique on (semesterId, level). Publishing replaces entries and increments `version`.
- MasterEntry: `{ id, timetableId, level, day (0–4), period (0–11), subject (normalised), venueCode, isFree (subject === "FREE"), departmentId? (resolved from subject prefix), courseKind: "C" | "E" | null }`
- TimetableUpload (history): `{ id, semesterId, level, filename, uploadedById, uploadedAt, entryCount, kind: "master" | "department", departmentId? }`

### 5.10 SlotRequest

`{ id, courseId, departmentId, requestedById, semesterId, level, day, venueCode, startPeriod, periodCount (1–3), status: "Pending" | "Approved" | "Returned" | "Withdrawn", reviewComment?, reviewedById?, reviewedAt?, scheduleItemId? }`
Computed in responses: `course` summary, `department` summary, `slotLabel` ("Mon 07:30–09:20"),
`clashes: Clash[]` (computed live, section 7.2), `competing: SlotRequest[]` (pending, same venue, overlapping).

### 5.11 ScheduleItem (a class on the timetable)

`{ id, semesterId, courseId, departmentId, slotRequestId?, day, startPeriod?, periodCount?, start ("HH:MM"), end ("HH:MM"), venueCode, lecturerId?, mode, groups: [{ programmeId, level, section? }], status: "pending" | "conflict" | "published", source: "request" | "manual" | "department-upload" }`
Computed in responses (for backward compatibility): `course` (code), `title`, `room`, `lecturer` (name or "Lecturer to be assigned"), `department` (name), `tone`, `groups` as strings `"{Programme name} · Level {n}"`.

### 5.12 Assessment

`{ id, courseId?, courseCode, courseTitle, departmentId, assessmentType: "Interim Assessment (IA)" | "Quiz" | "Mid-semester examination" | "Final examination" | "Practical assessment" | "Project presentation", deliveryMode: "In-person" | "Online" | "Hybrid", date, startTime, endTime, location (venue code or online link), venueCode?, cohorts: [{programmeId, level}], status: "Draft" | "Submitted" | "Upcoming" | "Shared" | "Returned" | "Cancelled", scope: "central" | "department" | "faculty", isShared (multi-department), createdById, createdByRole, reviewComment?, reviewedById?, reviewedAt? }`
AssessmentInvigilator: `{ assessmentId, userId, role: "chief" | "assistant" }`.

### 5.13 Attendance

- AttendanceSession: `{ id, courseId, scheduleItemId?, lecturerId, date, startTime, endTime, venueCode?, status: "scheduled" | "live" | "completed" | "missed", openedAt?, closedAt?, qrSecret (never returned), qrRotationSeconds (30), expectedCount }`
- AttendanceRecord: `{ id, sessionId, courseId, studentId, status: "Present" | "Late" | "Absent" | "Excused", source: "Manual entry" | "QR scan", recordedById, recordedAt, note? }` — unique on (sessionId, studentId); a second write updates the record.
  Computed: per-session `presentCount`, `lateCount`, `absentCount`, `excusedCount`, `rate = (present + late) / expected`.

### 5.14 CourseRegistration

`{ id, studentId, courseId?, customCourseCode?, customCourseTitle?, semesterId, level, registrationType: "Core" | "Elective" | "Research / Project" | "Lab / Practical", credits (1|2|3|6), status: "Registered" | "Dropped" | "Pending approval", source: "self" | "roster-import" }`
UI tab mapping: `Elective` → "Electives", everything else → "Required".

### 5.15 Imports (student onboarding and course rosters)

StudentImport: `{ id, kind: "student-onboarding" | "course-roster", departmentId, courseId?, programmeId?, programmeText?, levelText?, studentCategory, academicYear, semesterId?, filename, fileUrl, rowCount, createdCount, updatedCount, warningCount, errorCount, status: "Queued" | "Processing" | "Completed" | "Failed", createdById }`
StudentImportRow: `{ importId, rowNumber, raw: object, outcome: "created" | "updated" | "skipped", message? }`

### 5.16 Graduation

- GraduationSubmission: `{ id, departmentId, programmeId?, programmeText, studentCategory, academicYear, declaredCount, filename, fileUrl, rowCount, status: "Submitted" | "Validated" | "Returned", reviewComment?, reviewedById?, reviewedAt?, createdById }`
  (Use `Validated` as the approved state; the UI tabs already say "Validated".)
- GraduationCandidate: `{ submissionId, studentNumber, name, programme, studentId?, academicClearance: boolean | null, financialClearance: boolean | null, issues: string[] }`

### 5.17 RoleTemplate (permissions)

`{ id, name ("Department Administrator"), role, permissions: string[] }` — permission keys:
`schedule.manage, schedule.approve, timetable.upload, staff.manage, students.manage, courses.manage, attendance.manage, assessments.manage, assessments.review, graduation.submit, graduation.review, reports.view, audit.view, settings.manage, venues.manage, departments.manage`.
Seed one template per role with the abilities in section 2.

### 5.18 Section / StudentGroup

`{ id, programmeId, level, name ("Lab Group A"), courseId?, studentIds: string[] }` — used by the "Students & groups → Sections/Cohorts" tabs and by schedule `groups`.

### 5.19 Notification and NotificationRead

Notification: `{ id, title, detail, page (portal page label, e.g. "Approvals"), audienceRole?: Role, audienceDepartmentId?, recipientId?, category: "schedule" | "assessment" | "attendance" | "graduation" | "general", entityType?, entityId? }`
NotificationRead: `{ notificationId, userId, readAt }`.
Visibility: shown to a user if `recipientId = user.id`, else if `audienceRole = user.role` (and `audienceDepartmentId` is null or equals the user's department), else if both are null (broadcast).

### 5.20 AuditLog

`{ id, actorId, actorName, actorRole, action (e.g. "slot_request.approved"), category: "Scheduling" | "Approvals" | "Overrides" | "Academics" | "People" | "Assessments" | "Attendance" | "Graduation" | "Settings" | "Auth", entityType, entityId, departmentId?, summary (human sentence), before?: json, after?: json, reason?, ipAddress, userAgent, revision?, createdAt }` — append-only.

### 5.21 Settings

- InstitutionSettings (singleton): `organisationName, supportEmail, officeLocation, timezone ("Africa/Accra"), activeSemesterId, teachingStart ("08:00"), teachingEnd ("18:00"), defaultClassDuration (60|90|120|180), capacityTolerance (0|5|10 %), allowWeekends, requireConflictApproval, autoPublishApproved, requireGraduationApproval, requireAcademicClearance, requireFinancialClearance, notifyScheduleChanges, notifyGraduationSubmissions, notifyConflicts, emailChannel, inAppChannel, requireAdminTwoFactor, sessionTimeout (15|30|60 min), auditRetention ("1 year"|"3 years"|"7 years")`.
- DepartmentSettings (one per department): `departmentId, departmentName, departmentCode, supportEmail, officeLocation, timezone, teachingStart, teachingEnd, defaultClassDuration, capacityTolerance, allowWeekends, requireConflictApproval, autoPublishApproved, notifyScheduleChanges, notifyGraduationSubmissions, notifyConflicts, emailChannel, inAppChannel`.
- Semester dates (`semesterStart`, `semesterEnd`, `registrationDeadline`, `graduationDeadline`) live on the Semester entity; the settings endpoint returns and accepts them for the active semester so the existing form keeps working.

### 5.22 ReportJob

`{ id, reportType, academicYear, semester ("Semester 1"|"Semester 2"|"Full academic year"), programmeId?, studentCategory?, dateFrom, dateTo, format: "csv", departmentId?, status: "Ready" | "Failed", fileUrl, rowCount, createdById }`

---

## 6. Features and endpoints, module by module

Each endpoint lists who may call it. "Dept-scoped" means a department admin only sees and changes rows of their own department.

### 6.1 Auth and onboarding

| Method | Path                      | Who    | Behaviour                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | ------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| POST   | `/auth/login`             | public | Body `{ email, password, otp? }`. Lowercase+trim email. Wrong email/password → 401 `"Invalid email or password."`. Disabled user → 403. If `twoFactorEnabled` (or `requireAdminTwoFactor` for super/department) and no `otp` → 200 `{ data: { twoFactorRequired: true, challengeId } }`. Success → `{ user, accessToken }` + refresh token; create Session; set `lastLoginAt`. |
| POST   | `/auth/login/2fa`         | public | `{ challengeId, otp }` → tokens.                                                                                                                                                                                                                                                                                                                                               |
| POST   | `/auth/refresh`           | public | rotate refresh token.                                                                                                                                                                                                                                                                                                                                                          |
| POST   | `/auth/logout`            | any    | revoke current session.                                                                                                                                                                                                                                                                                                                                                        |
| GET    | `/auth/me`                | any    | current user + preferences + department/programme summaries + `permissions`.                                                                                                                                                                                                                                                                                                   |
| POST   | `/auth/register`          | public | Student self-registration. Body `{ email, password (≥6), name, studentNumber, programmeId, level }`. Missing field → 400 `"Complete all required registration fields."`. Duplicate → 409 `"An account with this email already exists."`. Creates active student. Optional institution-domain check on email.                                                                   |
| POST   | `/auth/forgot-password`   | public | `{ email }` → always 200; emails a reset link (token valid 1 h). Frontend route `/reset-password?token=`.                                                                                                                                                                                                                                                                      |
| POST   | `/auth/reset-password`    | public | `{ token, newPassword }` (≥8).                                                                                                                                                                                                                                                                                                                                                 |
| POST   | `/auth/accept-invitation` | public | `{ token, password, name? }` → status `active`, returns tokens.                                                                                                                                                                                                                                                                                                                |
| GET    | `/auth/invitation/:token` | public | returns invitee email, name, role for the activation screen.                                                                                                                                                                                                                                                                                                                   |

Session timeout: access token lifetime and idle revocation follow `sessionTimeout`.

### 6.2 Profile, security, preferences (all roles)

| Method    | Path                                                                                                                          | Behaviour                                                                                                                                                                                           |
| --------- | ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET/PATCH | `/me/profile`                                                                                                                 | `{ name, phone, office }`. Changing email goes through `POST /me/email-change` (sends confirmation to the new address; login changes on confirm).                                                   |
| POST      | `/me/photo`                                                                                                                   | multipart image (png/jpeg/webp, ≤2 MB) → `photoUrl`. DELETE removes it.                                                                                                                             |
| POST      | `/me/password`                                                                                                                | `{ currentPassword, newPassword, confirmPassword }`. Wrong current → 400 `fields.currentPassword`. Mismatch → 400 `fields.confirmPassword "Passwords do not match."`. Min 8. Revoke other sessions. |
| POST      | `/me/2fa/setup` → `{ otpauthUrl, qrDataUrl }`; POST `/me/2fa/enable` `{ otp }`; POST `/me/2fa/disable` `{ otp or password }`. |
| GET       | `/me/sessions`; DELETE `/me/sessions/:id`; POST `/me/sessions/revoke-others`.                                                 |
| GET/PUT   | `/me/notification-preferences`                                                                                                | section 5.2 fields.                                                                                                                                                                                 |

Account ID shown on the profile = `studentNumber` for students, `staffId` otherwise.

### 6.3 Settings (super, department)

- `GET/PUT /settings/institution` (super). PUT replaces all fields; validates semesterStart < semesterEnd, teachingStart < teachingEnd, dates within the semester.
- `GET/PUT /settings/department` (department; uses caller's department; super may pass `?departmentId=`).
- Settings must **take effect**: `allowWeekends` extends weekdays; `capacityTolerance` relaxes the capacity clash (capacity × (1 + tolerance%)); `autoPublishApproved` publishes department-created class slots without a manual publish step; `requireConflictApproval` blocks publishing a class with any danger clash unless super overrides; graduation toggles drive validation (6.12); notification toggles gate notification emission; `requireAdminTwoFactor` forces 2FA at login for super/department; `auditRetention` drives a nightly purge job.

### 6.4 Academic calendar

- `GET /semesters`, `POST /semesters` (super), `PATCH /semesters/:id`, `POST /semesters/:id/activate` (sets the only active semester).

### 6.5 Departments (super)

| Method | Path                                 | Behaviour                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------ | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| GET    | `/departments`                       | `?search=` on name/code. Each row: `{ id, name, code, school, email, phone, tone, counts: { programmes, courses, lecturers, students }, adminAccount: { id, email, status } }`.                                                                                                                                                                                                                                                                                                                                                                                                        |
| POST   | `/departments`                       | Body `{ name, code, email, phone? }`. Missing → 400 `"Please fill in department name, code and email."`. Code uppercased. Duplicate code/name/email → 409. In one transaction: create Department, create its DepartmentSettings with defaults, create a `department` role User (`email`, `name` = department name, `departmentId`, status `invited`) and send an invitation email. **Do not use the `{CODE}#123` password and never return a password.** Optional admin flag `generateTemporaryPassword: true` returns a one-time random password once, forcing change at first login. |
| GET    | `/departments/:id`                   | details + tabs: `programmes`, `courses`, `lecturers`, `students`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| PATCH  | `/departments/:id`                   | name, code, email, phone, tone, subjectPrefixes.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| DELETE | `/departments/:id`                   | Cascade: delete its programmes (and cohort links pointing to them), **delete its courses**, disable its department admin account, and either reassign or disable its lecturers (query `?lecturers=disable                                                                                                                                                                                                                                                                                                                                                                              | keep`). Refuse with 409 if it has Approved slot requests in the active semester unless `?force=true`. |
| POST   | `/departments/:id/resend-invitation` |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

### 6.6 Programmes & courses (department, dept-scoped; super sees all)

| Method     | Path                             | Behaviour                                                                                                                                                                                                                                                                                                                                                                                         |
| ---------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET        | `/programmes`                    | `?departmentId=` (department admins default to own). Include `linkedCourseCount` (across all departments).                                                                                                                                                                                                                                                                                        |
| POST/PATCH | `/programmes`, `/programmes/:id` | `{ name, code, levels[], category }`. Errors: "Programme name is required", "Short code is required", "Select at least one level."                                                                                                                                                                                                                                                                |
| DELETE     | `/programmes/:id`                | removes cohort links in every course; refuse if students are enrolled unless `?force=true`.                                                                                                                                                                                                                                                                                                       |
| GET        | `/courses`                       | `?departmentId=&lecturerId=&programmeId=&level=&search=`; returns `cohorts`, `lecturer`; `meta.counts.withoutLecturer`.                                                                                                                                                                                                                                                                           |
| POST/PATCH | `/courses`, `/courses/:id`       | `{ code, title, type, mode, creditHours, studentCount, lecturerId?, cohorts: [{programmeId, level}] }`. Code normalised (uppercase, whitespace removed), unique across all departments → 409 `"{CODE} already exists."`. At least one cohort → `"Select at least one programme that takes this course."`. Each cohort level must be in that programme's `levels`. Lecturer must be role lecturer. |
| DELETE     | `/courses/:id`                   | refuse with 409 if it has Approved slot requests or published schedule items in the active semester, unless `?force=true` (then return those requests and unpublish those items).                                                                                                                                                                                                                 |
| GET        | `/courses/:id/students`          | enrolled students (from registrations and rosters).                                                                                                                                                                                                                                                                                                                                               |

`studentCount` may be set manually; also return `enrolledCount` computed from registrations.

### 6.7 Venues (super; all roles can read)

- `GET /venues` `?type=&status=&search=` with `meta.counts` per tab (All, Lecture halls, Laboratories, Unavailable). Each venue includes `utilisation` = occupied cells / total teaching cells in the active semester (from master entries + published schedule items).
- `POST /venues` `{ building, roomNumber, location, gpsAddress, latitude?, longitude?, capacity, type, code? }` — derive `code` by normalising building+room if not given (normalisation rules in 7.1).
- `PATCH /venues/:id`, `DELETE /venues/:id` (refuse if used in the active semester), `POST /venues/:id/unavailable` `{ reason, until }`, `POST /venues/:id/available`.
- `GET /venues/:id/timetable?semesterId=` — the venue's week grid.

### 6.8 Master timetable (super uploads; all roles read)

| Method | Path                                                                    | Behaviour                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------ | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| GET    | `/timetables?semesterId=`                                               | list of uploaded levels with `filename, uploadedBy, uploadedAt, entryCount, freeCount`.                                                                                                                                                                                                                                                                                                                                                                                         |
| GET    | `/timetables/entries?semesterId=&level=&venue=&subjects=FREE,STAT&day=` | entries; `level` omitted = combined. Include `freeCount` per level and combined in `meta`.                                                                                                                                                                                                                                                                                                                                                                                      |
| POST   | `/timetables/preview`                                                   | multipart `{ file (.xlsx/.csv), semesterId, level }`. Parse with rules in 7.1. Returns `{ entries, issues: [{row, severity, message}], summary: { entryCount, freeCount, venueCount, level }, replaces: { uploadedAt, uploadedBy }                                                                                                                                                                                                                                              | null, affectedRequests: [...] }`. Nothing is saved. Store the parsed result under a `previewId` for 30 minutes. |
| POST   | `/timetables/publish`                                                   | `{ previewId }` → replace (semesterId, level) atomically, record TimetableUpload, auto-create unknown venues. Then re-check every Pending/Approved SlotRequest in that semester+level: if its cells are no longer FREE, mark Pending ones with a `not-free` clash (visible in Conflict centre) and notify their department; for Approved ones create an Override audit entry and notify super. Response message: `"Level X timetable for {semester} published with N entries."` |
| POST   | `/timetables/department/preview`                                        | multipart `{ file, semesterId, departmentId }`. Parse once per level the department's programmes offer; keep entries whose subject starts with one of the department's `subjectPrefixes`; ignore level-mismatch issues. Flag a conflict when the same (day, period, venue) in the semester's master holds a subject of another department. Return `{ entries, conflicts, summary: { entryCount, levels, venues, conflictCount } }`.                                             |
| POST   | `/timetables/department/publish`                                        | `{ previewId }`. 422 if any conflict. Each entry updates the matching master cell (subject, level) or inserts it; if that level's master does not exist, create an empty master for it first. Message `"Department timetable for {name} published with N entries."`                                                                                                                                                                                                             |
| PATCH  | `/timetables/entries/:id`                                               | `{ subject, venueCode, isFree }` (isFree true sets subject "FREE"). Audit as Override.                                                                                                                                                                                                                                                                                                                                                                                          |
| POST   | `/timetables/entries`                                                   | `{ semesterId, level, day, period, subject, venueCode }`.                                                                                                                                                                                                                                                                                                                                                                                                                       |
| DELETE | `/timetables/entries/:id`                                               |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| GET    | `/timetables/double-bookings?semesterId=`                               | cells (excluding shared venues DEPT, ONLINE) with more than one distinct subject: `{ venue, day, period, subjects[] }`.                                                                                                                                                                                                                                                                                                                                                         |
| GET    | `/timetables/export?semesterId=&level=`                                 | CSV `Level, Day, Time ("HH:MM - HH:MM"), Subject, Venue`, sorted day → period → venue. Filename `{semester}-{all-levels                                                                                                                                                                                                                                                                                                                                                         | L400}-master-timetable.csv`.                                                                                    |
| GET    | `/timetables/template`                                                  | the sample CSV.                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| GET    | `/timetables/history?semesterId=`                                       | upload log.                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |

### 6.9 Slot requests and approvals (core workflow)

| Method | Path                                               | Who                                     | Behaviour                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------ | -------------------------------------------------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| GET    | `/free-slots?semesterId=&level=&venue=&view=free   | all`                                    | department, super                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Returns cells for the grid. `view=free`: cells FREE in the semester-wide set (a cell FREE in one level but used in another is **not** free). Each cell: `{ day, period, venue, levels[], capacity, freeRun (consecutive FREE periods from here, max 3), claim: "open" | "pending" | "approved", pendingCount, pendingCourseCodes[], approved?: { courseCode, departmentCode } }`. `view=all`: also include master entries whose subject belongs to the caller's department. `meta`: `freeCount`per level and combined,`myPending`, `myApproved`. |
| POST   | `/slot-requests/check`                             | department                              | Body = placement `{ courseId, semesterId, level, day, venueCode, startPeriod, periodCount, id? }`. Returns `{ clashes: Clash[], blocking: boolean }` using 7.2. Called live while the dialog is open.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| POST   | `/slot-requests`                                   | department                              | Same body. Server re-runs 7.2: any `not-free` or `venue-taken` → 422 `CLASH_BLOCKED` with the clashes. Course must belong to caller's department. periodCount ≤ freeRun. Creates `Pending`, `requestedById = caller`. Returns request with clashes. Notify super: title `"{CODE} · {Title} requested"`, detail `"{dept} · {venue} · {slotLabel}"`, page "Approvals".                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| GET    | `/slot-requests?status=&semesterId=&departmentId=` | department (own dept only), super (all) | Sorted by day, startPeriod, venue. Each item includes `clashes` (omit for Returned), `competing`. `meta.counts` per status.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| DELETE | `/slot-requests/:id` (withdraw)                    | department, own, Pending only           | Sets status `Withdrawn` (keep history; exclude Withdrawn from default lists). 409 if not Pending.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| POST   | `/slot-requests/:id/approve`                       | super                                   | `{ comment? }`. 409 unless Pending. Transaction: (1) create ScheduleItem: start = `periods[startPeriod].start`, end = `periods[startPeriod+periodCount-1].end`, lecturer = course lecturer, groups = course cohorts, mode = course mode, status `published` (or `pending` if a department publish step is wanted; default **published**), source `request`; (2) request → Approved, `reviewComment`, `reviewedAt`, `scheduleItemId`; (3) every other Pending request in the same semester with the same venue and overlapping periods → Returned with comment `"Slot allocated to {dept}. Please choose another FREE slot."`. Notify requester `"{label} approved"` / `"{venue} · {slot}"` page "Schedule requests"; notify each displaced requester `"{label} returned"` / `"{venue} · {slot} was allocated to {dept}."`. Response `{ request, scheduleItem, displaced: [...] }`. |
| POST   | `/slot-requests/:id/return`                        | super                                   | `{ comment }` default `"Returned by central administration."`. Allowed from Pending; also from Approved (revoke): then delete/unpublish the linked ScheduleItem. Notify requester.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| POST   | `/slot-requests/:id/override`                      | super                                   | Approve despite danger clashes; requires `reason`; logged in audit with category "Overrides".                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

### 6.10 Conflict centre (super)

`GET /conflicts?semesterId=` → `{ requests: [{ request, clashes }] (non-Returned with ≥1 clash, danger first, then day, period), stats: { withDanger, warningsOnly, doubleBookings }, doubleBookings: [...] }`.
Also include ScheduleItems with status `conflict`. Sidebar badge = `withDanger`.

### 6.11 Department timetable, final timetable, personal timetables

| Method | Path                                                               | Who                                  | Behaviour                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------ | ------------------------------------------------------------------ | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET    | `/schedule?semesterId=&departmentId=&level=&venueType=lecture_hall | laboratory&search=&status=`          | all (scoped)                                                                                                                                                                                                                                                                                                                                                                                                                                             | Search over course code, title, venue, lecturer name. Level from the course cohorts; items with no level appear only in combined; return `meta.levelCounts` incl. `unassigned`, plus `pending`, `conflict`, `published` counts and `venueUtilisation` (% and peak period). |
| POST   | `/schedule`                                                        | department                           | Manual class slot `{ courseId, day, start, end (or startPeriod, periodCount), venueCode, lecturerId?, mode, groups[] }`. Validate end > start, day allowed (weekends only if allowed), course is own department. Run clash checks (7.2 extended to schedule items); status `conflict` if any danger clash, else `pending` (or `published` when `autoPublishApproved`).                                                                                   |
| PATCH  | `/schedule/:id`                                                    | department (own), super              | edit; re-run clash checks; conflict → pending if clean.                                                                                                                                                                                                                                                                                                                                                                                                  |
| DELETE | `/schedule/:id`                                                    | department (own manual items), super |                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| POST   | `/schedule/publish`                                                | department                           | `{ ids[] }` or `{ courseCode }` — pending → published. Refuse items in `conflict` when `requireConflictApproval`. Message `"{n} courses published."` Notify affected lecturers and students (schedule category).                                                                                                                                                                                                                                         |
| GET    | `/schedule/final?semesterId=&level=`                               | department                           | published items of own department + `meta.notIncluded: { pending, conflict }`.                                                                                                                                                                                                                                                                                                                                                                           |
| GET    | `/schedule/final/export`                                           | department                           | CSV columns `Course, Title, Day, Start, End, Venue, Lecturer, Mode, Student group, Status`, sorted day → start → venue; filename `{dept}-{all-levels                                                                                                                                                                                                                                                                                                     | L400}-final-timetable.csv`. Status labels: Published / Awaiting approval / Blocked by conflict.                                                                                                                                                                            |
| GET    | `/me/timetable?semesterId=&weekOf=`                                | lecturer, student                    | Lecturer: items where `lecturerId = me` (flag `assignedToMe`) plus optionally department items `?include=department`. Student: published items whose groups include the student's (programmeId, level) or whose course the student is registered for. Include `assessments` (Upcoming/Shared for the student's courses) and `stats: { weeklyClasses, classesToday (based on today's weekday), upcomingAssessments, registeredCourses, teachingGroups }`. |
| GET    | `/me/timetable/export?format=csv                                   | ics`                                 | lecturer, student                                                                                                                                                                                                                                                                                                                                                                                                                                        |                                                                                                                                                                                                                                                                            |

### 6.12 Assessments

| Method | Path                                            | Who                                                            | Behaviour                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------ | ----------------------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET    | `/assessments?status=&scope=&courseId=&search=` | all                                                            | Super: all. Department: own department + shared. Lecturer: own courses + invigilation assignments (tab "Invigilation"). Student: only Upcoming/Shared for courses they are registered on or cohorts they belong to. `meta.counts` per status.                                                                                                                                                                                                                                                                                                                                                                                                                           |
| POST   | `/assessments`                                  | super, department, lecturer                                    | Body section 5.12 form fields. Validation: end > start → `"The assessment end time must be after the start time."`; date inside the active semester. Status: super → `Upcoming`; department, lecturer → `Submitted` (or `Draft` if `saveAsDraft: true`). Run checks: venue already used by a class or another assessment at that time, cohort clash, lecturer clash, capacity — return as `clashes` warnings; block on venue double-booking. Notifications: lecturer submission → department admins of that department, page "My assessments"/"Department assessments"; department submission → super; super creation → students of the cohorts, page "My assessments". |
| PATCH  | `/assessments/:id`                              | creator while Draft/Returned; super                            |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| POST   | `/assessments/:id/submit`                       | creator                                                        | Draft/Returned → Submitted.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| POST   | `/assessments/:id/approve`                      | department (for lecturer submissions of own dept), super (any) | Submitted → Upcoming. A creator cannot approve their own submission. Notify creator and students.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| POST   | `/assessments/:id/return`                       | same reviewers                                                 | `{ comment }` required → `"Add a review comment before returning this entry."`. → Returned; notify creator.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| POST   | `/assessments/:id/cancel`                       | creator, super                                                 |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| PUT    | `/assessments/:id/invigilators`                 | department, super                                              | `[{ userId, role }]`; notify invigilators.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| GET    | `/assessments/export`                           | all (scoped)                                                   | CSV (students: `my-assessments.csv`, only their visible ones).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

### 6.13 Attendance

| Method | Path                                                 | Who                                                            | Behaviour                                                                                                                                                                                                                                                                        |
| ------ | ---------------------------------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| GET    | `/attendance/sessions?status=live                    | completed                                                      | missed&courseId=&departmentId=&date=`                                                                                                                                                                                                                                            | lecturer (own), department (own dept), super | Each: course, lecturer, venue, time, counts, rate, `lecturerCheckedIn`. `meta.counts` per tab (All, Live, Completed, Missed). |
| POST   | `/attendance/sessions`                               | lecturer (own course)                                          | `{ courseId, scheduleItemId?, date, startTime, endTime }`; `expectedCount` = enrolled students.                                                                                                                                                                                  |
| POST   | `/attendance/sessions/:id/open`                      | lecturer                                                       | status live, generate `qrSecret`.                                                                                                                                                                                                                                                |
| GET    | `/attendance/sessions/:id/qr`                        | lecturer                                                       | `{ token, expiresAt }`; token = HMAC(secret, floor(now/30s)); rotates every 30 s.                                                                                                                                                                                                |
| POST   | `/attendance/check-in`                               | student                                                        | `{ token }` → validate current or previous window, student enrolled → record Present (Late if after start + 15 min), source "QR scan". Optional geofence using venue lat/long.                                                                                                   |
| POST   | `/attendance/sessions/:id/close`                     | lecturer                                                       | status completed; every enrolled student without a record → Absent.                                                                                                                                                                                                              |
| POST   | `/attendance/records`                                | lecturer                                                       | Manual: `{ sessionId? or (courseId, sessionDate), studentId, status }`. Creates the session if needed. Upsert on (session, student). Student must be enrolled in the course. Notify the student: `"{course} attendance recorded"` / `"{status} · {date}"`, page "My attendance". |
| POST   | `/attendance/records/bulk`                           | lecturer                                                       | `{ sessionId, records: [{ studentId, status }] }` — full register in one call.                                                                                                                                                                                                   |
| PATCH  | `/attendance/records/:id`                            | lecturer (own), department                                     | change status, `note`.                                                                                                                                                                                                                                                           |
| GET    | `/attendance/records?courseId=&studentId=&from=&to=` | lecturer (own courses), student (self only), department, super | `stats: { sessions, present, late, absent, excused, rate }`.                                                                                                                                                                                                                     |
| GET    | `/attendance/export?scope=department                 | institution`                                                   | department, super                                                                                                                                                                                                                                                                | CSV register.                                |

Nightly job: scheduled sessions (derived from published schedule items for each teaching day) that were never opened → `missed`; notify department.

### 6.14 Course registration, rosters, students and faculty

| Method                          | Path                                                                               | Who                               | Behaviour                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------- | ---------------------------------------------------------------------------------- | --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET                             | `/me/registrations?semesterId=`                                                    | student                           | own only; `meta.counts` (Current, Required, Electives); `totalCredits`.                                                                                                                                                                                                                                                                                                                  |
| GET                             | `/registration/catalogue?semesterId=`                                              | student                           | courses whose cohorts include the student's programme+level first, then electives from other programmes.                                                                                                                                                                                                                                                                                 |
| POST                            | `/me/registrations`                                                                | student                           | `{ courseId                                                                                                                                                                                                                                                                                                                                                                              | (customCourseCode, customCourseTitle), semesterId, level, registrationType, credits }`. Reject after `registrationDeadline`(409 "Registration for this semester has closed."), duplicate course (409), credit cap if configured. Custom courses → status`Pending approval` for the department. Notify the course lecturer: "{title} submitted", page "My students". Student identity comes from the token, never the body. |
| DELETE                          | `/me/registrations/:id`                                                            | student                           | drop (before deadline).                                                                                                                                                                                                                                                                                                                                                                  |
| GET                             | `/lecturer/courses?semesterId=&tab=current                                         | groups                            | past`                                                                                                                                                                                                                                                                                                                                                                                    | lecturer                                                                                                                                                                                                                                                                                                                                                                                                                   | courses where `lecturerId = me` with sections, enrolled count, weekly contact hours (sum of published schedule item hours), workload % = contact hours / configured max (default 25 h). |
| GET                             | `/lecturer/students?courseId=`                                                     | lecturer                          | roster of own courses; `meta.counts` (Courses, Students, Registrations, Imports).                                                                                                                                                                                                                                                                                                        |
| POST                            | `/imports/course-roster`                                                           | lecturer (own course), department | multipart `{ file (.csv), courseId, studentCategory, academicYear, semesterId }`. Required headers `student id, name, email`. Parse properly (quoted commas). For each row: find student by student number or email; create student user (status invited) if missing; create CourseRegistration (source roster-import). Async; returns StudentImport. Notify the uploader on completion. |
| POST                            | `/imports/students`                                                                | department                        | multipart `{ file, studentCategory, academicYear, programmeId, level }`. Required headers `student id, name, email, programme, level`. Creates/updates student users with programme+level, sends invitations. Notify department admins on completion.                                                                                                                                    |
| GET                             | `/imports?kind=` / `GET /imports/:id` / `GET /imports/:id/rows`                    | creator, department, super        | status and per-row outcomes/warnings.                                                                                                                                                                                                                                                                                                                                                    |
| CSV validation messages (reuse) |                                                                                    |                                   | `"Choose a file to upload."`, `"Upload a CSV file so its columns and rows can be validated."`, `"The CSV file must include a header and at least one row."`, `"Missing CSV columns: …"`.                                                                                                                                                                                                 |
| GET                             | `/students?departmentId=&programmeId=&level=&search=`                              | department (own), super           | tabs Students, Cohorts (programme+level with counts), Sections, Imports.                                                                                                                                                                                                                                                                                                                 |
| CRUD                            | `/sections`                                                                        | department                        | section 5.18.                                                                                                                                                                                                                                                                                                                                                                            |
| GET                             | `/faculty?status=active                                                            | invited                           | disabled&search=`                                                                                                                                                                                                                                                                                                                                                                        | department (own), super                                                                                                                                                                                                                                                                                                                                                                                                    | lecturers with course count and last sign-in.                                                                                                                                           |
| POST                            | `/faculty`                                                                         | department, super                 | `{ name, email, rank, staffId?, departmentId (super only) }` → lecturer user, status invited, invitation email. Message `"{name} added and invited successfully."`                                                                                                                                                                                                                       |
| PATCH                           | `/faculty/:id`, POST `/faculty/:id/disable`, POST `/faculty/:id/resend-invitation` |                                   |                                                                                                                                                                                                                                                                                                                                                                                          |
| GET/POST/PATCH                  | `/staff`                                                                           | super                             | all non-student users; tabs Administrators, Faculty, Roles. POST `{ name, staffId, email, rank, departmentId, role }` creates the user and sends an invitation.                                                                                                                                                                                                                          |
| CRUD                            | `/role-templates`                                                                  | super                             | section 5.17.                                                                                                                                                                                                                                                                                                                                                                            |

### 6.15 Graduation data

| Method | Path                                   | Who                     | Behaviour                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------ | -------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| POST   | `/graduation/submissions`              | department              | multipart `{ file (.csv), studentCategory, academicYear, programmeId or programmeText, declaredCount (≥1) }`. Required headers `student id, name, programme`. Parse rows into GraduationCandidates; flag rows whose student number is unknown or not in that department; warn if row count ≠ declaredCount. Reject after `graduationDeadline` unless super. Status Submitted. Notify super, page "Graduation data". |
| GET    | `/graduation/submissions?status=`      | department (own), super | tabs All, Submitted, Validated, Returned.                                                                                                                                                                                                                                                                                                                                                                           |
| GET    | `/graduation/submissions/:id`          |                         | with candidates and issues.                                                                                                                                                                                                                                                                                                                                                                                         |
| PATCH  | `/graduation/candidates/:id`           | super                   | set academicClearance / financialClearance.                                                                                                                                                                                                                                                                                                                                                                         |
| POST   | `/graduation/submissions/:id/validate` | super only              | Submitted → Validated. If `requireAcademicClearance`/`requireFinancialClearance`, every candidate must be cleared. Notify the department and the submitter.                                                                                                                                                                                                                                                         |
| POST   | `/graduation/submissions/:id/return`   | super only              | comment required → Returned. Department may resubmit (new file) → Submitted.                                                                                                                                                                                                                                                                                                                                        |
| GET    | `/graduation/export`                   | super, department       | CSV `graduation-data.csv`.                                                                                                                                                                                                                                                                                                                                                                                          |

### 6.16 Notifications

- `GET /notifications?unread=true&page=` → visible items (rule 5.19), newest first, `meta.unreadCount`.
- `POST /notifications/:id/read`, `POST /notifications/read-all`.
- Real-time: push new notifications over WebSocket or Server-Sent Events at `/notifications/stream`; frontend falls back to polling every 30 s.
- Emission respects the recipient's preferences (category + channel) and the institution/department notify toggles. Email channel sends the same title/detail with a deep link `/#/{role}/{page-slug}`.
- The `page` field is the destination page **label** (e.g. "Approvals", "Schedule requests", "My attendance", "Graduation data", "My students", "Students & groups", "Programmes & courses", "My assessments"); the frontend resolves it with `resolvePortalPath`.
- Retention: keep 1 year; no 200-item cap.

### 6.17 Dashboards (replace every hard-coded number)

- `GET /dashboard/super` → `{ departments, faculty, assessments, venues, openSlots, freeCells, pendingApprovals, openConflicts, sessionsToday, liveSessions, assessmentsToday, readyToPublish, departmentsNotSubmitted: [...], submissionWindowClosesInDays, nextSessions: ScheduleItem[3] }`.
- `GET /dashboard/department` → `{ courseOfferings, faculty, activeStudents, scheduleRequests, readiness: { offeringsAssigned: {done,total}, facultyCoverage, studentGroupsMapped, venueSlotsConfirmed, percent }, centralSlotsAvailable, submissionWindowClosesInDays, attention: [{ title, detail, page }] }` (e.g. course whose studentCount > venue capacity, open FREE slots, pending invitations).
- `GET /dashboard/lecturer` → `{ classesToday, assignedCourses, studentsReached, attendanceRate, attendanceTrend, todayTimeline, contactHours, workloadPercent, teachingGroups, recentRegisters: [{course, present, expected, rate}], attendanceHealth: { rate, checkIns, expected, late, absent }, nextSessionStartsInMinutes }`.
- `GET /dashboard/student` → `{ classesToday, registeredCourses, assessmentsSoon, attendanceRate, today: [...] }`.
- Sidebar badges: `GET /badges` → `{ approvals, conflictCentre, scheduleRequests }` for the caller.

### 6.18 Reports (super, department)

`POST /reports` `{ reportType, academicYear, semester, programmeId?, studentCategory?, dateFrom, dateTo, format: "csv" }` → generates real data, stores ReportJob, returns `{ id, fileUrl }`; `GET /reports` lists previous jobs; `GET /reports/:id/download`.
Report types and columns:

- Institution timetable / Department timetable: the final-timetable CSV columns.
- Department submissions: department, pending, approved, returned requests, last submission date.
- Faculty workload: lecturer, department, courses, weekly contact hours, workload %.
- Venue utilisation: venue, capacity, occupied periods, utilisation %, peak period.
- Attendance summary: course, sessions, present, late, absent, excused, rate.
- Assessment schedule: course, type, date, start, end, location, status.
- Graduation data: programme, category, year, students, status.
- Student enrollment: programme, level, category, students.
- Course offerings: course, title, type, credits, lecturer, cohorts, students.
  Department reports are scoped to their department.

### 6.19 Audit trail (super)

`GET /audit?category=Scheduling|Approvals|Overrides&actorId=&entityType=&from=&to=&search=` with tab counts; `GET /audit/export` → `audit-trail.csv`. Every mutation in this document writes an entry (before/after JSON, IP, user agent). Nightly purge older than `auditRetention`.

### 6.20 Demo reset (keep the login screen's "Reset demo workspace")

`POST /admin/demo/reset` — enabled only when `DEMO_MODE=true`; truncates and re-seeds (section 9).

---

## 7. Business rules to port exactly

### 7.1 Master timetable file parsing (port `src/lib/timetable/parse.ts`)

- Accept `.csv` (RFC-style: quotes, `""` escapes, CRLF) and `.xlsx`. Anything else → `"Upload the master timetable as an Excel (.xlsx) or CSV file."`
- Header = first row with any non-empty cell. Match lowercase exactly: `level, day, time, start, end, subject, venue`. Required: `day, subject, venue` and (`time` or `start`). Missing → error at header row `"Missing column(s): x, y. Expected Level, Day, Time, Subject, Venue."`
- Cell text: Excel Date → `H:MM` (UTC); number in [0,1) → minutes `round(n×1440)` → `H:MM`; else trimmed string.
- Day: first 3 letters, case-insensitive, against weekdays.
- Time: from `time` or `start - end`; extract `\d{1,2}[:.]\d{2}` tokens; first must equal some `periods[i].start`; optional second must equal `periods[j].end` with j ≥ i → expands to one entry per period i..j.
- Level: first `\d{3}` in the cell; if present and ≠ selected level → skip with `"Level X does not match the selected Level Y"`.
- Subject normalisation: uppercase; `©` → `(C)`; `( C )`/`(E )` → ` (C)`/` (E)`; collapse whitespace. `FREE` → isFree.
- Venue normalisation: uppercase, collapse spaces, then `^L/OT\s*` → `LOT`, `^LOT\s+` → `LOT`, `^JQB\s*(\d+)$` → `JQB` + 2-digit number, `^GCB FFR(\d)` and `^GCB FF RM(\d)` → `GCB FF R$1`.
- Skip rows (error, 1-based sheet row number): unknown day, time not on the period grid, empty subject, empty venue.
- Same (day, period, venue) and same subject → skip silently. Different subject at a non-shared venue → warning `"{venue} is listed for both A and B on {Day} {label}."` and keep both.
- Entry id `${level}|${day}|${period}|${venue}|${subject}` (or a UUID; keep this as a natural key).
- Empty file → `"The file is empty."`; header only → `"The file has a header but no timetable rows."`

### 7.2 Clash engine (port `src/lib/scheduling/conflicts.ts`, then extend)

`overlap(a,b) = a.day === b.day && a.startPeriod < b.startPeriod + b.periodCount && b.startPeriod < a.startPeriod + a.periodCount`.
Free cells = all FREE master entries of the semester across all levels, keyed `day|period|venue`.
Checks for a placement, in order:

1. `level` (danger): course has no cohort at `placement.level`. Message: `"{code} is taken by Level X students (...), but this FREE slot is on the Level Y timetable. Pick a FREE slot from the Level X timetable."`
2. `not-free` (danger, **blocking**): any period in range not in free cells → `"{venue} is not FREE for {slot} in the active master timetable."`
3. For each other request (id ≠ placement.id, same semester, status Pending or Approved, overlapping):
   - same venue + Approved → `venue-taken` (danger, **blocking**) `"{venue} is already allocated to {code} ({dept}) for {slot}."`
   - same venue + Pending → `pending-venue` (warning) — same department: `"Your department already requested …"`; other: `"Requested by {dept} on {d MMM} for {code}, awaiting approval."`
   - different course sharing a cohort → `student` (danger), one per shared cohort, `", pending approval"` suffix if pending.
   - different course with the same lecturer → `lecturer` (danger) `"{name} also teaches {code} at …"`.
4. `capacity` (warning): `studentCount > capacity × (1 + capacityTolerance/100)`; skip when capacity unknown → `"{code} has {n} students but {venue} seats {cap}."`
   **Extension the frontend does not have:** also run checks 3 (venue, student, lecturer) against published/pending **ScheduleItems** and Upcoming **Assessments**, not only against SlotRequests, so manual class slots cannot double-book.
   Each clash: `{ kind, severity, message, otherRequestId?, otherScheduleItemId? }`. `slotLabel = "{Mon} {start}–{end}"`.

### 7.3 Grid helpers

- `freeRunLength(day, venue, start)` = consecutive FREE periods from start, max 3.
- Shared venues `DEPT`, `ONLINE` may host several classes in a cell and are excluded from double-booking.
- Schedule item ↔ course: always use `courseId` (do not rely on code matching).

### 7.4 Status machines (reject illegal transitions with 409)

- SlotRequest: Pending → Approved | Returned | Withdrawn; Approved → Returned (super revoke, removes the class).
- ScheduleItem: pending ↔ conflict (by clash re-check) → published; published → pending on edit.
- Assessment: Draft → Submitted → Upcoming | Returned; Returned → Submitted; Upcoming → Cancelled; super creates directly as Upcoming.
- GraduationSubmission: Submitted → Validated | Returned; Returned → Submitted (resubmission).
- AttendanceSession: scheduled → live → completed; scheduled → missed.
- StudentImport: Queued → Processing → Completed | Failed.
- User: invited → active → disabled → active.

### 7.5 Tone (badge colour) returned with every status

Approved / Upcoming / Published / Validated / Present → `green`; Returned / Absent / Missed / conflict → `red`; Submitted / Pending / Late → `amber`; Excused / Live → `blue`; others → `slate`.

---

## 8. End-to-end flow (onboarding to the end of a semester)

1. **System bootstrap.** Seed the super admin (`superadmin@ug.edu.gh`), periods, semesters, venues, role templates, institution settings.
2. **Super admin configures the institution.** Settings: name, support email, timezone, active semester and dates, registration and graduation deadlines, scheduling policy, 2FA policy.
3. **Super admin adds venues** (or they appear from the first master upload) with capacity and type.
4. **Super admin creates departments.** Each creation makes a department admin account and sends an invitation. The admin accepts, sets a password, optionally enables 2FA.
5. **Department admin builds the academic structure.** Programmes (levels offered), courses (type, credits, mode, students, lecturer, cohorts including other departments' programmes).
6. **Department admin onboards people.** Invites faculty (lecturer accounts), imports students by CSV (student accounts with programme and level), creates sections. Students may also self-register.
7. **Academic Affairs (super) uploads master timetables** per level: preview, fix issues, publish. FREE cells become requestable. Department-specific timetable files can be merged in.
8. **Departments request FREE slots.** They browse FREE cells per level, pick a course and length, see live clashes, submit. Super is notified.
9. **Super admin reviews in Approvals and the Conflict centre.** Approve (creates the class, returns competitors), return with comment, or override with a reason. Departments are notified and re-request returned slots. Departments can withdraw pending ones.
10. **Departments maintain their timetable.** Add manual class slots, fix conflicts, publish. The final timetable is exported and printed.
11. **Lecturers and students see their timetables.** Lecturers see assigned classes, courses, rosters; students register for courses before the registration deadline and lecturers upload rosters.
12. **Teaching runs.** Lecturers open attendance sessions (QR rotating every 30 s, or manual/bulk register), close them; absentees are filled in; missed sessions are flagged; students see their history; admins monitor live/completed/missed.
13. **Assessments.** Lecturers/departments submit, reviewers approve or return, super schedules institution-wide ones, invigilators are assigned, students see Upcoming ones on their timetable.
14. **Graduation.** Departments upload graduand lists before the deadline; super clears and validates or returns.
15. **Oversight throughout.** Notifications, dashboards, reports, audit trail, CSV exports.
16. **Semester rollover.** Super creates the next semester and activates it; master timetables, requests, schedule, sessions and registrations are per-semester so the new term starts clean while history stays queryable.

---

## 9. Seed data

Load from the frontend fixtures (they are currently never loaded by the UI):

- 11 accounts from `src/stores/fixtures/auth.ts` (map `scope` names to `departmentId` / `programmeId`; set student level 300 for the four demo students; hash the demo passwords; status active). Keep the demo passwords only in demo mode.
- 6 departments, 6 programmes, 11 courses with cohorts and lecturers from `fixtures/academics.ts`.
- Venues + capacities from `src/lib/timetable/venues.ts`.
- Level 400 master timetable for 2026/27 S1 parsed from `src/lib/timetable/master-2026-27-s1.csv`.
- 3 slot requests (`seed-stat431` Approved with its schedule item, `seed-math445` Pending, `seed-dcit415` Returned), attendance, notifications and workflow records from the remaining fixtures, mapped to the new tables (split `ModuleRecord` collections into Assessment, GraduationSubmission, CourseRegistration, StudentImport).

---

## 10. Frontend integration map (what each store action becomes)

| Frontend store action                                                  | Endpoint                                                                               |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------ | ------------------------------------------- |
| `auth.login / logout / register`                                       | `POST /auth/login`, `/auth/logout`, `/auth/register`                                   |
| `auth.createDepartmentAccount` + `academics.saveDepartment`            | single `POST /departments`                                                             |
| `academics.deleteDepartment`                                           | `DELETE /departments/:id`                                                              |
| `academics.saveProgramme / deleteProgramme`                            | `POST                                                                                  | PATCH                                | DELETE /programmes`                         |
| `academics.saveCourse / deleteCourse`                                  | `POST                                                                                  | PATCH                                | DELETE /courses`                            |
| `timetable.publish`                                                    | `POST /timetables/preview` then `/timetables/publish`                                  |
| `timetable.updateEntry / addEntry / removeEntry`                       | `PATCH                                                                                 | POST                                 | DELETE /timetables/entries`                 |
| `scheduling.submitRequest` (+ live `detectClashes`)                    | `POST /slot-requests/check`, `POST /slot-requests`                                     |
| `scheduling.approveRequest / returnRequest / withdrawRequest`          | `POST /slot-requests/:id/approve                                                       | return`, `DELETE /slot-requests/:id` |
| `scheduling.saveScheduleItem / deleteScheduleItem / clearCourseStatus` | `POST                                                                                  | PATCH                                | DELETE /schedule`, `POST /schedule/publish` |
| `attendance.recordAttendance`                                          | `POST /attendance/records`                                                             |
| `records.saveRecord("assessments")` / `updateStatus`                   | `POST /assessments`, `/assessments/:id/approve                                         | return`                              |
| `records.saveRecord("graduation-data")` / `updateStatus`               | `POST /graduation/submissions`, `/validate`, `/return`                                 |
| `records.saveRecord("course-registrations")`                           | `POST /me/registrations`                                                               |
| `records.saveRecord("student-imports")` / faculty roster import        | `POST /imports/students`, `/imports/course-roster`                                     |
| `records.saveRecord("super.Venues")`                                   | `POST /venues`                                                                         |
| `records.saveRecord("super.Staff & access")` / `department.Faculty`    | `POST /staff`, `POST /faculty`                                                         |
| `records.saveRecord("super.Academic structure")`                       | `POST /departments` (remove the duplicate placeholder)                                 |
| reports `downloadSummary`                                              | `POST /reports` + download                                                             |
| audit page                                                             | `GET /audit`, `/audit/export`                                                          |
| `notifications.push / markRead / markAllRead`                          | server-emitted; `POST /notifications/:id/read`, `/read-all`                            |
| `profile.saveProfile`                                                  | `PATCH /me/profile`, `POST /me/photo`, `PUT /me/notification-preferences`, `/me/2fa/*` |
| `settings.saveSettings(role)`                                          | `PUT /settings/institution` or `/settings/department`                                  |
| hard-coded dashboard numbers                                           | `GET /dashboard/{role}`, `GET /badges`                                                 |

Deliver a typed client (or OpenAPI-generated TypeScript types) so the frontend can replace each
zustand action with a call and keep the stores as caches.

---

## 11. Verification (definition of done)

1. Automated tests for: the timetable parser (feed `master-2026-27-s1.csv`, expect 551 rows read, 15 FREE, correct venue normalisation), every clash kind, approve-with-displacement, withdraw/return state rules, scoping (a lecturer cannot read another lecturer's attendance; a student cannot read another student's registrations; a department admin cannot approve requests or touch another department's courses), CSV import validation messages, graduation validation with clearance flags.
2. Scripted end-to-end run of section 8 against a fresh seeded database via the HTTP API: create department → accept invitation → add programme and course → upload Level 400 timetable → request a FREE slot → approve → see it in the department final timetable, the lecturer's and the student's timetable → open an attendance session → QR check-in → close → student sees Present → submit and approve an assessment → upload and validate graduation data → generate each report → confirm audit entries and notifications exist for every step.
3. OpenAPI document served and matching the implementation.
4. Frontend smoke test: point the frontend at the API for login and one workflow per portal, then run `pnpm typecheck` and `pnpm build` in this repo.

We are working on this project. Before I brief you, learn what has already implemented. The structure and everythingso you can familiarise yourself as a new senior backend n=engineer about to take over this project

The target is to make this a fully fledged application. You may refence, but not limit yourself to /Users/mac/Documents/projects/SPMS_Academic_Hub_Server/backend.md

You are a senior backend engineer who is most particular about domain relevance, efficiencey, correctness, effectiveness, and optimisation. Work on this project with industry standard practices. All migrations should be tracked in the versions files

I am particular about role based acccess control. We must have clearly defined roles and their permissions set, and all endpoints should be accessible only by permission injection
