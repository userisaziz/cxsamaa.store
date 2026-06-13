# SAMAA Analytics API Documentation

Complete documentation for all analytics endpoints serving Brand, Store, and Salesperson dashboards.

---

## Table of Contents

- [Overview](#overview)
- [Analytics Scoping Hierarchy](#analytics-scoping-hierarchy)
- [Endpoint 1: Analytics Overview](#endpoint-1-analytics-overview)
- [Endpoint 2: Salespeople Comparison](#endpoint-2-salespeople-comparison)
- [Endpoint 3: Store Metrics](#endpoint-3-store-metrics)
- [Endpoint 4: Salesperson Performance](#endpoint-4-salesperson-performance)
- [Data Models](#data-models)
- [Visualization Components](#visualization-components)
- [Date Range Filtering](#date-range-filtering)
- [Empty State Handling](#empty-state-handling)

---

## Overview

SAMAA provides a hierarchical analytics system that aggregates performance data across three levels:

1. **Brand Level** — Aggregates all stores and salespeople under a brand
2. **Store Level** — Aggregates all salespeople within a specific store
3. **Salesperson Level** — Individual performance metrics for a single salesperson

All analytics are computed from `ConversationAnalysis` records, which contain AI-generated scores, outcomes, objections, and funnel stage data from recorded sales interactions.

---

## Analytics Scoping Hierarchy

```
Brand (brand_id)
  └─ Store 1 (store_id)
      ├─ Salesperson A (salesperson_id)
      └─ Salesperson B (salesperson_id)
  └─ Store 2 (store_id)
      └─ Salesperson C (salesperson_id)
```

**Scope Resolution Logic:**

The analytics service uses a cascading scope resolution to determine which recordings to include:

- **Brand scope** (`brand_id`): Collects all recordings from all salespeople in all stores under the brand
- **Store scope** (`store_id`): Collects all recordings from all salespeople in the specified store
- **Salesperson scope** (`salesperson_id`): Collects recordings directly assigned to the salesperson

> **Priority**: `salesperson_id` > `store_id` > `brand_id` — only one scope parameter should be used per request.

---

## Endpoint 1: Analytics Overview

**URL**: `GET /api/v1/analytics/overview`

**Authentication**: Requires `operator` role or higher

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `brand_id` | `string` (UUID) | No | Scope analytics to a specific brand |
| `store_id` | `string` (UUID) | No | Scope analytics to a specific store |
| `salesperson_id` | `string` (UUID) | No | Scope analytics to a specific salesperson |
| `date_from` | `date` (ISO 8601) | No | Start date for trend data (default: 30 days ago) |
| `date_to` | `date` (ISO 8601) | No | End date for trend data (default: today) |

**Response Model**: `AnalyticsOverviewResponse`

```typescript
{
  outcome_distribution: OutcomeCount[];
  top_objections: ObjectionCount[];
  funnel_stages: FunnelStage[];
  score_trend: TrendPoint[];
  volume_trend: TrendPoint[];
  store_comparison: StoreComparisonItem[];  // Only populated for brand scope
  total_conversations: number;
  avg_confidence: number | null;
  conversion_rate: number | null;
}
```

### Response Fields Breakdown

#### 1. `outcome_distribution`

**Type**: `OutcomeCount[]`

**Description**: Distribution of conversation outcomes (won/lost/no-sale).

**Schema**:
```typescript
interface OutcomeCount {
  outcome: string;  // "SALE_MADE" | "NO_SALE" | "FOLLOW_UP" | etc.
  count: number;
}
```

**Source**: `ConversationAnalysis.outcome` field, grouped and counted.

**Use Case**: Outcome Donut chart, conversion rate calculation.

---

#### 2. `top_objections`

**Type**: `ObjectionCount[]`

**Description**: Most frequently raised customer objections, ranked by frequency.

**Schema**:
```typescript
interface ObjectionCount {
  objection: string;  // e.g., "Price too high", "Need to think about it"
  count: number;
}
```

**Source**: `ConversationAnalysis.objections` JSONB array. Supports both string objections and structured objects with `issue` field.

**Max Items**: 10

**Use Case**: Objection Treemap chart, coaching insights.

---

#### 3. `funnel_stages`

**Type**: `FunnelStage[]`

**Description**: Sales funnel progression showing drop-off at each stage.

**Schema**:
```typescript
interface FunnelStage {
  stage: string;  // "Conversations" | "Closing Attempts" | "Sales Made"
  count: number;
}
```

**Calculation**:
- **Conversations**: Total conversations in scope
- **Closing Attempts**: Conversations where `ConversationAnalysis.closing_attempt == true`
- **Sales Made**: Conversations where `ConversationAnalysis.outcome == "SALE_MADE"`

**Use Case**: Sales Funnel horizontal bar chart, conversion analysis.

---

#### 4. `score_trend`

**Type**: `TrendPoint[]`

**Description**: Daily average performance scores over time.

**Schema**:
```typescript
interface TrendPoint {
  date: string;  // ISO 8601 date (YYYY-MM-DD)
  avg_score: number | null;  // Average of all skill scores (0-100)
  conversion_rate: number | null;  // Daily conversion rate (%)
  conversation_count?: number;  // Included in volume_trend
}
```

**Source Priority**:
1. **Primary**: `DailyMetrics` table (pre-aggregated daily metrics)
2. **Fallback**: Computed from `ConversationAnalysis.scores` JSONB on-the-fly

**Score Calculation**: Average of 5 skill dimensions:
- `greeting_score`
- `discovery_score`
- `product_knowledge_score`
- `objection_handling_score`
- `closing_score`

**Use Case**: Score Trend area chart, performance trajectory analysis.

---

#### 5. `volume_trend`

**Type**: `TrendPoint[]`

**Description**: Daily conversation volume over time.

**Schema**:
```typescript
interface TrendPoint {
  date: string;
  conversation_count: number;
}
```

**Source Priority**:
1. **Primary**: `DailyMetrics.conversation_count`
2. **Fallback**: `COUNT(Conversation.id)` grouped by `DATE(Conversation.created_at)`

**Use Case**: Volume Trend area chart, activity pattern analysis.

---

#### 6. `store_comparison`

**Type**: `StoreComparisonItem[]`

**Description**: Per-store breakdown (only populated when `brand_id` is provided).

**Schema**:
```typescript
interface StoreComparisonItem {
  store_id: string;
  store_name: string;
  avg_score: number | null;  // Average overall score across all conversations
  conversion_rate: number | null;  // Store-level conversion rate (%)
  total_conversations: number;
}
```

**Calculation**:
- Iterates all stores under the brand
- For each store, computes avg score from `ConversationAnalysis.scores` JSONB
- Conversion rate = `(sales_count / total_conversations) * 100`

**Use Case**: Store Scatter chart (avg_score vs conversion_rate), store ranking table.

---

#### 7. `total_conversations`

**Type**: `number`

**Description**: Total number of conversations in the current scope.

**Source**: `COUNT(Conversation.id)` where `Conversation.recording_id` matches scope.

---

#### 8. `avg_confidence`

**Type**: `number | null`

**Description**: Average AI confidence score across all conversation analyses.

**Source**: `AVG(ConversationAnalysis.confidence)`

**Range**: 0-100 (percentage)

---

#### 9. `conversion_rate`

**Type**: `number | null`

**Description**: Overall conversion rate (sales made / total conversations).

**Formula**: `(sales_count / total_conversations) * 100`

**Range**: 0-100 (percentage)

---

### Example Request

```bash
GET /api/v1/analytics/overview?brand_id=abc-123&date_from=2026-05-01&date_to=2026-06-01
Authorization: Bearer <token>
```

### Example Response

```json
{
  "outcome_distribution": [
    { "outcome": "SALE_MADE", "count": 45 },
    { "outcome": "NO_SALE", "count": 30 },
    { "outcome": "FOLLOW_UP", "count": 25 }
  ],
  "top_objections": [
    { "objection": "Price too high", "count": 18 },
    { "objection": "Need to compare options", "count": 12 }
  ],
  "funnel_stages": [
    { "stage": "Conversations", "count": 100 },
    { "stage": "Closing Attempts", "count": 60 },
    { "stage": "Sales Made", "count": 45 }
  ],
  "score_trend": [
    { "date": "2026-05-01", "avg_score": 72.5, "conversion_rate": 42.0 },
    { "date": "2026-05-02", "avg_score": 68.3, "conversion_rate": 38.5 }
  ],
  "volume_trend": [
    { "date": "2026-05-01", "conversation_count": 12 },
    { "date": "2026-05-02", "conversation_count": 8 }
  ],
  "store_comparison": [
    {
      "store_id": "store-1",
      "store_name": "Downtown Flagship",
      "avg_score": 74.2,
      "conversion_rate": 48.5,
      "total_conversations": 60
    }
  ],
  "total_conversations": 100,
  "avg_confidence": 82.3,
  "conversion_rate": 45.0
}
```

---

## Endpoint 2: Salespeople Comparison

**URL**: `GET /api/v1/analytics/salespeople-comparison`

**Authentication**: Requires `operator` role or higher

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `brand_id` | `string` (UUID) | No | Scope to all salespeople under a brand |
| `store_id` | `string` (UUID) | No | Scope to all salespeople in a store |
| `date_from` | `date` (ISO 8601) | No | Start date for filtering recordings |
| `date_to` | `date` (ISO 8601) | No | End date for filtering recordings |

**Response Model**: `AnalyticsSalespeopleResponse`

```typescript
{
  salespeople: SalespersonComparisonItem[];
}
```

### SalespersonComparisonItem Schema

```typescript
interface SalespersonComparisonItem {
  salesperson_id: string;
  name: string;
  total_conversations: number;
  avg_overall_score: number | null;
  conversion_rate: number | null;
  avg_greeting_score: number | null;
  avg_discovery_score: number | null;
  avg_product_knowledge_score: number | null;
  avg_objection_handling_score: number | null;
  avg_closing_score: number | null;
}
```

### Field Descriptions

| Field | Description | Calculation |
|-------|-------------|-------------|
| `salesperson_id` | Unique identifier | UUID |
| `name` | Salesperson display name | From `Salesperson.name` |
| `total_conversations` | Number of conversations | `COUNT(Conversation)` in scope |
| `avg_overall_score` | Average of all 5 skill scores | Mean of 5 dimension averages |
| `conversion_rate` | Sales conversion rate | `(sales / conversations) * 100` |
| `avg_greeting_score` | Greeting skill average | `AVG(scores.greeting_score)` |
| `avg_discovery_score` | Discovery skill average | `AVG(scores.discovery_score)` |
| `avg_product_knowledge_score` | Product knowledge average | `AVG(scores.product_knowledge_score)` |
| `avg_objection_handling_score` | Objection handling average | `AVG(scores.objection_handling_score)` |
| `avg_closing_score` | Closing skill average | `AVG(scores.closing_score)` |

### Use Cases

- **Performance Bar Race**: Horizontal bar chart comparing salespeople by overall score
- **Skill Heatmap**: Grid showing skill proficiency across team members
- **Team Ranking Table**: Sortable table with drill-down to individual detail pages

### Example Request

```bash
GET /api/v1/analytics/salespeople-comparison?store_id=store-1&date_from=2026-05-01
Authorization: Bearer <token>
```

### Example Response

```json
{
  "salespeople": [
    {
      "salesperson_id": "sp-001",
      "name": "Alice Johnson",
      "total_conversations": 45,
      "avg_overall_score": 78.5,
      "conversion_rate": 52.3,
      "avg_greeting_score": 82.0,
      "avg_discovery_score": 75.5,
      "avg_product_knowledge_score": 80.0,
      "avg_objection_handling_score": 74.0,
      "avg_closing_score": 81.0
    },
    {
      "salesperson_id": "sp-002",
      "name": "Bob Smith",
      "total_conversations": 38,
      "avg_overall_score": 71.2,
      "conversion_rate": 44.7,
      "avg_greeting_score": 76.0,
      "avg_discovery_score": 68.5,
      "avg_product_knowledge_score": 72.0,
      "avg_objection_handling_score": 67.0,
      "avg_closing_score": 72.5
    }
  ]
}
```

---

## Endpoint 3: Store Metrics

**URL**: `GET /api/v1/stores/{store_id}/metrics`

**Authentication**: Requires `store_manager` role or higher for the store

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `store_id` | `string` (UUID) | Yes | Store identifier |

**Response Model**: `StoreMetricsResponse`

```typescript
interface StoreMetricsResponse {
  store_id: string;
  name: string;
  total_salespeople: number;
  total_recordings: number;
  total_conversations: number;
  avg_performance_score: number | null;
  conversion_rate: number | null;
  top_objection: string | null;
}
```

### Field Descriptions

| Field | Description | Source |
|-------|-------------|--------|
| `store_id` | Store UUID | `Store.id` |
| `name` | Store name | `Store.name` |
| `total_salespeople` | Number of salespeople in store | `COUNT(Salesperson)` where `store_id` matches |
| `total_recordings` | Number of audio recordings | `COUNT(Recording)` for store's salespeople |
| `total_conversations` | Number of analyzed conversations | `COUNT(Conversation)` from recordings |
| `avg_performance_score` | Average overall score | From `ConversationAnalysis.scores` JSONB |
| `conversion_rate` | Store conversion rate | `(sales / conversations) * 100` |
| `top_objection` | Most common objection | Mode of `ConversationAnalysis.objections` |

### Use Case

Store detail page KPI cards, store comparison tables, operational dashboards.

### Example Request

```bash
GET /api/v1/stores/store-123/metrics
Authorization: Bearer <token>
```

### Example Response

```json
{
  "store_id": "store-123",
  "name": "Downtown Flagship",
  "total_salespeople": 8,
  "total_recordings": 156,
  "total_conversations": 142,
  "avg_performance_score": 74.2,
  "conversion_rate": 48.5,
  "top_objection": "Price too high"
}
```

---

## Endpoint 4: Salesperson Performance

**URL**: `GET /api/v1/salespeople/{salesperson_id}/performance`

**Authentication**: Requires `operator` role or higher

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `salesperson_id` | `string` (UUID) | Yes | Salesperson identifier |

**Response Model**: `SalespersonPerformanceResponse`

```typescript
interface SalespersonPerformanceResponse {
  salesperson_id: string;
  name: string;
  total_conversations: number;
  avg_overall_score: number | null;
  conversion_rate: number | null;
  avg_greeting_score: number | null;
  avg_discovery_score: number | null;
  avg_product_knowledge_score: number | null;
  avg_objection_handling_score: number | null;
  avg_closing_score: number | null;
}
```

### Field Descriptions

Same schema as `SalespersonComparisonItem` — provides individual performance snapshot for detail pages.

### Score Calculation Logic

```python
# For each skill dimension:
avg_greeting = sum(s["greeting_score"] for s in scores if s["greeting_score"] is not None) / count

# Overall score:
valid_averages = [avg_greeting, avg_discovery, avg_pk, avg_oh, avg_closing]
valid_averages = [a for a in valid_averages if a is not None]
avg_overall = sum(valid_averages) / len(valid_averages)
```

> **Note**: Only non-None values are included in averages to handle missing data gracefully.

### Use Case

Salesperson detail page, performance reviews, coaching recommendations, radar chart visualization.

### Example Request

```bash
GET /api/v1/salespeople/sp-001/performance
Authorization: Bearer <token>
```

### Example Response

```json
{
  "salesperson_id": "sp-001",
  "name": "Alice Johnson",
  "total_conversations": 45,
  "avg_overall_score": 78.5,
  "conversion_rate": 52.3,
  "avg_greeting_score": 82.0,
  "avg_discovery_score": 75.5,
  "avg_product_knowledge_score": 80.0,
  "avg_objection_handling_score": 74.0,
  "avg_closing_score": 81.0
}
```

---

## Data Models

### Core Database Models

#### ConversationAnalysis

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `conversation_id` | UUID | FK to Conversation |
| `outcome` | VARCHAR | "SALE_MADE", "NO_SALE", "FOLLOW_UP", etc. |
| `closing_attempt` | BOOLEAN | Whether closing was attempted |
| `confidence` | FLOAT | AI confidence (0-100) |
| `scores` | JSONB | `{greeting_score, discovery_score, product_knowledge_score, objection_handling_score, closing_score}` |
| `objections` | JSONB | Array of objections (strings or `{issue, severity}` objects) |
| `created_at` | TIMESTAMP | Analysis timestamp |

#### DailyMetrics

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `entity_id` | UUID | Brand/Store/Salesperson ID |
| `entity_type` | VARCHAR | "BRAND", "STORE", "SALESPERSON" |
| `date` | DATE | Metrics date |
| `avg_score` | FLOAT | Average performance score |
| `conversion_rate` | FLOAT | Daily conversion rate |
| `conversation_count` | INT | Number of conversations |

#### Recording

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `salesperson_id` | UUID | FK to Salesperson |
| `created_at` | TIMESTAMP | Recording upload timestamp |

---

## Visualization Components

### Frontend Chart Components (Next.js)

| Component | Data Source | Page |
|-----------|-------------|------|
| `OutcomeDonut` | `outcome_distribution` | Brand / Store / Salesperson |
| `ConversionGauge` | `conversion_rate` | Brand / Store / Salesperson |
| `ScoreTrend` | `score_trend` | Brand / Store / Salesperson |
| `VolumeTrend` | `volume_trend` | Brand / Store / Salesperson |
| `PerformanceBar` | `salespeople[].avg_overall_score` | Brand / Store |
| `StoreScatter` | `store_comparison` | Brand |
| `ObjectionTreemap` | `top_objections` | Brand / Store / Salesperson |
| `SkillHeatmap` | `salespeople[]` skill scores | Brand / Store |
| `RadarChart` | Individual skill scores | Salesperson detail |

### Chart Library

**Recharts** (React-based charting library)

**Common Configuration**:
- Color palette: SAMAA brand colors (mint green accent, neutral grays)
- Responsive: All charts use `ResponsiveContainer`
- Tooltips: Enabled with custom formatters
- Empty states: Graceful handling with placeholder messages

---

## Date Range Filtering

### Default Behavior

- **`date_from`**: 30 days ago from current date
- **`date_to`**: Current date (end of day)

### Frontend Implementation

```typescript
const [dateRange, setDateRange] = useState<DateRange>(() => {
  const now = new Date();
  const to = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
  const from = new Date(now);
  from.setDate(from.getDate() - 30);
  from.setHours(0, 0, 0, 0);
  return { from, to };
});
```

### API Query Parameter Format

```
date_from=2026-05-01&date_to=2026-06-01
```

> **Note**: Dates are sent as ISO 8601 strings (YYYY-MM-DD), not full timestamps.

### Date Filter Application

**Analytics Overview**:
- Trend data filtered by date range
- Fallback score/volume aggregation respects date bounds

**Salespeople Comparison**:
- Recording creation date filtered before conversation aggregation
- `date_to` includes full end day (23:59:59)

**Individual Performance**:
- No date filtering (current implementation shows all-time data)
- Future enhancement: Add date range to `/salespeople/{id}/performance`

---

## Empty State Handling

### When No Data Exists

All analytics endpoints return structured empty states rather than errors:

```json
{
  "outcome_distribution": [],
  "top_objections": [],
  "funnel_stages": [
    { "stage": "Conversations", "count": 0 },
    { "stage": "Closing Attempts", "count": 0 },
    { "stage": "Sales Made", "count": 0 }
  ],
  "score_trend": [],
  "volume_trend": [],
  "store_comparison": [],
  "total_conversations": 0,
  "avg_confidence": null,
  "conversion_rate": null
}
```

### Frontend Empty State Messages

| Scenario | Message |
|----------|---------|
| No conversations | "No conversations yet — upload a recording to get started" |
| No analytics data | "Analytics will appear once conversations are processed" |
| Zero conversion rate | "No sales recorded in selected period" |
| No objections | "No objections detected — great selling!" |

### UI Implementation Pattern

```typescript
{analytics && analytics.total_conversations === 0 ? (
  <EmptyState
    icon={Inbox}
    title="No conversations yet"
    description="Upload a recording to see analytics"
  />
) : (
  <AnalyticsDashboard data={analytics} />
)}
```

---

## Authentication & Authorization

### Role Hierarchy

| Role | Analytics Access |
|------|------------------|
| `operator` | All brands, stores, salespeople |
| `brand_admin` | Own brand and children |
| `store_manager` | Own store and salespeople |
| `salesperson` | Own performance only (future) |

### Dependency Injection

```python
@router.get("/overview")
async def analytics_overview(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_operator_up),
):
    ...
```

**Available Dependencies**:
- `require_operator_up` — Operator or higher
- `require_brand_admin_up` — Brand admin or higher
- `require_store_manager_up` — Store manager or higher

---

## Performance Considerations

### Query Optimization

1. **Recording ID Pre-filtering**: `_get_recording_ids_for_scope()` resolves scope once, reuses across all subqueries
2. **DailyMetrics Priority**: Uses pre-aggregated daily metrics when available (avoiding expensive JSONB aggregation)
3. **JSONB Indexing**: Consider adding GIN index on `ConversationAnalysis.scores` for faster score extraction

### Recommended Indexes

```sql
CREATE INDEX idx_conversation_recording_id ON conversation(recording_id);
CREATE INDEX idx_analysis_conversation_id ON conversation_analysis(conversation_id);
CREATE INDEX idx_recording_salesperson_id ON recording(salesperson_id);
CREATE INDEX idx_daily_metrics_entity ON daily_metrics(entity_id, entity_type, date);
CREATE INDEX idx_analysis_scores ON conversation_analysis USING gin(scores);
```

### Caching Strategy

**Future Enhancement**: Implement Redis caching for analytics queries with 5-minute TTL.

---

## Error Handling

### Common Error Responses

| Status Code | Scenario | Message |
|-------------|----------|---------|
| 401 | Missing/invalid token | "Not authenticated" |
| 403 | Insufficient role | "Insufficient permissions" |
| 404 | Entity not found | "Salesperson not found" |
| 422 | Invalid UUID | "Invalid UUID format" |

### Graceful Degradation

- **Missing scores**: Returns `null` instead of 0 to distinguish "no data" from "zero performance"
- **No daily metrics**: Falls back to on-the-fly aggregation from conversation-level data
- **Empty objections**: Handles both string arrays and structured JSON objects

---

## Future Enhancements

### Planned Features

1. **Cross-Entity Comparison**: Compare multiple stores/salespeople side-by-side
2. **Cohort Analysis**: Track performance changes over rolling periods
3. **Benchmarking**: Compare against brand/store averages
4. **Export Analytics**: CSV/PDF export of dashboard data
5. **Real-time Updates**: WebSocket streaming for live conversation updates
6. **Custom Date Presets**: "Last 7 days", "This month", "Last quarter"
7. **Advanced Filtering**: Filter by product category, conversation duration, outcome type
8. **Predictive Analytics**: ML-based conversion probability scoring

### API Versioning

Current version: `v1` (under `/api/v1/analytics/`)

Future versions will maintain backward compatibility with deprecation notices.

---

## Testing

### Example Test Cases

```python
async def test_analytics_overview_brand_scope():
    response = await client.get(
        "/api/v1/analytics/overview?brand_id=abc-123",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "outcome_distribution" in data
    assert "total_conversations" in data
    assert len(data["store_comparison"]) > 0

async def test_analytics_empty_state():
    response = await client.get(
        "/api/v1/analytics/overview?brand_id=no-data-brand",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_conversations"] == 0
    assert data["conversion_rate"] is None
```

---

## Related Documentation

- [Conversation Analysis Pipeline](./PIPELINE_IMPLEMENTATION_SUMMARY.md)
- [Scoring System](./PIPELINE_UPGRADE_GUIDE.md)
- [Frontend Analytics Components](../apps/web/src/components/charts/)
- [Shared TypeScript Types](../packages/shared/src/api-types.ts)

---

**Last Updated**: 2026-06-13  
**Version**: 1.0.0  
**Maintainer**: SAMAA Engineering Team
