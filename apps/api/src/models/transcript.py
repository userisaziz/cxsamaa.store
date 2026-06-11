import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.sql import text as sql_text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recording_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recordings.id"), nullable=False, index=True
    )
    speaker_label: Mapped[str] = mapped_column(String(20), nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(768), nullable=True)

    # Relationships
    recording: Mapped["Recording"] = relationship(
        "Recording", back_populates="transcript_segments"
    )


class WordTranscript(Base):
    """Word-level transcript with speaker attribution and confidence scores."""
    __tablename__ = "word_transcripts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recording_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recordings.id"), nullable=False, index=True
    )
    word: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    speaker_label: Mapped[str] = mapped_column(String(20), nullable=False)
    embedding = mapped_column(Vector(768), nullable=True)

    # Relationships
    recording: Mapped["Recording"] = relationship(
        "Recording", back_populates="word_transcripts"
    )


class ConversationTurn(Base):
    """Conversation turn — merged words into speaker turns."""
    __tablename__ = "conversation_turns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recording_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recordings.id"), nullable=False, index=True
    )
    speaker_label: Mapped[str] = mapped_column(String(20), nullable=False)
    role_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=sql_text("NOW()")
    )

    # Relationships
    recording: Mapped["Recording"] = relationship(
        "Recording", back_populates="conversation_turns"
    )


class SpeakerRole(Base):
    """Speaker role classification result."""
    __tablename__ = "speaker_roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recording_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recordings.id"), nullable=False, index=True
    )
    speaker_label: Mapped[str] = mapped_column(String(20), nullable=False)
    role_label: Mapped[str] = mapped_column(String(20), nullable=False)
    classification_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=sql_text("NOW()")
    )

    # Relationships
    recording: Mapped["Recording"] = relationship(
        "Recording", back_populates="speaker_roles"
    )


class SpeakerVoiceprint(Base):
    """Voiceprint enrollment profile for known speaker identification.

    Stores speaker embeddings linked to a salesperson. Used for
    cross-conversation speaker matching — if audio matches an enrolled
    voiceprint, the speaker is identified as that salesperson.

    Engines: pyannote/embedding (primary), resemblyzer (fallback). Both free.
    """
    __tablename__ = "speaker_voiceprints"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    salesperson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("salespeople.id"), nullable=False, index=True
    )
    recording_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recordings.id"), nullable=True,
        comment="Source recording used for enrollment"
    )
    engine: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pyannote",
        comment="Voiceprint engine: pyannote, resemblyzer"
    )
    voiceprint_bytes: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True,
        comment="Serialized speaker embedding vector (float32 bytes)"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="Enrollment status: pending, enrolled, failed"
    )
    sample_duration_seconds: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Total duration of enrollment audio samples"
    )
    sample_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Number of audio samples used for enrollment"
    )
    notes: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
        comment="Optional notes about enrollment"
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=sql_text("NOW()")
    )
    enrolled_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Timestamp when enrollment was completed"
    )

    # Relationships
    salesperson: Mapped["Salesperson"] = relationship(
        "Salesperson", backref="voiceprints"
    )
