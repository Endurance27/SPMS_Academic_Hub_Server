"""Make token_hash nullable in password_reset_tokens

Revision ID: 006_make_token_hash_nullable
Revises: 005_update_password_reset_tokens
Create Date: 2026-11-03 07:30:00.000000

"""
from alembic import op

revision = '006_make_token_hash_nullable'
down_revision = '005_update_password_reset_tokens'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('password_reset_tokens', 'token_hash', nullable=True)


def downgrade() -> None:
    op.execute("UPDATE password_reset_tokens SET token_hash = '' WHERE token_hash IS NULL")
    op.alter_column('password_reset_tokens', 'token_hash', nullable=False)
