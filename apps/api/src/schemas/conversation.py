import math
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PaginatedConversationsResponse(BaseModel):
    """Paginated list of conversations with inline analysis."""
    items: list["ConversationListItem"]
    total: int
    page: int
    page_size: int
    total_pages: int


class ConversationListItem(BaseModel):
    """A single conversation row with inline analysis data for list view."""
    id: uuid.UUID
    recording_id: uuid.UUID
    salesperson_id: uuid.UUID | None = None
    start_time: float
    end_time: float
    duration_seconds: float | None = None
    segment_count: int
    summary: str | None = None
    recorded_at: datetime | None = None
    created_at: datetime
    # Inline analysis fields
    outcome: str | None = None
    confidence: int | None = None
    intent: str | None = None
    scores: dict | None = None

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: uuid.UUID
    recording_id: uuid.UUID
    start_time: float
    end_time: float
    segment_count: int
    summary: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationAnalysisResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    intent: str | None = None
    customer_expectation: str | None = None
    products: list[str] | None = None
    budget: str | None = None
    objections: list[Any] | None = None
    competitors: list[str] | None = None
    closing_attempt: bool = False
    outcome: str | None = None
    loss_reason: str | None = None
    confidence: int | None = None
    scores: dict | None = None
    summary: str | None = None
    coaching_notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
