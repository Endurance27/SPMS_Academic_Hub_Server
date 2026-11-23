"""Fix attendance_records.status enum type name mismatch

The column was created with a type named 'attendancestatus' but the
SQLAlchemy model generates SQL that casts to 'attendancerecordstatus'.
This migration renames the DB type to match the ORM expectation.

Also renames 'attendancesource' → 'attendancerecordsource' for the
source column, keeping parity with the Python enum class names.

Revision ID: 014_fix_attendance_record_status
Revises: 013_assessment_delivery_mode
Create Date: 2026-11-23 00:00:00.000000
"""
from alembic import op

revision = "014_fix_attendance_record_status"
down_revision = "013_assessment_delivery_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename the status enum used by attendance_records
    # 'attendancestatus' → 'attendancerecordstatus'
    op.execute("ALTER TYPE attendancestatus RENAME TO attendancerecordstatus")

    # Rename the source enum used by attendance_records
    # 'attendancesource' → 'attendancerecordsource'
    op.execute("ALTER TYPE attendancesource RENAME TO attendancerecordsource")


def downgrade() -> None:
    op.execute("ALTER TYPE attendancerecordstatus RENAME TO attendancestatus")
    op.execute("ALTER TYPE attendancerecordsource RENAME TO attendancesource")
