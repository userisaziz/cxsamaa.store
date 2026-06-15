"""add PENDING_UPLOAD recording status

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-06-15 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6g7h8i9j0k1'
down_revision: Union[str, None] = 'e5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add PENDING_UPLOAD status to recordingstatus enum.
    
    This status is used when a pre-signed upload URL has been generated
    but the browser hasn't finished uploading the file to R2 yet.
    """
    op.execute("ALTER TYPE recordingstatus ADD VALUE IF NOT EXISTS 'PENDING_UPLOAD'")


def downgrade() -> None:
    """Remove PENDING_UPLOAD status from recordingstatus enum.
    
    Note: PostgreSQL doesn't support removing enum values directly,
    so this is a no-op downgrade.
    """
    pass  # Can't remove enum values in PostgreSQL
