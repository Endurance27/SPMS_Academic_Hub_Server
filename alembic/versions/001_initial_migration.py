"""Initial migration with all models

Revision ID: 001_initial
Revises: 
Create Date: 2026-10-24 20:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create tables in dependency order (SQLAlchemy will handle enum creation automatically)
    
    # 1. Departments (no dependencies)
    op.create_table('departments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('school', sa.String(length=255), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('tone', sa.Enum('BLUE', 'VIOLET', 'AMBER', 'GREEN', 'ROSE', name='departmenttone'), nullable=True),
    sa.Column('subject_prefixes', sa.ARRAY(sa.String()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index(op.f('ix_departments_code'), 'departments', ['code'], unique=True)
    op.create_index(op.f('ix_departments_name'), 'departments', ['name'], unique=True)
    
    # 2. Users (no dependencies except roles/permissions which we handle separately)
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('role', sa.Enum('SUPER', 'DEPARTMENT', 'LECTURER', 'STUDENT', name='userrole'), nullable=False),
    sa.Column('status', sa.Enum('INVITED', 'ACTIVE', 'DISABLED', name='userstatus'), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=True),
    sa.Column('programme_id', sa.UUID(), nullable=True),
    sa.Column('level', sa.Integer(), nullable=True),
    sa.Column('student_category', sa.Enum('UNDERGRADUATE', 'POSTGRADUATE', name='studentcategory'), nullable=True),
    sa.Column('student_number', sa.String(length=50), nullable=True),
    sa.Column('staff_id', sa.String(length=50), nullable=True),
    sa.Column('rank', sa.Enum('PROFESSOR', 'ASSOCIATE_PROFESSOR', 'SENIOR_LECTURER', 'LECTURER', 'ASSISTANT_LECTURER', name='staffrank'), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('office', sa.String(length=100), nullable=True),
    sa.Column('photo_url', sa.String(length=500), nullable=True),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('two_factor_enabled', sa.Boolean(), nullable=True),
    sa.Column('two_factor_secret', sa.String(length=32), nullable=True),
    sa.Column('two_factor_method', sa.String(length=20), nullable=True),
    sa.Column('role_template_id', sa.UUID(), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failed_login_attempts', sa.Integer(), nullable=True),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('staff_id'),
    sa.UniqueConstraint('student_number')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Add foreign keys to users after departments and programmes exist
    op.create_foreign_key('fk_users_department_id', 'users', 'departments', ['department_id'], ['id'])
    
    # 3. Semesters (no dependencies)
    op.create_table('semesters',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('academic_year', sa.String(length=20), nullable=False),
    sa.Column('number', sa.Integer(), nullable=False),
    sa.Column('label', sa.String(length=50), nullable=False),
    sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('teaching_start', sa.DateTime(timezone=True), nullable=True),
    sa.Column('teaching_end', sa.DateTime(timezone=True), nullable=True),
    sa.Column('registration_deadline', sa.DateTime(timezone=True), nullable=False),
    sa.Column('graduation_deadline', sa.DateTime(timezone=True), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id'),
    sa.UniqueConstraint('is_active')
    )
    
    # 4. Venues (no dependencies)
    op.create_table('venues',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('building', sa.String(length=100), nullable=False),
    sa.Column('room_number', sa.String(length=50), nullable=False),
    sa.Column('location', sa.String(length=255), nullable=True),
    sa.Column('gps_address', sa.String(length=255), nullable=True),
    sa.Column('latitude', sa.String(length=50), nullable=True),
    sa.Column('longitude', sa.String(length=50), nullable=True),
    sa.Column('capacity', sa.Integer(), nullable=True),
    sa.Column('type', sa.Enum('LECTURE_HALL', 'LABORATORY', 'SEMINAR_ROOM', 'ONLINE', 'SHARED', name='venuetype'), nullable=False),
    sa.Column('is_shared', sa.Boolean(), nullable=True),
    sa.Column('status', sa.Enum('AVAILABLE', 'UNAVAILABLE', name='venuestatus'), nullable=True),
    sa.Column('unavailable_reason', sa.String(length=255), nullable=True),
    sa.Column('unavailable_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index(op.f('ix_venues_code'), 'venues', ['code'], unique=True)
    
    # 5. Programmes (depends on departments)
    op.create_table('programmes',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('levels', sa.ARRAY(sa.Integer()), nullable=True),
    sa.Column('category', sa.Enum('UNDERGRADUATE', 'POSTGRADUATE', name='programmecategory'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    # Add programme foreign key to users
    op.create_foreign_key('fk_users_programme_id', 'users', 'programmes', ['programme_id'], ['id'])
    
    # 6. Courses (depends on departments and users)
    op.create_table('courses',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('type', sa.Enum('CORE', 'ELECTIVE', name='coursetype'), nullable=False),
    sa.Column('credit_hours', sa.Integer(), nullable=False),
    sa.Column('mode', sa.Enum('ONLINE', 'IN_PERSON', 'HYBRID', name='coursemode'), nullable=True),
    sa.Column('student_count', sa.Integer(), nullable=False),
    sa.Column('lecturer_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['lecturer_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index(op.f('ix_courses_code'), 'courses', ['code'], unique=True)
    
    # Course cohorts association table
    op.create_table('course_cohorts',
    sa.Column('course_id', sa.UUID(), nullable=False),
    sa.Column('programme_id', sa.UUID(), nullable=False),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['programme_id'], ['programmes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('course_id', 'programme_id', 'level')
    )
    
    # 7. Slot Requests (without circular FK to schedule_items)
    op.create_table('slot_requests',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('course_id', sa.UUID(), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('requested_by_id', sa.UUID(), nullable=False),
    sa.Column('semester_id', sa.UUID(), nullable=False),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.Column('day', sa.Integer(), nullable=False),
    sa.Column('venue_code', sa.String(length=50), nullable=False),
    sa.Column('start_period', sa.Integer(), nullable=False),
    sa.Column('period_count', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'RETURNED', 'WITHDRAWN', name='slotrequeststatus'), nullable=True),
    sa.Column('review_comment', sa.Text(), nullable=True),
    sa.Column('reviewed_by_id', sa.UUID(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('schedule_item_id', sa.UUID(), nullable=True),  # No FK constraint yet
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['requested_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    # 8. Schedule Items (without circular FK to slot_requests)
    op.create_table('schedule_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('semester_id', sa.UUID(), nullable=False),
    sa.Column('course_id', sa.UUID(), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('slot_request_id', sa.UUID(), nullable=True),  # No FK constraint yet
    sa.Column('day', sa.Integer(), nullable=False),
    sa.Column('start_period', sa.Integer(), nullable=True),
    sa.Column('period_count', sa.Integer(), nullable=True),
    sa.Column('start', sa.String(length=5), nullable=True),
    sa.Column('end', sa.String(length=5), nullable=True),
    sa.Column('venue_code', sa.String(length=50), nullable=False),
    sa.Column('lecturer_id', sa.UUID(), nullable=True),
    sa.Column('mode', sa.String(length=20), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'CONFLICT', 'PUBLISHED', name='scheduleitemstatus'), nullable=True),
    sa.Column('source', sa.Enum('REQUEST', 'MANUAL', 'DEPARTMENT_UPLOAD', name='scheduleitemsource'), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['lecturer_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    # Now add the circular foreign keys
    op.create_foreign_key('fk_slot_requests_schedule_item_id', 'slot_requests', 'schedule_items', ['schedule_item_id'], ['id'])
    op.create_foreign_key('fk_schedule_items_slot_request_id', 'schedule_items', 'slot_requests', ['slot_request_id'], ['id'])
    
    # Schedule item groups
    op.create_table('schedule_item_groups',
    sa.Column('schedule_item_id', sa.UUID(), nullable=False),
    sa.Column('programme_id', sa.UUID(), nullable=False),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.Column('section', sa.String(length=50), nullable=True),
    sa.ForeignKeyConstraint(['programme_id'], ['programmes.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['schedule_item_id'], ['schedule_items.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('schedule_item_id', 'programme_id', 'level')
    )
    
    # 9. Master Timetables
    op.create_table('master_timetables',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('semester_id', sa.UUID(), nullable=False),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('uploaded_by_id', sa.UUID(), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('version', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ),
    sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    op.create_table('master_entries',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('timetable_id', sa.UUID(), nullable=False),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.Column('day', sa.Integer(), nullable=False),
    sa.Column('period', sa.Integer(), nullable=False),
    sa.Column('subject', sa.String(length=50), nullable=False),
    sa.Column('venue_code', sa.String(length=50), nullable=False),
    sa.Column('is_free', sa.Boolean(), nullable=True),
    sa.Column('department_id', sa.UUID(), nullable=True),
    sa.Column('course_kind', sa.String(length=1), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['timetable_id'], ['master_timetables.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    # 10. Assessments
    op.create_table('assessments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('course_id', sa.UUID(), nullable=True),
    sa.Column('course_code', sa.String(length=50), nullable=False),
    sa.Column('course_title', sa.String(length=255), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('assessment_type', sa.Enum('INTERIM_ASSESSMENT', 'QUIZ', 'MID_SEMESTER_EXAMINATION', 'FINAL_EXAMINATION', 'PRACTICAL_ASSESSMENT', 'PROJECT_PRESENTATION', name='assessmenttype'), nullable=False),
    sa.Column('delivery_mode', sa.Enum('IN_PERSON', 'ONLINE', 'HYBRID', name='deliverymode'), nullable=False),
    sa.Column('date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('start_time', sa.String(length=5), nullable=False),
    sa.Column('end_time', sa.String(length=5), nullable=False),
    sa.Column('location', sa.String(length=255), nullable=False),
    sa.Column('venue_code', sa.String(length=50), nullable=True),
    sa.Column('cohorts', postgresql.ARRAY(postgresql.JSON(astext_type=sa.Text())), nullable=True),
    sa.Column('status', sa.Enum('DRAFT', 'SUBMITTED', 'UPCOMING', 'SHARED', 'RETURNED', 'CANCELLED', name='assessmentstatus'), nullable=True),
    sa.Column('scope', sa.Enum('CENTRAL', 'DEPARTMENT', 'FACULTY', name='assessmentscope'), nullable=True),
    sa.Column('is_shared', sa.Boolean(), nullable=True),
    sa.Column('created_by_id', sa.UUID(), nullable=False),
    sa.Column('created_by_role', sa.String(length=20), nullable=True),
    sa.Column('review_comment', sa.Text(), nullable=True),
    sa.Column('reviewed_by_id', sa.UUID(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    op.create_table('assessment_invigilators',
    sa.Column('assessment_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('role', sa.Enum('CHIEF', 'ASSISTANT', name='invigilatorrole'), nullable=False),
    sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('assessment_id', 'user_id')
    )
    
    # 11. Attendance
    op.create_table('attendance_sessions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('course_id', sa.UUID(), nullable=False),
    sa.Column('schedule_item_id', sa.UUID(), nullable=True),
    sa.Column('lecturer_id', sa.UUID(), nullable=False),
    sa.Column('date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('start_time', sa.String(length=5), nullable=False),
    sa.Column('end_time', sa.String(length=5), nullable=False),
    sa.Column('venue_code', sa.String(length=50), nullable=True),
    sa.Column('status', sa.Enum('SCHEDULED', 'LIVE', 'COMPLETED', 'MISSED', name='attendancesessionstatus'), nullable=True),
    sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('qr_secret', sa.String(length=255), nullable=True),
    sa.Column('qr_rotation_seconds', sa.Integer(), nullable=True),
    sa.Column('expected_count', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['schedule_item_id'], ['schedule_items.id'], ),
    sa.ForeignKeyConstraint(['lecturer_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    op.create_table('attendance_records',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('course_id', sa.UUID(), nullable=False),
    sa.Column('student_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.Enum('PRESENT', 'LATE', 'ABSENT', 'EXCUSED', name='attendancestatus'), nullable=True),
    sa.Column('source', sa.Enum('MANUAL_ENTRY', 'QR_SCAN', name='attendancesource'), nullable=True),
    sa.Column('recorded_by_id', sa.UUID(), nullable=False),
    sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['session_id'], ['attendance_sessions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['recorded_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_id', 'student_id')
    )
    
    # 12. Course Registration
    op.create_table('course_registrations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('student_id', sa.UUID(), nullable=False),
    sa.Column('course_id', sa.UUID(), nullable=True),
    sa.Column('custom_course_code', sa.String(length=50), nullable=True),
    sa.Column('custom_course_title', sa.String(length=255), nullable=True),
    sa.Column('semester_id', sa.UUID(), nullable=False),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.Column('registration_type', sa.Enum('CORE', 'ELECTIVE', 'RESEARCH_PROJECT', 'LAB_PRACTICAL', name='registrationtype'), nullable=True),
    sa.Column('credits', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('REGISTERED', 'DROPPED', 'PENDING_APPROVAL', name='registrationstatus'), nullable=True),
    sa.Column('source', sa.Enum('SELF', 'ROSTER_IMPORT', name='registrationsource'), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    op.create_table('student_imports',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.Enum('STUDENT_ONBOARDING', 'COURSE_ROSTER', name='importkind'), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=True),
    sa.Column('course_id', sa.UUID(), nullable=True),
    sa.Column('programme_id', sa.UUID(), nullable=True),
    sa.Column('programme_text', sa.String(length=255), nullable=True),
    sa.Column('level_text', sa.String(length=50), nullable=True),
    sa.Column('student_category', sa.String(length=50), nullable=False),
    sa.Column('academic_year', sa.String(length=20), nullable=False),
    sa.Column('semester_id', sa.UUID(), nullable=True),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('file_url', sa.String(length=500), nullable=True),
    sa.Column('row_count', sa.Integer(), nullable=True),
    sa.Column('created_count', sa.Integer(), nullable=True),
    sa.Column('updated_count', sa.Integer(), nullable=True),
    sa.Column('warning_count', sa.Integer(), nullable=True),
    sa.Column('error_count', sa.Integer(), nullable=True),
    sa.Column('status', sa.Enum('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', name='importstatus'), nullable=True),
    sa.Column('created_by_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['programme_id'], ['programmes.id'], ),
    sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    op.create_table('student_import_rows',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('import_id', sa.UUID(), nullable=False),
    sa.Column('row_number', sa.Integer(), nullable=False),
    sa.Column('raw', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('outcome', sa.Enum('CREATED', 'UPDATED', 'SKIPPED', name='importrowoutcome'), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['import_id'], ['student_imports.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    # 13. Graduation
    op.create_table('graduation_submissions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('programme_id', sa.UUID(), nullable=True),
    sa.Column('programme_text', sa.String(length=255), nullable=True),
    sa.Column('student_category', sa.String(length=50), nullable=False),
    sa.Column('academic_year', sa.String(length=20), nullable=False),
    sa.Column('declared_count', sa.Integer(), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('file_url', sa.String(length=500), nullable=True),
    sa.Column('row_count', sa.Integer(), nullable=True),
    sa.Column('status', sa.Enum('SUBMITTED', 'VALIDATED', 'RETURNED', name='graduationstatus'), nullable=True),
    sa.Column('review_comment', sa.Text(), nullable=True),
    sa.Column('reviewed_by_id', sa.UUID(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['programme_id'], ['programmes.id'], ),
    sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    op.create_table('graduation_candidates',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('submission_id', sa.UUID(), nullable=False),
    sa.Column('student_number', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('programme', sa.String(length=255), nullable=False),
    sa.Column('student_id', sa.UUID(), nullable=True),
    sa.Column('academic_clearance', sa.Boolean(), nullable=True),
    sa.Column('financial_clearance', sa.Boolean(), nullable=True),
    sa.Column('issues', postgresql.ARRAY(sa.String()), nullable=True),
    sa.ForeignKeyConstraint(['submission_id'], ['graduation_submissions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    # 14. Settings
    op.create_table('institution_settings',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organisation_name', sa.String(length=255), nullable=False),
    sa.Column('support_email', sa.String(length=255), nullable=False),
    sa.Column('office_location', sa.String(length=255), nullable=True),
    sa.Column('timezone', sa.String(length=50), nullable=True),
    sa.Column('active_semester_id', sa.UUID(), nullable=True),
    sa.Column('teaching_start', sa.String(length=5), nullable=True),
    sa.Column('teaching_end', sa.String(length=5), nullable=True),
    sa.Column('default_class_duration', sa.Integer(), nullable=True),
    sa.Column('capacity_tolerance', sa.Integer(), nullable=True),
    sa.Column('allow_weekends', sa.Boolean(), nullable=True),
    sa.Column('require_conflict_approval', sa.Boolean(), nullable=True),
    sa.Column('auto_publish_approved', sa.Boolean(), nullable=True),
    sa.Column('require_graduation_approval', sa.Boolean(), nullable=True),
    sa.Column('require_academic_clearance', sa.Boolean(), nullable=True),
    sa.Column('require_financial_clearance', sa.Boolean(), nullable=True),
    sa.Column('notify_schedule_changes', sa.Boolean(), nullable=True),
    sa.Column('notify_graduation_submissions', sa.Boolean(), nullable=True),
    sa.Column('notify_conflicts', sa.Boolean(), nullable=True),
    sa.Column('email_channel', sa.Boolean(), nullable=True),
    sa.Column('in_app_channel', sa.Boolean(), nullable=True),
    sa.Column('require_admin_two_factor', sa.Boolean(), nullable=True),
    sa.Column('session_timeout', sa.Integer(), nullable=True),
    sa.Column('audit_retention', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['active_semester_id'], ['semesters.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    op.create_table('department_settings',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('department_name', sa.String(length=255), nullable=False),
    sa.Column('department_code', sa.String(length=50), nullable=False),
    sa.Column('support_email', sa.String(length=255), nullable=True),
    sa.Column('office_location', sa.String(length=255), nullable=True),
    sa.Column('timezone', sa.String(length=50), nullable=True),
    sa.Column('teaching_start', sa.String(length=5), nullable=True),
    sa.Column('teaching_end', sa.String(length=5), nullable=True),
    sa.Column('default_class_duration', sa.Integer(), nullable=True),
    sa.Column('capacity_tolerance', sa.Integer(), nullable=True),
    sa.Column('allow_weekends', sa.Boolean(), nullable=True),
    sa.Column('require_conflict_approval', sa.Boolean(), nullable=True),
    sa.Column('auto_publish_approved', sa.Boolean(), nullable=True),
    sa.Column('notify_schedule_changes', sa.Boolean(), nullable=True),
    sa.Column('notify_graduation_submissions', sa.Boolean(), nullable=True),
    sa.Column('notify_conflicts', sa.Boolean(), nullable=True),
    sa.Column('email_channel', sa.Boolean(), nullable=True),
    sa.Column('in_app_channel', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('department_id'),
    sa.UniqueConstraint('id')
    )
    
    # 15. Supporting tables
    op.create_table('role_templates',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('permissions', sa.ARRAY(sa.String()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    op.create_table('sections',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('programme_id', sa.UUID(), nullable=False),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('course_id', sa.UUID(), nullable=True),
    sa.Column('student_ids', sa.ARRAY(sa.UUID()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['programme_id'], ['programmes.id'], ),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    op.create_table('report_jobs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('report_type', sa.String(length=100), nullable=False),
    sa.Column('academic_year', sa.String(length=20), nullable=True),
    sa.Column('semester', sa.String(length=50), nullable=True),
    sa.Column('programme_id', sa.UUID(), nullable=True),
    sa.Column('student_category', sa.String(length=50), nullable=True),
    sa.Column('date_from', sa.DateTime(timezone=True), nullable=True),
    sa.Column('date_to', sa.DateTime(timezone=True), nullable=True),
    sa.Column('format', sa.String(length=20), nullable=True),
    sa.Column('department_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('file_url', sa.String(length=500), nullable=True),
    sa.Column('row_count', sa.Integer(), nullable=True),
    sa.Column('created_by_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['programme_id'], ['programmes.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    # 16. Notifications
    op.create_table('notifications',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('recipient_id', sa.UUID(), nullable=True),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('detail', sa.Text(), nullable=False),
    sa.Column('page', sa.String(length=100), nullable=True),
    sa.Column('category', sa.Enum('SCHEDULE', 'ASSESSMENT', 'ATTENDANCE', 'GRADUATION', 'GENERAL', name='notificationcategory'), nullable=False),
    sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='notificationpriority'), nullable=True),
    sa.Column('audience_role', sa.String(length=20), nullable=True),
    sa.Column('audience_department_id', sa.UUID(), nullable=True),
    sa.Column('entity_type', sa.String(length=50), nullable=True),
    sa.Column('entity_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['audience_department_id'], ['departments.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index(op.f('ix_notifications_recipient_id'), 'notifications', ['recipient_id'])
    
    op.create_table('notification_reads',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('notification_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('read_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('notification_id', 'user_id')
    )
    
    op.create_table('notification_preferences',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('schedule_notifications', sa.Boolean(), nullable=True),
    sa.Column('assessment_notifications', sa.Boolean(), nullable=True),
    sa.Column('attendance_notifications', sa.Boolean(), nullable=True),
    sa.Column('graduation_notifications', sa.Boolean(), nullable=True),
    sa.Column('email_notifications', sa.Boolean(), nullable=True),
    sa.Column('in_app_notifications', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    
    # 17. Audit logs
    op.create_table('audit_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('actor_name', sa.String(length=255), nullable=False),
    sa.Column('actor_role', sa.String(length=20), nullable=False),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('category', sa.Enum('SCHEDULING', 'APPROVALS', 'OVERRIDES', 'ACADEMICS', 'PEOPLE', 'ASSESSMENTS', 'ATTENDANCE', 'GRADUATION', 'SETTINGS', 'AUTH', name='auditcategory'), nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=True),
    sa.Column('entity_id', sa.UUID(), nullable=True),
    sa.Column('department_id', sa.UUID(), nullable=True),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('before', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('after', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('ip_address', sa.String(length=50), nullable=True),
    sa.Column('user_agent', sa.String(length=500), nullable=True),
    sa.Column('revision', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    # 18. Password reset tokens
    op.create_table('password_reset_tokens',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token_hash', sa.String(length=255), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    
    # 19. Roles and permissions (RBAC)
    op.create_table('permissions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('code', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('module', sa.String(length=50), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id'),
    sa.UniqueConstraint('code'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_permissions_code'), 'permissions', ['code'], unique=True)
    op.create_index(op.f('ix_permissions_name'), 'permissions', ['name'], unique=True)
    
    op.create_table('roles',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('code', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_system_role', sa.Boolean(), nullable=True),
    sa.Column('is_admin_role', sa.Boolean(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_by_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id'),
    sa.UniqueConstraint('code'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_roles_code'), 'roles', ['code'], unique=True)
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)
    
    op.create_table('user_roles',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('role_id', sa.UUID(), nullable=False),
    sa.Column('assigned_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'role_id')
    )
    
    op.create_table('role_permissions',
    sa.Column('role_id', sa.UUID(), nullable=False),
    sa.Column('permission_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_table('role_permissions')
    op.drop_table('user_roles')
    op.drop_table('roles')
    op.drop_table('permissions')
    op.drop_table('password_reset_tokens')
    op.drop_table('audit_logs')
    op.drop_table('notification_preferences')
    op.drop_table('notification_reads')
    op.drop_table('notifications')
    op.drop_table('report_jobs')
    op.drop_table('sections')
    op.drop_table('role_templates')
    op.drop_table('department_settings')
    op.drop_table('institution_settings')
    op.drop_table('graduation_candidates')
    op.drop_table('graduation_submissions')
    op.drop_table('student_import_rows')
    op.drop_table('student_imports')
    op.drop_table('course_registrations')
    op.drop_table('attendance_records')
    op.drop_table('attendance_sessions')
    op.drop_table('assessment_invigilators')
    op.drop_table('assessments')
    op.drop_table('master_entries')
    op.drop_table('master_timetables')
    op.drop_table('schedule_item_groups')
    op.drop_table('schedule_items')
    op.drop_table('slot_requests')
    op.drop_table('course_cohorts')
    op.drop_table('courses')
    op.drop_table('programmes')
    op.drop_table('venues')
    op.drop_table('semesters')
    op.drop_table('users')
    op.drop_table('departments')
    
    # Drop enums
    sa.Enum(name='notificationpriority').drop(op.get_bind())
    sa.Enum(name='notificationcategory').drop(op.get_bind())
    sa.Enum(name='registrationsource').drop(op.get_bind())
    sa.Enum(name='registrationstatus').drop(op.get_bind())
    sa.Enum(name='importrowoutcome').drop(op.get_bind())
    sa.Enum(name='importstatus').drop(op.get_bind())
    sa.Enum(name='importkind').drop(op.get_bind())
    sa.Enum(name='attendancesource').drop(op.get_bind())
    sa.Enum(name='attendancestatus').drop(op.get_bind())
    sa.Enum(name='attendancesessionstatus').drop(op.get_bind())
    sa.Enum(name='graduationstatus').drop(op.get_bind())
    sa.Enum(name='assessmentstatus').drop(op.get_bind())
    sa.Enum(name='assessmentscope').drop(op.get_bind())
    sa.Enum(name='deliverymode').drop(op.get_bind())
    sa.Enum(name='assessmenttype').drop(op.get_bind())
    sa.Enum(name='scheduleitemsource').drop(op.get_bind())
    sa.Enum(name='scheduleitemstatus').drop(op.get_bind())
    sa.Enum(name='slotrequeststatus').drop(op.get_bind())
    sa.Enum(name='venuestatus').drop(op.get_bind())
    sa.Enum(name='venuetype').drop(op.get_bind())
    sa.Enum(name='coursemode').drop(op.get_bind())
    sa.Enum(name='coursetype').drop(op.get_bind())
    sa.Enum(name='programmecategory').drop(op.get_bind())
    sa.Enum(name='departmenttone').drop(op.get_bind())
