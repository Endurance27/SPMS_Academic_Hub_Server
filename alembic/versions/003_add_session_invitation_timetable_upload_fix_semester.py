"""Add sessions, invitations, timetable_uploads tables; fix semester is_active constraint

Revision ID: 003_new_tables_and_fixes
Revises: 002_add_role_template_fk
Create Date: 2026-10-25 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '003_new_tables_and_fixes'
down_revision = '002_add_role_template_fk'
branch_labels = None
depends_on = None


def _table_exists(name):
    bind = op.get_bind()
    insp = inspect(bind)
    return name in insp.get_table_names()


def upgrade():
    if not _table_exists('sessions'):
        op.create_table('sessions',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=False),
            sa.Column('user_agent', sa.String(length=500), nullable=True),
            sa.Column('ip_address', sa.String(length=45), nullable=True),
            sa.Column('location', sa.String(length=255), nullable=True),
            sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('id')
        )

    if not _table_exists('invitations'):
        op.create_table('invitations',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=False),
            sa.Column('token_hash', sa.String(length=255), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('id')
        )
        op.create_index(op.f('ix_invitations_token_hash'), 'invitations', ['token_hash'], unique=True)

    if not _table_exists('timetable_uploads'):
        op.create_table('timetable_uploads',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('semester_id', sa.UUID(), nullable=False),
            sa.Column('level', sa.Integer(), nullable=False),
            sa.Column('filename', sa.String(length=255), nullable=False),
            sa.Column('uploaded_by_id', sa.UUID(), nullable=False),
            sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('entry_count', sa.Integer(), nullable=True),
            sa.Column('kind', sa.String(length=20), nullable=False),
            sa.Column('department_id', sa.UUID(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['semester_id'], ['semesters.id']),
            sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id']),
            sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('id')
        )

    # Fix semester is_active: drop the broken UNIQUE constraint, add partial unique index
    try:
        op.drop_constraint('semesters_is_active_key', 'semesters', type_='unique')
    except Exception:
        pass
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_semesters_active_unique ON semesters (is_active) WHERE is_active = true"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_semesters_active_unique")
    try:
        op.create_unique_constraint('semesters_is_active_key', 'semesters', ['is_active'])
    except Exception:
        pass
    op.drop_table('timetable_uploads')
    op.drop_index(op.f('ix_invitations_token_hash'), table_name='invitations')
    op.drop_table('invitations')
    op.drop_table('sessions')
