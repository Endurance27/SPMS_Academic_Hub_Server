"""Make semester registration_deadline and graduation_deadline nullable

Revision ID: 004_nullable_deadlines
Revises: 003_new_tables_and_fixes
Create Date: 2026-10-25 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '004_nullable_deadlines'
down_revision = '003_new_tables_and_fixes'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('semesters', 'registration_deadline', existing_type=sa.DateTime(timezone=True), nullable=True)
    op.alter_column('semesters', 'graduation_deadline', existing_type=sa.DateTime(timezone=True), nullable=True)


def downgrade():
    op.alter_column('semesters', 'graduation_deadline', existing_type=sa.DateTime(timezone=True), nullable=False)
    op.alter_column('semesters', 'registration_deadline', existing_type=sa.DateTime(timezone=True), nullable=False)
