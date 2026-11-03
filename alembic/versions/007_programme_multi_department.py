"""Add programme_departments junction table for many-to-many

Revision ID: 007_programme_multi_department
Revises: 006_make_token_hash_nullable
Create Date: 2026-11-03 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = '007_programme_multi_department'
down_revision = '006_make_token_hash_nullable'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create the junction table
    op.create_table(
        'programme_departments',
        sa.Column('programme_id', sa.UUID(), nullable=False),
        sa.Column('department_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['programme_id'], ['programmes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('programme_id', 'department_id'),
    )

    # 2. Migrate existing data: copy each programme's department_id into the junction table
    op.execute(
        "INSERT INTO programme_departments (programme_id, department_id) "
        "SELECT id, department_id FROM programmes WHERE department_id IS NOT NULL"
    )

    # 3. Drop the old foreign key and column
    # Convention: when no explicit name is given, SQLAlchemy/Alembic uses {table}_{column}_fkey
    op.drop_constraint('programmes_department_id_fkey', 'programmes', type_='foreignkey')
    op.drop_column('programmes', 'department_id')


    # 4. Add index on department_id in junction table for faster lookups
    op.create_index('ix_programme_departments_department_id', 'programme_departments', ['department_id'])


def downgrade() -> None:
    # 1. Re-add the department_id column (nullable at first)
    op.add_column('programmes', sa.Column('department_id', sa.UUID(), nullable=True))

    # 2. Restore data from junction table (pick one department per programme)
    op.execute(
        "UPDATE programmes SET department_id = pd.department_id "
        "FROM (SELECT DISTINCT ON (programme_id) programme_id, department_id "
        "FROM programme_departments ORDER BY programme_id) pd "
        "WHERE programmes.id = pd.programme_id"
    )

    # 3. Make it NOT NULL and add FK back
    op.alter_column('programmes', 'department_id', nullable=False)
    op.create_foreign_key(
        'programmes_department_id_fkey', 'programmes', 'departments',
        ['department_id'], ['id'],
    )

    # 4. Drop junction table (index is dropped with it)
    op.drop_table('programme_departments')
