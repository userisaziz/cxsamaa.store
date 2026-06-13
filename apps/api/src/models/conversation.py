import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recording_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recordings.id"), nullable=False, index=True
    )
    salesperson_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("salespeople.id"), nullable=True, index=True
    )
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    segment_count: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
        comment="Path to pre-stitched conversation audio file in storage",
    )
    recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    recording: Mapped["Recording"] = relationship(
        "Recording", back_populates="conversations"
    )
    salesperson: Mapped["Salesperson | None"] = relationship(
        "Salesperson", back_populates="conversations"
    )
    analysis: Mapped["ConversationAnalysis | None"] = relationship(
        "ConversationAnalysis", back_populates="conversation", uselist=False
    )


class ConversationAnalysis(Base):
    __tablename__ = "conversation_analysis"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), unique=True, nullable=False
    )
    intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    products: Mapped[list | None] = mapped_column(JSONB, default=lambda: [])
    budget: Mapped[str | None] = mapped_column(String(100), nullable=True)
    objections: Mapped[list | None] = mapped_column(JSONB, default=lambda: [])
    competitors: Mapped[list | None] = mapped_column(JSONB, default=lambda: [])
    closing_attempt: Mapped[bool] = mapped_column(Boolean, default=False)
    outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    loss_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_expectation: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    coaching_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="analysis"
    )
