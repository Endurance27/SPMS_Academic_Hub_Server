"""Add postgraduate timetable support

Revision ID: 008_postgraduate_timetable_support
Revises: 007_programme_multi_department
Create Date: 2026-11-11 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = '008_pg_timetable'
down_revision = '007_programme_multi_department'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('master_timetables', sa.Column('category', sa.String(20), server_default='undergraduate', nullable=False))
    op.add_column('master_entries', sa.Column('start_time', sa.String(5), nullable=True))
    op.add_column('master_entries', sa.Column('end_time', sa.String(5), nullable=True))
    op.add_column('timetable_uploads', sa.Column('category', sa.String(20), server_default='undergraduate', nullable=False))


def downgrade() -> None:
    op.drop_column('timetable_uploads', 'category')
    op.drop_column('master_entries', 'end_time')
    op.drop_column('master_entries', 'start_time')
    op.drop_column('master_timetables', 'category')
