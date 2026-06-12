import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class RecordingStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PREPROCESSING = "PREPROCESSING"
    TRANSCRIBING = "TRANSCRIBING"
    DIARIZING = "DIARIZING"
    SEGMENTING = "SEGMENTING"
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
