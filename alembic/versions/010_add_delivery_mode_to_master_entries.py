"""Add delivery_mode to master_entries

Revision ID: 010_delivery_mode
Revises: 009_add_programme
Create Date: 2026-11-13 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = '010_delivery_mode'
down_revision = '009_add_programme'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('master_entries', sa.Column('delivery_mode', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('master_entries', 'delivery_mode')
