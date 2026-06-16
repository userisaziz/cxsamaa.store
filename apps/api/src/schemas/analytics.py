"""Pydantic schemas for analytics aggregation endpoints."""
from pydantic import BaseModel


class OutcomeCount(BaseModel):
    outcome: str
    count: int


class ObjectionCount(BaseModel):
    objection: str
    count: int


class FunnelStage(BaseModel):
    stage: str
    count: int


class TrendPoint(BaseModel):
    date: str
    avg_score: float | None = None
    conversion_rate: float | None = None
    conversation_count: int = 0


class StoreComparisonItem(BaseModel):
    store_id: str
    store_name: str
    avg_score: float | None = None
    conversion_rate: float | None = None
    total_conversations: int = 0


class AnalyticsOverviewResponse(BaseModel):
    outcome_distribution: list[OutcomeCount]
    top_objections: list[ObjectionCount]
    funnel_stages: list[FunnelStage]
    score_trend: list[TrendPoint]
    volume_trend: list[TrendPoint]
    store_comparison: list[StoreComparisonItem]
    total_conversations: int = 0
    avg_confidence: float | None = None
    conversion_rate: float | None = None


class SalespersonComparisonItem(BaseModel):
    salesperson_id: str
    name: str
    total_conversations: int = 0
    avg_overall_score: float | None = None
    conversion_rate: float | None = None
    avg_greeting_score: float | None = None
    avg_discovery_score: float | None = None
    avg_product_knowledge_score: float | None = None
    avg_objection_handling_score: float | None = None
    avg_closing_score: float | None = None


class AnalyticsSalespeopleResponse(BaseModel):
    salespeople: list[SalespersonComparisonItem]
    top_objections: list[ObjectionCount] = []
