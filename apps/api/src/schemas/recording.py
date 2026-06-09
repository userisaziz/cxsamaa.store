from pydantic import BaseModel


class RecordingResponse(BaseModel):
    id: str
    salesperson_id: str
    file_url: str
    file_size: int | None = None
    duration_seconds: int | None = None
    format: str
    status: str
    error_message: str | None = None
    uploaded_at: str
    recorded_at: str | None = None
    processed_at: str | None = None

    model_config = {"from_attributes": True}


class RecordingStatusResponse(BaseModel):
    id: str
    status: str
    error_message: str | None = None

    model_config = {"from_attributes": True}


class TranscriptSegmentResponse(BaseModel):
    id: str
    recording_id: str
    speaker_label: str
    start_time: float
    end_time: float
    text: str

    model_config = {"from_attributes": True}


class ConversationSummaryResponse(BaseModel):
    id: str
    recording_id: str
    start_time: float
    end_time: float
    segment_count: int
    summary: str | None = None
    created_at: str

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
