"""Add optional meeting link to courses

Revision ID: 011_course_meeting_link
Revises: 010_delivery_mode
Create Date: 2026-11-20 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op


revision = "011_course_meeting_link"
down_revision = "010_delivery_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("meeting_link", sa.String(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column("courses", "meeting_link")
