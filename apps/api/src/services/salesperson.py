import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation import Conversation, ConversationAnalysis
from src.models.recording import Recording
from src.models.salesperson import Salesperson
from src.schemas.salesperson import SalespersonCreate, SalespersonPerformanceResponse, SalespersonUpdate


async def list_salespeople(db: AsyncSession, store_id: str | None = None) -> list[Salesperson]:
    query = select(Salesperson)
    if store_id:
        query = query.where(Salesperson.store_id == uuid.UUID(store_id))
    result = await db.execute(query.order_by(Salesperson.created_at.desc()))
    return list(result.scalars().all())


async def get_salesperson(db: AsyncSession, salesperson_id: str) -> Salesperson | None:
    result = await db.execute(
        select(Salesperson).where(Salesperson.id == uuid.UUID(salesperson_id))
    )
    return result.scalar_one_or_none()


async def create_salesperson(db: AsyncSession, data: SalespersonCreate) -> Salesperson:
    salesperson = Salesperson(
        store_id=uuid.UUID(data.store_id),
        name=data.name,
        email=data.email,
        role=data.role,
        shift=data.shift,
        device_number=data.device_number,
    )
    db.add(salesperson)
    await db.flush()
    await db.refresh(salesperson)
    return salesperson


async def update_salesperson(
    db: AsyncSession, salesperson_id: str, data: SalespersonUpdate
) -> Salesperson | None:
    salesperson = await get_salesperson(db, salesperson_id)
    if not salesperson:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(salesperson, key, value)
    await db.flush()
    await db.refresh(salesperson)
    return salesperson


async def get_salesperson_performance(
    db: AsyncSession, salesperson_id: str
) -> SalespersonPerformanceResponse | None:
    salesperson = await get_salesperson(db, salesperson_id)
    if not salesperson:
        return None

    sid = uuid.UUID(salesperson_id)

    # Count conversations for this salesperson
    conv_count = await db.execute(
        select(func.count()).select_from(Conversation).where(
            Conversation.recording_id.in_(
                select(Recording.id).where(Recording.salesperson_id == sid)
            )
        )
    )
    total_conversations = conv_count.scalar() or 0

    # Get average scores from conversation_analysis
    # Scores are stored as JSONB: {greeting, discovery, product_knowledge, objection_handling, closing}
    score_query = select(ConversationAnalysis.scores).where(
        ConversationAnalysis.conversation_id.in_(
            select(Conversation.id).where(
                Conversation.recording_id.in_(
                    select(Recording.id).where(Recording.salesperson_id == sid)
                )
            )
        ),
        ConversationAnalysis.scores.isnot(None),
    )
    score_result = await db.execute(score_query)
    scores_list = [row[0] for row in score_result.all() if row[0]]

    if scores_list:
        avg_greeting = sum(s.get("greeting_score", 0) for s in scores_list) / len(scores_list)
        avg_discovery = sum(s.get("discovery_score", 0) for s in scores_list) / len(scores_list)
        avg_pk = sum(s.get("product_knowledge_score", 0) for s in scores_list) / len(scores_list)
        avg_oh = sum(s.get("objection_handling_score", 0) for s in scores_list) / len(scores_list)
        avg_closing = sum(s.get("closing_score", 0) for s in scores_list) / len(scores_list)
        avg_overall = (avg_greeting + avg_discovery + avg_pk + avg_oh + avg_closing) / 5
    else:
        avg_greeting = avg_discovery = avg_pk = avg_oh = avg_closing = avg_overall = None

    return SalespersonPerformanceResponse(
        salesperson_id=salesperson_id,
        name=salesperson.name,
        total_conversations=total_conversations,
        avg_greeting_score=round(avg_greeting, 1) if avg_greeting is not None else None,
        avg_discovery_score=round(avg_discovery, 1) if avg_discovery is not None else None,
        avg_product_knowledge_score=round(avg_pk, 1) if avg_pk is not None else None,
        avg_objection_handling_score=round(avg_oh, 1) if avg_oh is not None else None,
        avg_closing_score=round(avg_closing, 1) if avg_closing is not None else None,
        avg_overall_score=round(avg_overall, 1) if avg_overall is not None else None,
    )
