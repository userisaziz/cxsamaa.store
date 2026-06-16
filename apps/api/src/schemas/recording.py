import uuid
from datetime import datetime

from pydantic import BaseModel


class RecordingResponse(BaseModel):
    id: uuid.UUID
    salesperson_id: uuid.UUID
    file_url: str
    file_size: int | None = None
    duration_seconds: int | None = None
    format: str
    status: str
    error_message: str | None = None
    uploaded_at: datetime
    recorded_at: datetime | None = None
    processed_at: datetime | None = None
    pipeline_state: dict | None = None

    model_config = {"from_attributes": True}


class RecordingStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    error_message: str | None = None
    transcript_segment_count: int = 0
    conversation_count: int = 0
    
    model_config = {"from_attributes": True}


class TranscriptSegmentResponse(BaseModel):
    id: uuid.UUID
    recording_id: uuid.UUID
    speaker_label: str
    role_label: str | None = None
    role_confidence: float | None = None
    start_time: float
    end_time: float
    text: str

    model_config = {"from_attributes": True}


class ConversationSummaryResponse(BaseModel):
    id: uuid.UUID
    recording_id: uuid.UUID
    start_time: float
    end_time: float
    segment_count: int
    summary: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecordingSummaryResponse(BaseModel):
    """Recording-level summary with AI insights across all conversations."""
    id: str
    status: str
    duration_seconds: int | None = None
    total_conversations: int = 0
    top_intent: str | None = None
    top_objection: str | None = None
    missed_opportunities: int = 0
    outcomes: dict = {}
    avg_confidence: float | None = None


class PaginatedRecordingsResponse(BaseModel):
    """Paginated list of recordings."""
    items: list[RecordingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SpeakerRoleCorrectionRequest(BaseModel):
    """Request to manually correct a speaker's role classification."""
    speaker_label: str
    corrected_role: str  # "Salesperson" or "Customer"


class SpeakerRoleSummary(BaseModel):
    """Summary of a single speaker's role classification for a recording."""
    speaker_label: str
    role_label: str
    classification_method: str | None = None
    confidence: float | None = None
    is_manually_corrected: bool = False


class SpeakerRolesResponse(BaseModel):
    """Full speaker role classification summary for a recording."""
    recording_id: str
    speakers: list[SpeakerRoleSummary]
    total_speakers: int = 0
    manually_corrected_count: int = 0
    primary_method: str | None = None  # Most common classification method


class PresignedUploadRequest(BaseModel):
    """Request to generate a pre-signed upload URL."""
    filename: str
    content_type: str
    salesperson_id: str
    recorded_at: str | None = None


class PresignedUploadResponse(BaseModel):
    """Response containing pre-signed upload URL."""
    upload_url: str
    recording_id: str
    file_key: str


class ConfirmUploadRequest(BaseModel):
    """Request to confirm a direct-to-R2 upload."""
    file_size: int | None = None
