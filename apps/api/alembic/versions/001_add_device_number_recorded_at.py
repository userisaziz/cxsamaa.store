"""add device_number and recorded_at fields

Revision ID: 001_add_device_number_recorded_at
Revises:
Create Date: 2026-06-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001_add_device_number_recorded_at"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add device_number to salespeople table
    op.add_column(
        "salespeople",
        sa.Column("device_number", sa.String(100), nullable=True),
    )

    # Add recorded_at to recordings table
    op.add_column(
        "recordings",
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recordings", "recorded_at")
    op.drop_column("salespeople", "device_number")
