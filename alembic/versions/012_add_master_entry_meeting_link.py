"""Add optional meeting link to master timetable entries

Revision ID: 012_master_entry_meeting_link
Revises: 011_course_meeting_link
Create Date: 2026-11-21 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op


revision = "012_master_entry_meeting_link"
down_revision = "011_course_meeting_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("master_entries", sa.Column("meeting_link", sa.String(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column("master_entries", "meeting_link")
