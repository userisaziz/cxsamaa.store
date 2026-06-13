import uuid

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation import Conversation, ConversationAnalysis
from src.models.recording import Recording
from src.models.salesperson import Salesperson
from src.models.store import Store
from src.schemas.store import StoreCreate, StoreMetricsResponse, StoreUpdate


async def list_stores(db: AsyncSession, brand_id: str | None = None) -> list[Store]:
    query = select(Store)
    if brand_id:
        query = query.where(Store.brand_id == uuid.UUID(brand_id))
    result = await db.execute(query.order_by(Store.created_at.desc()))
    return list(result.scalars().all())


async def get_store(db: AsyncSession, store_id: str) -> Store | None:
    result = await db.execute(select(Store).where(Store.id == uuid.UUID(store_id)))
    return result.scalar_one_or_none()


async def create_store(db: AsyncSession, data: StoreCreate) -> Store:
    store = Store(
        name=data.name,
        brand_id=uuid.UUID(data.brand_id),
        location=data.location,
        working_hours=data.working_hours,
    )
    db.add(store)
    await db.flush()
    await db.refresh(store)
    return store


async def update_store(db: AsyncSession, store_id: str, data: StoreUpdate) -> Store | None:
    store = await get_store(db, store_id)
    if not store:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(store, key, value)
    await db.flush()
    await db.refresh(store)
    return store


async def get_store_metrics(db: AsyncSession, store_id: str) -> StoreMetricsResponse | None:
    store = await get_store(db, store_id)
    if not store:
        return None

    sid = uuid.UUID(store_id)

    # Count salespeople
    sp_count = await db.execute(
        select(func.count()).select_from(Salesperson).where(Salesperson.store_id == sid)
    )
    total_salespeople = sp_count.scalar() or 0

    # Count recordings
    rec_count = await db.execute(
        select(func.count()).select_from(Recording).where(Recording.salesperson_id.in_(
            select(Salesperson.id).where(Salesperson.store_id == sid)
        ))
    )
    total_recordings = rec_count.scalar() or 0

    # Count conversations
    conv_count = await db.execute(
        select(func.count()).select_from(Conversation).where(Conversation.recording_id.in_(
            select(Recording.id).where(Recording.salesperson_id.in_(
                select(Salesperson.id).where(Salesperson.store_id == sid)
            ))
        ))
    )
    total_conversations = conv_count.scalar() or 0

    # Average performance score
    sp_ids_result = await db.execute(
        select(Salesperson.id).where(Salesperson.store_id == sid)
    )
    sp_ids = [row[0] for row in sp_ids_result.all()]

    avg_score = None
    conversion_rate = None
    top_objection = None

    if sp_ids:
        rec_ids_q = select(Recording.id).where(Recording.salesperson_id.in_(sp_ids))

        # Avg performance score from scores JSONB
        scores_result = await db.execute(
            select(ConversationAnalysis.scores).join(Conversation).where(
                Conversation.recording_id.in_(rec_ids_q),
                ConversationAnalysis.scores.isnot(None),
            )
        )
        scores_list = [row[0] for row in scores_result.all() if row[0]]
        
        if scores_list:
            overall_scores = []
            for s in scores_list:
                if isinstance(s, dict):
                    # Collect non-None score values
                    score_values = []
                    for key in ["greeting_score", "discovery_score", "product_knowledge_score", "objection_handling_score", "closing_score"]:
                        val = s.get(key)
                        if val is not None:
                            score_values.append(val)
                    if score_values:
                        overall = sum(score_values) / len(score_values)
                        if overall > 0:
                            overall_scores.append(overall)
            if overall_scores:
                avg_score = round(sum(overall_scores) / len(overall_scores), 1)

        # Conversion rate
        if total_conversations > 0:
            sale_result = await db.execute(
                select(func.count()).select_from(ConversationAnalysis).join(Conversation).where(
                    Conversation.recording_id.in_(rec_ids_q),
                    ConversationAnalysis.outcome == "SALE_MADE",
                )
            )
            sale_count = sale_result.scalar() or 0
            conversion_rate = round(sale_count / total_conversations * 100, 1)

        # Top objection
        objections_result = await db.execute(
            select(ConversationAnalysis.objections).join(Conversation).where(
                Conversation.recording_id.in_(rec_ids_q),
                ConversationAnalysis.objections.isnot(None),
            )
        )
        all_objections: list[str] = []
        for row in objections_result.all():
            if row[0]:
                for obj in row[0]:
                    if isinstance(obj, dict):
                        issue = obj.get("issue", "")
                        if issue:
                            all_objections.append(issue)
                    elif isinstance(obj, str) and obj:
                        all_objections.append(obj)
        if all_objections:
            top_objection = Counter(all_objections).most_common(1)[0][0]

    return StoreMetricsResponse(
        store_id=store_id,
        name=store.name,
        total_salespeople=total_salespeople,
        total_recordings=total_recordings,
        total_conversations=total_conversations,
        avg_performance_score=avg_score,
        conversion_rate=conversion_rate,
        top_objection=top_objection,
    )
