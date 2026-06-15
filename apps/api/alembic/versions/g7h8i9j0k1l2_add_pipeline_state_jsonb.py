"""add pipeline_state JSONB column

Revision ID: g7h8i9j0k1l2
Revises: f6g7h8i9j0k1
Create Date: 2026-06-15 07:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'g7h8i9j0k1l2'
down_revision: Union[str, None] = 'f6g7h8i9j0k1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pipeline_state JSONB column for granular stage tracking.
    
    This enables:
    - Idempotent workers (skip completed stages)
    - Resume from failed step
    - Upload Now, Process Later workflow
    - Detailed pipeline visibility in ops dashboard
    """
    # Add pipeline_state column with default empty state
    op.add_column(
        'recordings',
        sa.Column(
            'pipeline_state',
            JSONB,
            nullable=False,
            server_default=sa.text(
                "'{\"current_stage\": \"UPLOADED\", \"completed_stages\": [], \"failed_stage\": null, \"error_message\": null, \"last_updated_by\": null, \"retry_count\": {}, \"stage_timestamps\": {}}'::jsonb"
            )
        )
    )
    
    # Backfill existing recordings based on their status enum
    # This maps the current status to the appropriate pipeline state
    op.execute("""
        UPDATE recordings
        SET pipeline_state = CASE
            -- PENDING_UPLOAD: awaiting browser upload
            WHEN status = 'PENDING_UPLOAD' THEN
                '{"current_stage": "PENDING_UPLOAD", "completed_stages": [], "failed_stage": null, "error_message": null, "last_updated_by": "migration", "retry_count": {}, "stage_timestamps": {}}'::jsonb
            
            -- UPLOADED: file in R2, not yet processing
            WHEN status = 'UPLOADED' THEN
                '{"current_stage": "UPLOADED", "completed_stages": [], "failed_stage": null, "error_message": null, "last_updated_by": "migration", "retry_count": {}, "stage_timestamps": {}}'::jsonb
            
            -- PREPROCESSING: in first stage
            WHEN status = 'PREPROCESSING' THEN
                '{"current_stage": "PREPROCESSING", "completed_stages": [], "failed_stage": null, "error_message": null, "last_updated_by": "migration", "retry_count": {}, "stage_timestamps": {}}'::jsonb
            
            -- TRANSCRIBING: preprocess completed, running STT
            WHEN status = 'TRANSCRIBING' THEN
                '{"current_stage": "STT", "completed_stages": ["preprocess"], "failed_stage": null, "error_message": null, "last_updated_by": "migration", "retry_count": {}, "stage_timestamps": {}}'::jsonb
            
            -- DIARIZING: preprocess + STT completed
            WHEN status = 'DIARIZING' THEN
                '{"current_stage": "DIARIZATION", "completed_stages": ["preprocess", "stt"], "failed_stage": null, "error_message": null, "last_updated_by": "migration", "retry_count": {}, "stage_timestamps": {}}'::jsonb
            
            -- RECONCILING: preprocess + STT + diarization completed
            WHEN status = 'RECONCILING' THEN
                '{"current_stage": "RECONCILING", "completed_stages": ["preprocess", "stt", "diarization"], "failed_stage": null, "error_message": null, "last_updated_by": "migration", "retry_count": {}, "stage_timestamps": {}}'::jsonb
            
            -- SEGMENTING: turns + roles completed
            WHEN status = 'SEGMENTING' THEN
                '{"current_stage": "SEGMENTATION", "completed_stages": ["preprocess", "stt", "diarization", "turns", "roles"], "failed_stage": null, "error_message": null, "last_updated_by": "migration", "retry_count": {}, "stage_timestamps": {}}'::jsonb
            
            -- STITCHING: segmentation completed
            WHEN status = 'STITCHING' THEN
                '{"current_stage": "STITCHING", "completed_stages": ["preprocess", "stt", "diarization", "turns", "roles", "segmentation"], "failed_stage": null, "error_message": null, "last_updated_by": "migration", "retry_count": {}, "stage_timestamps": {}}'::jsonb
            
            -- ANALYZING: stitch completed
            WHEN status = 'ANALYZING' THEN
                '{"current_stage": "ANALYZING", "completed_stages": ["preprocess", "stt", "diarization", "turns", "roles", "segmentation", "stitch"], "failed_stage": null, "error_message": null, "last_updated_by": "migration", "retry_count": {}, "stage_timestamps": {}}'::jsonb
            
            -- SCORING: analyze completed
            WHEN status = 'SCORING' THEN
                '{"current_stage": "SCORING", "completed_stages": ["preprocess", "stt", "diarization", "turns", "roles", "segmentation", "stitch", "analyze"], "failed_stage": null, "error_message": null, "last_updated_by": "migration", "retry_count": {}, "stage_timestamps": {}}'::jsonb
            
            -- COMPLETED: all stages done
            WHEN status = 'COMPLETED' THEN
                '{"current_stage": "COMPLETED", "completed_stages": ["preprocess", "stt", "diarization", "turns", "roles", "segmentation", "stitch", "analyze", "scoring"], "failed_stage": null, "error_message": null, "last_updated_by": "migration", "retry_count": {}, "stage_timestamps": {}}'::jsonb
            
            -- FAILED: keep as-is, operators will inspect manually
            WHEN status = 'FAILED' THEN
                '{"current_stage": "FAILED", "completed_stages": [], "failed_stage": null, "error_message": null, "last_updated_by": "migration", "retry_count": {}, "stage_timestamps": {}}'::jsonb
            
            ELSE
                '{"current_stage": "UPLOADED", "completed_stages": [], "failed_stage": null, "error_message": null, "last_updated_by": "migration", "retry_count": {}, "stage_timestamps": {}}'::jsonb
        END
        WHERE pipeline_state = '{}'::jsonb OR pipeline_state IS NULL;
    """)


def downgrade() -> None:
    """Remove pipeline_state column.
    
    Note: This will lose all pipeline state tracking data.
    """
    op.drop_column('recordings', 'pipeline_state')
