"""add word_transcripts table and recording.speech_regions

Revision ID: a1b2c3d4e5f6
Revises: e272c0dd7159
Create Date: 2026-06-10 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e272c0dd7159'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add speech_regions column to recordings table
    op.add_column('recordings', sa.Column('speech_regions', JSONB(), nullable=True))

    # Create word_transcripts table
    op.create_table(
        'word_transcripts',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('recording_id', sa.UUID(), sa.ForeignKey('recordings.id'), nullable=False, index=True),
        sa.Column('word', sa.String(100), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('end_time', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('speaker_label', sa.String(20), nullable=False),
        sa.Column('embedding', Vector(768), nullable=True),
    )

    # Create indexes for efficient queries
    op.create_index('idx_word_transcripts_recording', 'word_transcripts', ['recording_id'])
    op.create_index('idx_word_transcripts_time', 'word_transcripts', ['recording_id', 'start_time'])


def downgrade() -> None:
    # Drop word_transcripts table
    op.drop_index('idx_word_transcripts_time', table_name='word_transcripts')
    op.drop_index('idx_word_transcripts_recording', table_name='word_transcripts')
    op.drop_table('word_transcripts')

    # Remove speech_regions column
    op.drop_column('recordings', 'speech_regions')
