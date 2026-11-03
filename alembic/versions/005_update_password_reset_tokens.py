"""Add missing columns to password_reset_tokens

Revision ID: 005_update_password_reset_tokens
Revises: 004_nullable_deadlines
Create Date: 2026-11-03 07:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '005_update_password_reset_tokens'
down_revision = '004_nullable_deadlines'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('password_reset_tokens', 'token_hash', nullable=True)

    op.add_column('password_reset_tokens', sa.Column('code', sa.String(length=6), nullable=True))
    op.add_column('password_reset_tokens', sa.Column('token', sa.String(length=255), nullable=True))
    op.add_column('password_reset_tokens', sa.Column('is_used', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('password_reset_tokens', sa.Column('ip_address', sa.String(length=45), nullable=True))
    op.add_column('password_reset_tokens', sa.Column('user_agent', sa.String(length=500), nullable=True))

    op.create_index('ix_password_reset_tokens_code', 'password_reset_tokens', ['code'])
    op.create_unique_constraint('uq_password_reset_tokens_token', 'password_reset_tokens', ['token'])

    # Mark existing rows with used_at as used
    op.execute("UPDATE password_reset_tokens SET is_used = true WHERE used_at IS NOT NULL")


def downgrade() -> None:
    op.drop_constraint('uq_password_reset_tokens_token', 'password_reset_tokens', type_='unique')
    op.drop_index('ix_password_reset_tokens_code', table_name='password_reset_tokens')
    op.drop_column('password_reset_tokens', 'user_agent')
    op.drop_column('password_reset_tokens', 'ip_address')
    op.drop_column('password_reset_tokens', 'is_used')
    op.drop_column('password_reset_tokens', 'token')
    op.drop_column('password_reset_tokens', 'code')

    op.alter_column('password_reset_tokens', 'token_hash', nullable=False)
