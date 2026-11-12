"""Add programme, lecturer_name, course_title to master_entries for PG timetable support

Revision ID: 009_add_programme
Revises: 008_pg_timetable
Create Date: 2026-11-12 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = '009_add_programme'
down_revision = '008_pg_timetable'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('master_entries', sa.Column('programme', sa.String(50), nullable=True))
    op.add_column('master_entries', sa.Column('lecturer_name', sa.String(100), nullable=True))
    op.add_column('master_entries', sa.Column('course_title', sa.String(200), nullable=True))
    op.create_index('ix_master_entries_programme', 'master_entries', ['programme'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_master_entries_programme', table_name='master_entries')
    op.drop_column('master_entries', 'course_title')
    op.drop_column('master_entries', 'lecturer_name')
    op.drop_column('master_entries', 'programme')
