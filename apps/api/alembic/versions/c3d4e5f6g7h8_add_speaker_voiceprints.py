"""add speaker voiceprints table

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2025-01-15

Creates the speaker_voiceprints table for Phase C voiceprint enrollment.
Stores speaker embedding vectors linked to salespeople, enabling
cross-conversation speaker identification. Free engines: pyannote, resemblyzer.
"""
from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6g7h8"
down_revision = "b2c3d4e5f6g7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "speaker_voiceprints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("salesperson_id", sa.Uuid(), nullable=False),
        sa.Column(
            "recording_id",
            sa.Uuid(),
            nullable=True,
            comment="Source recording used for enrollment",
        ),
        sa.Column(
            "engine",
            sa.String(50),
            nullable=False,
            server_default="pyannote",
            comment="Voiceprint engine: pyannote, resemblyzer",
        ),
        sa.Column(
            "voiceprint_bytes",
            sa.LargeBinary(),
            nullable=True,
            comment="Serialized speaker embedding vector (float32 bytes)",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
            comment="Enrollment status: pending, enrolled, failed",
        ),
        sa.Column(
            "sample_duration_seconds",
            sa.Float(),
            nullable=True,
            comment="Total duration of enrollment audio samples",
        ),
        sa.Column(
            "sample_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of audio samples used for enrollment",
        ),
        sa.Column(
            "notes",
            sa.String(500),
            nullable=True,
            comment="Optional notes about enrollment",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "enrolled_at",
            sa.DateTime(),
            nullable=True,
            comment="Timestamp when enrollment was completed",
        ),
        sa.ForeignKeyConstraint(["salesperson_id"], ["salespeople.id"]),
        sa.ForeignKeyConstraint(["recording_id"], ["recordings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_speaker_voiceprints_salesperson_id",
        "speaker_voiceprints",
        ["salesperson_id"],
    )
    op.create_index(
        "ix_speaker_voiceprints_engine_status",
        "speaker_voiceprints",
        ["engine", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_speaker_voiceprints_engine_status", table_name="speaker_voiceprints")
    op.drop_index("ix_speaker_voiceprints_salesperson_id", table_name="speaker_voiceprints")
    op.drop_table("speaker_voiceprints")
