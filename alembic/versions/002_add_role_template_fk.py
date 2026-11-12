"""Add role template foreign key to users

Revision ID: 002_add_role_template_fk
Revises: 001_initial
Create Date: 2026-10-24 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_role_template_fk'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # Add foreign key from users.role_template_id to role_templates.id
    op.create_foreign_key(
        'fk_users_role_template_id',
        'users',
        'role_templates',
        ['role_template_id'],
        ['id']
    )


def downgrade():
    # Remove foreign key
    op.drop_constraint('fk_users_role_template_id', 'users', type_='foreignkey')
