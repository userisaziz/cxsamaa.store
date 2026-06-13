import os
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import require_salesperson_up
from src.config import settings
from src.database import get_db
from src.models.conversation import Conversation
from src.models.recording import Recording
from src.models.user import User
from src.schemas.conversation import ConversationAnalysisResponse, ConversationResponse, PaginatedConversationsResponse
from src.services.conversation import get_analysis, get_conversation, list_conversations

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=PaginatedConversationsResponse)
async def list_conversations_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    outcome: str | None = None,
    salesperson_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    return await list_conversations(
        db,
        page=page,
        page_size=page_size,
        outcome=outcome,
        salesperson_id=salesperson_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation_detail(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    conversation = await get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/{conversation_id}/analysis", response_model=ConversationAnalysisResponse)
async def get_conversation_analysis(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    analysis = await get_analysis(db, conversation_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.get("/{conversation_id}/audio")
async def get_conversation_audio(
    conversation_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_salesperson_up),
):
    """Extract and serve the audio segment for a specific conversation.

    Uses ffmpeg to cut the relevant time range from the preprocessed
    audio file. Returns a WAV suitable for browser playback.
    """
    # Look up conversation with its recording
    result = await db.execute(
        select(Conversation, Recording)
        .join(Recording, Recording.id == Conversation.recording_id)
        .where(Conversation.id == uuid.UUID(conversation_id))
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation, recording = row

    # Prefer preprocessed WAV (16kHz mono); fall back to original file
    base_dir = Path(settings.local_upload_dir)
    preprocessed_path = base_dir / f"preprocessed/{recording.id}/audio.wav"
    if preprocessed_path.exists():
        source_path = preprocessed_path
    else:
        source_path = base_dir / recording.file_url
        if not source_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")

    # Extract segment with ffmpeg
    start_sec = conversation.start_time
    duration_sec = conversation.end_time - conversation.start_time

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        proc = subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", str(start_sec),
                "-i", str(source_path),
                "-t", str(duration_sec),
                "-ac", "1",
                "-ar", "16000",
                "-f", "wav",
                tmp_path,
            ],
            capture_output=True,
            timeout=120,
            stdin=subprocess.DEVNULL,
        )
        if proc.returncode != 0:
            os.unlink(tmp_path)
            raise HTTPException(status_code=500, detail="Audio extraction failed")
    except subprocess.TimeoutExpired:
        os.unlink(tmp_path)
        raise HTTPException(status_code=504, detail="Audio extraction timed out")

    # Schedule cleanup after response is sent
    background_tasks.add_task(os.unlink, tmp_path)

    return FileResponse(
        path=tmp_path,
        media_type="audio/wav",
        filename=f"conversation_{conversation_id}.wav",
    )
