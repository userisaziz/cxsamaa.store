import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class RecordingStatus(str, enum.Enum):
    PENDING_UPLOAD = "PENDING_UPLOAD"  # Pre-signed URL generated, awaiting browser upload
    UPLOADED = "UPLOADED"  # File confirmed in R2, ready for processing
    PREPROCESSING = "PREPROCESSING"
    TRANSCRIBING = "TRANSCRIBING"
    DIARIZING = "DIARIZING"
    RECONCILING = "RECONCILING"
    SEGMENTING = "SEGMENTING"
    STITCHING = "STITCHING"
    ANALYZING = "ANALYZING"
    SCORING = "SCORING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    salesperson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("salespeople.id"), nullable=False
    )
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[RecordingStatus] = mapped_column(
        Enum(RecordingStatus), nullable=False, default=RecordingStatus.UPLOADED
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    silence_gaps: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    speech_regions: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # VAD-detected speech-active regions
    chunk_manifest: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Chunk boundaries for parallel processing
    pipeline_state: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text(
            "'{\"current_stage\": \"UPLOADED\", \"completed_stages\": [], \"failed_stage\": null, \"error_message\": null, \"last_updated_by\": null, \"retry_count\": {}, \"stage_timestamps\": {}}'::jsonb"
        )
    )

    # Relationships
    salesperson: Mapped["Salesperson"] = relationship(
        "Salesperson", back_populates="recordings"
    )
    transcript_segments: Mapped[list["TranscriptSegment"]] = relationship(
        "TranscriptSegment", back_populates="recording", cascade="all, delete-orphan"
    )
    word_transcripts: Mapped[list["WordTranscript"]] = relationship(
        "WordTranscript", back_populates="recording", cascade="all, delete-orphan"
    )
    conversation_turns: Mapped[list["ConversationTurn"]] = relationship(
        "ConversationTurn", back_populates="recording", cascade="all, delete-orphan"
    )
    role_corrections: Mapped[list["SpeakerRoleCorrection"]] = relationship(
        "SpeakerRoleCorrection", back_populates="recording", cascade="all, delete-orphan"
    )
    speaker_roles: Mapped[list["SpeakerRole"]] = relationship(
        "SpeakerRole", back_populates="recording", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="recording", cascade="all, delete-orphan"
    )

    # Pipeline state helper methods
    def get_pipeline_state(self) -> dict:
        """Get the current pipeline state."""
        return self.pipeline_state or {}

    def update_pipeline_state(self, updates: dict) -> None:
        """Merge updates into pipeline state."""
        state = self.pipeline_state or {}
        state.update(updates)
        self.pipeline_state = state

    def mark_stage_complete(self, stage_name: str) -> None:
        """Mark a pipeline stage as completed."""
        from datetime import datetime, timezone
        
        state = self.pipeline_state or {}
        completed = state.get("completed_stages", [])
        if stage_name not in completed:
            completed.append(stage_name)
        
        timestamps = state.get("stage_timestamps", {})
        timestamps[stage_name] = datetime.now(timezone.utc).isoformat()
        
        state["completed_stages"] = completed
        state["stage_timestamps"] = timestamps
        state["current_stage"] = stage_name
        state["failed_stage"] = None
        state["error_message"] = None
        self.pipeline_state = state

    def mark_stage_failed(self, stage_name: str, error: str) -> None:
        """Mark a pipeline stage as failed."""
        state = self.pipeline_state or {}
        state["failed_stage"] = stage_name
        state["error_message"] = error
        state["current_stage"] = "FAILED"
        self.pipeline_state = state

    def is_stage_completed(self, stage_name: str) -> bool:
        """Check if a stage has been completed."""
        state = self.pipeline_state or {}
        return stage_name in state.get("completed_stages", [])
