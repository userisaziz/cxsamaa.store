"""Analytics aggregation service — computes overview and comparison data."""
import uuid
from collections import Counter
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation import Conversation, ConversationAnalysis
from src.models.metrics import DailyMetrics
from src.models.recording import Recording
from src.models.salesperson import Salesperson
from src.models.store import Store
from src.schemas.analytics import (
    AnalyticsOverviewResponse,
    AnalyticsSalespeopleResponse,
    FunnelStage,
    ObjectionCount,
    OutcomeCount,
    SalespersonComparisonItem,
    StoreComparisonItem,
    TrendPoint,
)


async def _get_recording_ids_for_scope(
    db: AsyncSession,
    brand_id: str | None = None,
    store_id: str | None = None,
    salesperson_id: str | None = None,
) -> list[uuid.UUID]:
    """Get recording IDs scoped to a brand, store, or salesperson."""
    query = select(Recording.id)

    if salesperson_id:
        # Direct salesperson scope
        query = query.where(Recording.salesperson_id == uuid.UUID(salesperson_id))
    elif store_id:
        sp_ids_q = select(Salesperson.id).where(
            Salesperson.store_id == uuid.UUID(store_id)
        )
        query = query.where(Recording.salesperson_id.in_(sp_ids_q))
    elif brand_id:
        store_ids_q = select(Store.id).where(
            Store.brand_id == uuid.UUID(brand_id)
        )
        sp_ids_q = select(Salesperson.id).where(
            Salesperson.store_id.in_(store_ids_q)
        )
        query = query.where(Recording.salesperson_id.in_(sp_ids_q))

    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def get_analytics_overview(
    db: AsyncSession,
    brand_id: str | None = None,
    store_id: str | None = None,
    salesperson_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> AnalyticsOverviewResponse:
    """Compute a full analytics overview for a brand, store, or salesperson."""
    rec_ids = await _get_recording_ids_for_scope(db, brand_id, store_id, salesperson_id)

    if not rec_ids:
        return AnalyticsOverviewResponse(
            outcome_distribution=[],
            top_objections=[],
            funnel_stages=[
                FunnelStage(stage="Conversations", count=0),
                FunnelStage(stage="Closing Attempts", count=0),
                FunnelStage(stage="Sales Made", count=0),
            ],
            score_trend=[],
            volume_trend=[],
            store_comparison=[],
            total_conversations=0,
            avg_confidence=None,
            conversion_rate=None,
        )

    # --- Conversation IDs in scope ---
    conv_ids_q = select(Conversation.id).where(
        Conversation.recording_id.in_(rec_ids)
    )

    # --- 1. Outcome distribution ---
    outcome_q = select(
        ConversationAnalysis.outcome, func.count(ConversationAnalysis.id)
    ).where(
        ConversationAnalysis.conversation_id.in_(conv_ids_q),
        ConversationAnalysis.outcome.isnot(None),
    ).group_by(ConversationAnalysis.outcome)
    outcome_result = await db.execute(outcome_q)
    outcome_distribution = [
        OutcomeCount(outcome=row[0], count=row[1])
        for row in outcome_result.all()
    ]

    # --- 2. Top objections ---
    objections_q = select(ConversationAnalysis.objections).where(
        ConversationAnalysis.conversation_id.in_(conv_ids_q),
        ConversationAnalysis.objections.isnot(None),
        ConversationAnalysis.objections != func.jsonb_build_array(),  # JSONB empty array
    )
    objections_result = await db.execute(objections_q)
    objection_counter: Counter = Counter()
    for (objections_list,) in objections_result.all():
        if isinstance(objections_list, list):
            for obj in objections_list:
                if isinstance(obj, dict):
                    issue = obj.get("issue", "")
                    if issue:
                        objection_counter[issue] += 1
                elif isinstance(obj, str) and obj:
                    objection_counter[obj] += 1
    top_objections = [
        ObjectionCount(objection=obj, count=cnt)
        for obj, cnt in objection_counter.most_common(10)
    ]

    # --- 3. Funnel stages ---
    total_conv_q = select(func.count()).select_from(Conversation).where(
        Conversation.recording_id.in_(rec_ids)
    )
    total_conv = (await db.execute(total_conv_q)).scalar() or 0

    closing_q = select(func.count()).select_from(ConversationAnalysis).where(
        ConversationAnalysis.conversation_id.in_(conv_ids_q),
        ConversationAnalysis.closing_attempt == True,  # noqa: E712
    )
    closing_count = (await db.execute(closing_q)).scalar() or 0

    sales_q = select(func.count()).select_from(ConversationAnalysis).where(
        ConversationAnalysis.conversation_id.in_(conv_ids_q),
        ConversationAnalysis.outcome == "SALE_MADE",
    )
    sales_count = (await db.execute(sales_q)).scalar() or 0

    funnel_stages = [
        FunnelStage(stage="Conversations", count=total_conv),
        FunnelStage(stage="Closing Attempts", count=closing_count),
        FunnelStage(stage="Sales Made", count=sales_count),
    ]

    # --- 4. Score trend (daily) ---
    if not date_from:
        date_from = date.today() - timedelta(days=30)
    if not date_to:
        date_to = date.today()

    # Determine entity_id/entity_type for daily metrics lookup
    score_trend: list[TrendPoint] = []
    volume_trend: list[TrendPoint] = []

    if salesperson_id:
        entity_id = uuid.UUID(salesperson_id)
        entity_type = "SALESPERSON"
    elif store_id:
        entity_id = uuid.UUID(store_id)
        entity_type = "STORE"
    elif brand_id:
        entity_id = uuid.UUID(brand_id)
        entity_type = "BRAND"
    else:
        entity_id = None
        entity_type = None

    if entity_id and entity_type:
        trend_q = select(DailyMetrics).where(
            DailyMetrics.entity_id == entity_id,
            DailyMetrics.entity_type == entity_type,
            DailyMetrics.date >= date_from,
            DailyMetrics.date <= date_to,
        ).order_by(DailyMetrics.date.asc())
        trend_result = await db.execute(trend_q)
        daily_metrics = list(trend_result.scalars().all())

        score_trend = [
            TrendPoint(
                date=m.date.isoformat(),
                avg_score=m.avg_score,
                conversion_rate=m.conversion_rate,
            )
            for m in daily_metrics
        ]
        volume_trend = [
            TrendPoint(
                date=m.date.isoformat(),
                conversation_count=m.conversation_count,
            )
            for m in daily_metrics
        ]

    # If no daily metrics, build from conversation-level data as fallback
    if not score_trend and not volume_trend:
        # Fallback: aggregate from ConversationAnalysis per day
        fallback_q = select(
            func.date(Conversation.created_at).label("day"),
            func.count(Conversation.id),
        ).where(
            Conversation.recording_id.in_(rec_ids),
        ).group_by(func.date(Conversation.created_at)).order_by(
            func.date(Conversation.created_at)
        )
        fallback_result = await db.execute(fallback_q)
        volume_rows = fallback_result.all()
        
        # Get scores separately (need to join ConversationAnalysis)
        scores_q = select(
            func.date(Conversation.created_at).label("day"),
            ConversationAnalysis.scores,
        ).join(
            ConversationAnalysis,
            ConversationAnalysis.conversation_id == Conversation.id,
        ).where(
            Conversation.recording_id.in_(rec_ids),
            ConversationAnalysis.scores.isnot(None),
        ).order_by(func.date(Conversation.created_at))
        scores_result = await db.execute(scores_q)
        
        # Build day -> scores mapping
        day_scores: dict = {}
        for day, scores in scores_result.all():
            if day not in day_scores:
                day_scores[day] = []
            if isinstance(scores, dict):
                day_scores[day].append(scores)
        
        for day, conv_count in volume_rows:
            if day:
                volume_trend.append(TrendPoint(
                    date=str(day),
                    conversation_count=conv_count or 0,
                ))
                
                # Calculate average overall score from scores JSONB
                avg_score_val = None
                if day in day_scores and day_scores[day]:
                    overall_scores = []
                    for s in day_scores[day]:
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
                        avg_score_val = sum(overall_scores) / len(overall_scores)
                
                score_trend.append(TrendPoint(
                    date=str(day),
                    avg_score=round(avg_score_val, 1) if avg_score_val else None,
                ))

    # --- 5. Avg confidence + conversion rate ---
    avg_conf_q = select(func.avg(ConversationAnalysis.confidence)).where(
        ConversationAnalysis.conversation_id.in_(conv_ids_q),
        ConversationAnalysis.confidence.isnot(None),
    )
    avg_confidence = (await db.execute(avg_conf_q)).scalar()
    avg_confidence = round(float(avg_confidence), 1) if avg_confidence else None

    conversion_rate = (
        round(sales_count / total_conv * 100, 1) if total_conv > 0 else None
    )

    # --- 6. Store comparison (only for brand scope) ---
    store_comparison: list[StoreComparisonItem] = []
    if brand_id:
        stores_q = select(Store).where(
            Store.brand_id == uuid.UUID(brand_id)
        ).order_by(Store.name)
        stores_result = await db.execute(stores_q)
        stores = list(stores_result.scalars().all())

        for store in stores:
            sp_ids_q = select(Salesperson.id).where(
                Salesperson.store_id == store.id
            )
            store_rec_ids_q = select(Recording.id).where(
                Recording.salesperson_id.in_(sp_ids_q)
            )
            store_conv_ids_q = select(Conversation.id).where(
                Conversation.recording_id.in_(store_rec_ids_q)
            )

            # Conversation count
            store_conv_count = (
                await db.execute(
                    select(func.count()).select_from(Conversation).where(
                        Conversation.recording_id.in_(store_rec_ids_q)
                    )
                )
            ).scalar() or 0

            # Avg performance score from scores JSONB
            store_scores_q = select(ConversationAnalysis.scores).where(
                ConversationAnalysis.conversation_id.in_(store_conv_ids_q),
                ConversationAnalysis.scores.isnot(None),
            )
            store_scores_result = await db.execute(store_scores_q)
            store_scores_list = [row[0] for row in store_scores_result.all() if row[0]]

            avg_score_val = None
            if store_scores_list:
                overall_scores = []
                for s in store_scores_list:
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
                    avg_score_val = sum(overall_scores) / len(overall_scores)

            # Sales count
            store_sales = (
                await db.execute(
                    select(func.count()).select_from(ConversationAnalysis).where(
                        ConversationAnalysis.conversation_id.in_(store_conv_ids_q),
                        ConversationAnalysis.outcome == "SALE_MADE",
                    )
                )
            ).scalar() or 0

            store_conversion = (
                round(store_sales / store_conv_count * 100, 1)
                if store_conv_count > 0
                else None
            )

            store_comparison.append(StoreComparisonItem(
                store_id=str(store.id),
                store_name=store.name,
                avg_score=round(avg_score_val, 1) if avg_score_val else None,
                conversion_rate=store_conversion,
                total_conversations=store_conv_count,
            ))

    return AnalyticsOverviewResponse(
        outcome_distribution=outcome_distribution,
        top_objections=top_objections,
        funnel_stages=funnel_stages,
        score_trend=score_trend,
        volume_trend=volume_trend,
        store_comparison=store_comparison,
        total_conversations=total_conv,
        avg_confidence=avg_confidence,
        conversion_rate=conversion_rate,
    )


async def get_salespeople_comparison(
    db: AsyncSession,
    brand_id: str | None = None,
    store_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> AnalyticsSalespeopleResponse:
    """Get per-salesperson performance comparison."""
    sp_query = select(Salesperson)
    if store_id:
        sp_query = sp_query.where(
            Salesperson.store_id == uuid.UUID(store_id)
        )
    elif brand_id:
        store_ids_q = select(Store.id).where(
            Store.brand_id == uuid.UUID(brand_id)
        )
        sp_query = sp_query.where(
            Salesperson.store_id.in_(store_ids_q)
        )
    sp_query = sp_query.order_by(Salesperson.name)
    sp_result = await db.execute(sp_query)
    salespeople = list(sp_result.scalars().all())

    items: list[SalespersonComparisonItem] = []

    for sp in salespeople:
        rec_ids_q = select(Recording.id).where(
            Recording.salesperson_id == sp.id
        )
        
        # Apply date filter to recordings if provided
        if date_from:
            rec_ids_q = rec_ids_q.where(Recording.created_at >= date_from)
        if date_to:
            # Include full end date
            rec_ids_q = rec_ids_q.where(Recording.created_at <= date_to.replace(hour=23, minute=59, second=59))
        
        conv_ids_q = select(Conversation.id).where(
            Conversation.recording_id.in_(rec_ids_q)
        )

        total_conv = (
            await db.execute(
                select(func.count()).select_from(Conversation).where(
                    Conversation.recording_id.in_(rec_ids_q)
                )
            )
        ).scalar() or 0

        # Scores
        scores_q = select(ConversationAnalysis.scores).where(
            ConversationAnalysis.conversation_id.in_(conv_ids_q),
            ConversationAnalysis.scores.isnot(None),
        )
        scores_result = await db.execute(scores_q)
        scores_list = [row[0] for row in scores_result.all() if row[0]]

        if scores_list:
            avg_greeting = sum(
                s.get("greeting_score", 0) for s in scores_list
            ) / len(scores_list)
            avg_discovery = sum(
                s.get("discovery_score", 0) for s in scores_list
            ) / len(scores_list)
            avg_pk = sum(
                s.get("product_knowledge_score", 0) for s in scores_list
            ) / len(scores_list)
            avg_oh = sum(
                s.get("objection_handling_score", 0) for s in scores_list
            ) / len(scores_list)
            avg_closing = sum(
                s.get("closing_score", 0) for s in scores_list
            ) / len(scores_list)
            avg_overall = (
                avg_greeting + avg_discovery + avg_pk + avg_oh + avg_closing
            ) / 5
        else:
            avg_greeting = avg_discovery = avg_pk = avg_oh = (
                avg_closing
            ) = avg_overall = None

        # Conversion rate
        sales_count = (
            await db.execute(
                select(func.count()).select_from(ConversationAnalysis).where(
                    ConversationAnalysis.conversation_id.in_(conv_ids_q),
                    ConversationAnalysis.outcome == "SALE_MADE",
                )
            )
        ).scalar() or 0
        conv_rate = (
            round(sales_count / total_conv * 100, 1)
            if total_conv > 0
            else None
        )

        items.append(SalespersonComparisonItem(
            salesperson_id=str(sp.id),
            name=sp.name,
            total_conversations=total_conv,
            avg_overall_score=round(avg_overall, 1) if avg_overall is not None else None,
            conversion_rate=conv_rate,
            avg_greeting_score=round(avg_greeting, 1) if avg_greeting is not None else None,
            avg_discovery_score=round(avg_discovery, 1) if avg_discovery is not None else None,
            avg_product_knowledge_score=round(avg_pk, 1) if avg_pk is not None else None,
            avg_objection_handling_score=round(avg_oh, 1) if avg_oh is not None else None,
            avg_closing_score=round(avg_closing, 1) if avg_closing is not None else None,
        ))

    # Calculate top objections across all salespeople in scope
    # Build recording IDs query for all salespeople we already fetched
    sp_ids = [sp.id for sp in salespeople]
    
    if sp_ids:
        rec_ids_for_objections = select(Recording.id).where(
            Recording.salesperson_id.in_(sp_ids)
        )
        
        # Apply date filter if provided
        if date_from:
            rec_ids_for_objections = rec_ids_for_objections.where(Recording.created_at >= date_from)
        if date_to:
            rec_ids_for_objections = rec_ids_for_objections.where(Recording.created_at <= date_to.replace(hour=23, minute=59, second=59))
        
        conv_ids_for_objections = select(Conversation.id).where(
            Conversation.recording_id.in_(rec_ids_for_objections)
        )
        
        objections_q = select(ConversationAnalysis.objections).where(
            ConversationAnalysis.conversation_id.in_(conv_ids_for_objections),
            ConversationAnalysis.objections.isnot(None),
            ConversationAnalysis.objections != func.jsonb_build_array(),
        )
        objections_result = await db.execute(objections_q)
        objection_counter: Counter = Counter()
        for (objections_list,) in objections_result.all():
            if isinstance(objections_list, list):
                for obj in objections_list:
                    if isinstance(obj, dict):
                        issue = obj.get("issue", "")
                        if issue:
                            objection_counter[issue] += 1
                    elif isinstance(obj, str) and obj:
                        objection_counter[obj] += 1
        
        top_objections = [
            ObjectionCount(objection=obj, count=cnt)
            for obj, cnt in objection_counter.most_common(10)
        ]
    else:
        top_objections = []

    return AnalyticsSalespeopleResponse(salespeople=items, top_objections=top_objections)
