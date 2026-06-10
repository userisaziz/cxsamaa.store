"""add conversation_turns and speaker_roles tables

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-10 14:00:00.000000

This migration adds support for:
1. conversation_turns table — stores merged speaker turns from word-level transcripts
2. speaker_roles table — stores role classification results (Salesperson/Customer)
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create conversation_turns table
    op.create_table(
        'conversation_turns',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('recording_id', sa.UUID(), sa.ForeignKey('recordings.id'), nullable=False, index=True),
        sa.Column('speaker_label', sa.String(20), nullable=False),
        sa.Column('role_label', sa.String(20), nullable=True),
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('end_time', sa.Float(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Create speaker_roles table
    op.create_table(
        'speaker_roles',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('recording_id', sa.UUID(), sa.ForeignKey('recordings.id'), nullable=False, index=True),
        sa.Column('speaker_label', sa.String(20), nullable=False),
        sa.Column('role_label', sa.String(20), nullable=False),
        sa.Column('classification_method', sa.String(20), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Create performance indexes
    op.create_index('idx_conversation_turns_recording', 'conversation_turns', ['recording_id'])
    op.create_index('idx_conversation_turns_time', 'conversation_turns', ['recording_id', 'start_time'])
    op.create_index('idx_speaker_roles_recording', 'speaker_roles', ['recording_id'])


def downgrade() -> None:
    # Drop tables (indexes are dropped automatically with tables)
    op.drop_table('speaker_roles')
    op.drop_table('conversation_turns')
