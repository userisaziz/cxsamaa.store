"""Conversation service — list, retrieve, and analyze conversations."""
import math
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.conversation import Conversation, ConversationAnalysis
from src.schemas.conversation import ConversationListItem, PaginatedConversationsResponse


async def list_conversations(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    outcome: str | None = None,
    salesperson_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> PaginatedConversationsResponse:
    """List conversations with pagination and optional filters."""
    from datetime import datetime as dt

    query = (
        select(Conversation, ConversationAnalysis)
        .outerjoin(ConversationAnalysis, ConversationAnalysis.conversation_id == Conversation.id)
    )
    count_query = select(func.count(Conversation.id))

    if outcome:
        query = query.where(ConversationAnalysis.outcome == outcome)
        count_query = count_query.join(
            ConversationAnalysis, ConversationAnalysis.conversation_id == Conversation.id
        ).where(ConversationAnalysis.outcome == outcome)

    if salesperson_id:
        query = query.where(Conversation.salesperson_id == uuid.UUID(salesperson_id))
        count_query = count_query.where(Conversation.salesperson_id == uuid.UUID(salesperson_id))

    if date_from:
        try:
            parsed_from = dt.fromisoformat(date_from)
            query = query.where(Conversation.recorded_at >= parsed_from)
            count_query = count_query.where(Conversation.recorded_at >= parsed_from)
        except ValueError:
            pass

    if date_to:
        try:
            parsed_to = dt.fromisoformat(date_to)
            query = query.where(Conversation.recorded_at <= parsed_to)
            count_query = count_query.where(Conversation.recorded_at <= parsed_to)
        except ValueError:
            pass

    # Total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    total_pages = max(1, math.ceil(total / page_size))

    # Paginated results
    query = query.order_by(Conversation.recorded_at.desc().nulls_last(), Conversation.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    items: list[ConversationListItem] = []
    for conv, analysis in rows:
        item = ConversationListItem(
            id=conv.id,
            recording_id=conv.recording_id,
            salesperson_id=conv.salesperson_id,
            start_time=conv.start_time,
            end_time=conv.end_time,
            duration_seconds=conv.duration_seconds,
            segment_count=conv.segment_count,
            summary=conv.summary,
            recorded_at=conv.recorded_at,
            created_at=conv.created_at,
            outcome=analysis.outcome if analysis else None,
            confidence=analysis.confidence if analysis else None,
            intent=analysis.intent if analysis else None,
            scores=analysis.scores if analysis else None,
        )
        items.append(item)

    return PaginatedConversationsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


async def get_conversation(db: AsyncSession, conversation_id: str) -> Conversation | None:
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.analysis))
        .where(Conversation.id == uuid.UUID(conversation_id))
    )
    return result.scalar_one_or_none()


async def get_analysis(db: AsyncSession, conversation_id: str) -> ConversationAnalysis | None:
    result = await db.execute(
        select(ConversationAnalysis).where(
            ConversationAnalysis.conversation_id == uuid.UUID(conversation_id)
        )
    )
    return result.scalar_one_or_none()
