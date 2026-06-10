import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, ForeignKey, Integer, String, Text
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
