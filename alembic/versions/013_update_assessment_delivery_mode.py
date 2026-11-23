"""Replace Hybrid with Take-home Assignment and Term Paper in DeliveryMode enum

Revision ID: 013_assessment_delivery_mode
Revises: 012_master_entry_meeting_link
Create Date: 2026-11-11 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = "013_assessment_delivery_mode"
down_revision = "012_master_entry_meeting_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL does not allow removing enum values directly.
    # Strategy:
    #   1. Add the two new values to the existing type.
    #   2. Migrate any existing HYBRID rows to IN_PERSON.
    #   3. Change the column to a plain VARCHAR so the old type can be dropped.
    #   4. Drop the old enum type.
    #   5. Create a fresh enum with exactly the four desired values.
    #   6. Cast the column back to the new enum.

    # Step 1 — add new labels (safe; ADD VALUE cannot be rolled back inside a
    # transaction on older Postgres, but we isolate this before the DDL changes)
    op.execute("ALTER TYPE deliverymode ADD VALUE IF NOT EXISTS 'TAKE_HOME_ASSIGNMENT'")
    op.execute("ALTER TYPE deliverymode ADD VALUE IF NOT EXISTS 'TERM_PAPER'")

    # Step 2 — migrate existing HYBRID rows before we remove that value
    op.execute(
        "UPDATE assessments SET delivery_mode = 'IN_PERSON' "
        "WHERE delivery_mode::text = 'HYBRID'"
    )

    # Step 3 — detach the column from the enum so we can replace the type
    op.execute(
        "ALTER TABLE assessments "
        "ALTER COLUMN delivery_mode TYPE VARCHAR(50) "
        "USING delivery_mode::text"
    )

    # Step 4 — drop the old enum (all four values, including the two we just added)
    op.execute("DROP TYPE deliverymode")

    # Step 5 — create the definitive enum with the four correct values
    op.execute(
        "CREATE TYPE deliverymode AS ENUM "
        "('IN_PERSON', 'ONLINE', 'TAKE_HOME_ASSIGNMENT', 'TERM_PAPER')"
    )

    # Step 6 — restore the column to the new enum type
    op.execute(
        "ALTER TABLE assessments "
        "ALTER COLUMN delivery_mode TYPE deliverymode "
        "USING delivery_mode::deliverymode"
    )


def downgrade() -> None:
    # Reverse: convert TAKE_HOME_ASSIGNMENT and TERM_PAPER back to HYBRID

    op.execute(
        "ALTER TABLE assessments "
        "ALTER COLUMN delivery_mode TYPE VARCHAR(50) "
        "USING delivery_mode::text"
    )

    op.execute("DROP TYPE deliverymode")

    op.execute(
        "CREATE TYPE deliverymode AS ENUM "
        "('IN_PERSON', 'ONLINE', 'HYBRID')"
    )

    op.execute(
        "UPDATE assessments SET delivery_mode = 'HYBRID' "
        "WHERE delivery_mode IN ('TAKE_HOME_ASSIGNMENT', 'TERM_PAPER')"
    )

    op.execute(
        "ALTER TABLE assessments "
        "ALTER COLUMN delivery_mode TYPE deliverymode "
        "USING delivery_mode::deliverymode"
    )
