"""add chunk_manifest to recordings

Revision ID: d4e5f6g7h8i9
Revises: 14ff67e4c4bf
Create Date: 2026-06-13 12:00:00.000000

Adds a JSONB column to store chunk boundaries computed during preprocessing.
Enables parallel chunk processing for long audio recordings.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, Sequence[str], None] = '14ff67e4c4bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('recordings', sa.Column('chunk_manifest', postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('recordings', 'chunk_manifest')
