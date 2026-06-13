"""add audio_url to conversations and RECONCILING/STITCHING statuses

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-06-14 12:00:00.000000

Adds:
- conversations.audio_url: path to pre-stitched conversation audio file
- RecordingStatus enum values: RECONCILING, STITCHING (for pipeline Stage 6.5)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f6g7h8i9j0"
down_revision: Union[str, None] = "d4e5f6g7h8i9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add audio_url column to conversations table
    op.add_column(
        "conversations",
        sa.Column(
            "audio_url",
            sa.String(500),
            nullable=True,
            comment="Path to pre-stitched conversation audio file in storage",
        ),
    )

    # Add new RecordingStatus enum values
    # PostgreSQL requires ALTER TYPE ... ADD VALUE for enum extensions
    op.execute("ALTER TYPE recordingstatus ADD VALUE IF NOT EXISTS 'RECONCILING'")
    op.execute("ALTER TYPE recordingstatus ADD VALUE IF NOT EXISTS 'STITCHING'")


def downgrade() -> None:
    # Remove audio_url column
    op.drop_column("conversations", "audio_url")

    # Note: PostgreSQL does not support removing values from an enum type.
    # The RECONCILING and STITCHING values will remain in the enum after downgrade.
    # This is acceptable since they are only used as transient pipeline states.
