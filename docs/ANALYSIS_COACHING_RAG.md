# SAMAA Analysis, Coaching & RAG Documentation

Comprehensive documentation of the AI-powered analysis, coaching, and retrieval-augmented generation (RAG) capabilities in the SAMAI (Sales Audio Management & AI Analysis) platform.

---

## Table of Contents

1. [Overview](#overview)
2. [Conversation Analysis](#conversation-analysis)
3. [Salesperson Performance Scoring](#salesperson-performance-scoring)
4. [Coaching Notes Generation](#coaching-notes-generation)
5. [Semantic Search & RAG](#semantic-search--rag)
6. [Data Models](#data-models)
7. [Pipeline Integration](#pipeline-integration)
8. [Configuration](#configuration)

---

## Overview

SAMAI transforms raw retail audio recordings into structured business intelligence through an 8-stage AI pipeline. The analysis, coaching, and search capabilities are implemented in stages 7-8 of the pipeline, powered by **Llama 3.3 70B via NVIDIA NIM API** and **pgvector similarity search**.

### Key Capabilities

| Capability | Technology | Purpose |
|---|---|---|
| **Conversation Analysis** | Llama 3.3 70B | Extract structured business intelligence from sales conversations |
| **Performance Scoring** | Llama 3.3 70B | Score salesperson performance across 5 dimensions |
| **Coaching Notes** | Llama 3.3 70B | Generate actionable feedback for salesperson improvement |
| **Semantic Search** | pgvector + NVIDIA Embeddings | Search conversations by meaning, not just keywords |
| **Cross-Conversation Tracking** | Segment embeddings | Track speaker patterns across multiple recordings |

---

## Conversation Analysis

### Purpose

Analyzes customer-salesperson conversations to extract structured business intelligence including customer intent, products discussed, objections raised, competitors mentioned, and conversation outcomes.

### Implementation

**File:** `apps/api/src/workers/analysis.py`  
**AI Engine:** `apps/api/src/ai/analyzer.py`  
**Model:** Llama 3.3 70B via NVIDIA NIM API  
**Stage:** Pipeline Stage 7 (`analyze_conversations`)

### Analysis Schema

The LLM is prompted to return structured JSON matching this schema:

```json
{
  "intent": "Primary customer purchase intent or inquiry",
  "customer_expectation": "What the customer expects from the product/service",
  "products": ["product1", "product2"],
  "budget": "$200-$500 or null",
  "objections": [
    {
      "category": "Price|Features|Timing|Trust|Competitor|Other",
      "issue": "The specific customer concern",
      "response": "How the salesperson addressed it"
    }
  ],
  "competitors": ["competitor1", "competitor2"],
  "closing_attempt": true,
  "outcome": "SALE_MADE|LOST|FOLLOW_UP_NEEDED",
  "loss_reason": "Why the sale was lost (if LOST)",
  "confidence": 0-100,
  "summary": "One paragraph summary",
  "coaching_notes": "Specific coaching feedback"
}
```

### Analysis Workflow

1. **Load Conversations**: Query all conversations for a recording from the database
2. **Extract Segments**: For each conversation, load transcript segments within its time range
3. **Format Transcript**: Convert segments to readable format with speaker labels
4. **LLM Analysis**: Send to Llama 3.3 with structured system prompt
5. **Parse Response**: Extract JSON, validate schema, handle malformed responses
6. **Confidence Check**: Discard results below minimum threshold (50%)
7. **Store Results**: Save to `conversation_analysis` table
8. **Update Summary**: Update conversation summary field

### Quality Controls

- **Retry Logic**: Up to 3 retries with accumulated context for malformed responses
- **Confidence Threshold**: Minimum 50% confidence required (configurable via `MIN_CONFIDENCE_THRESHOLD`)
- **Schema Validation**: Strict validation of required fields and value constraints
- **Outcome Enforcement**: Must be one of `SALE_MADE`, `LOST`, `FOLLOW_UP_NEEDED`
- **Error Handling**: Graceful degradation on API failures with retry

### Code Example

```python
from src.ai.analyzer import analyze_conversation

segments = [
    {"start": 0.0, "end": 5.2, "text": "Welcome to our store!", "speaker": "A"},
    {"start": 5.5, "end": 12.0, "text": "Hi, I'm looking for a laptop.", "speaker": "B"},
]

analysis = analyze_conversation(segments)
# Returns structured dict with intent, products, objections, outcome, etc.
```

---

## Salesperson Performance Scoring

### Purpose

Evaluates salesperson performance across 5 standardized dimensions per conversation, enabling objective performance tracking and targeted coaching.

### Implementation

**File:** `apps/api/src/workers/scoring.py`  
**AI Engine:** `apps/api/src/ai/scorer.py`  
**Model:** Llama 3.3 70B via NVIDIA NIM API  
**Stage:** Pipeline Stage 8 (`score_salesperson`)

### Scoring Dimensions

| Dimension | Weight | Description |
|---|---|---|
| **Greeting Score** | 20% | Warmth, professionalism, speed of initial greeting |
| **Discovery Score** | 20% | Quality and depth of needs-finding questions |
| **Product Knowledge** | 20% | Accuracy and depth of product explanations |
| **Objection Handling** | 20% | Effectiveness at addressing and resolving objections |
| **Closing Score** | 20% | Number and quality of closing attempts |

### Scoring Rubric

#### Greeting Score (0-100)
- **90-100**: Warm, professional, immediate acknowledgment, uses welcoming language
- **70-89**: Friendly greeting but could be more personalized
- **50-69**: Basic greeting, lacks warmth or professionalism
- **0-49**: No greeting or rude/abrupt start

#### Discovery Score (0-100)
- **90-100**: Asks open-ended questions, uncovers needs, budget, timeline, preferences
- **70-89**: Asks some qualifying questions but misses key areas
- **50-69**: Minimal questioning, mostly reactive
- **0-49**: No discovery attempts

#### Product Knowledge Score (0-100)
- **90-100**: Detailed, accurate product info, features, benefits, comparisons
- **70-89**: Good product knowledge but misses some details
- **50-69**: Basic product info, lacks depth
- **0-49**: Incorrect information or unable to answer questions

#### Objection Handling Score (0-100)
- **90-100**: Acknowledges concerns, provides solutions, offers alternatives, empathetic
- **70-89**: Addresses objections but could be more persuasive
- **50-69**: Minimal response to objections, dismissive
- **0-49**: Ignores objections or argues with customer
- **Note**: Set to null/50 if no objections were raised

#### Closing Score (0-100)
- **90-100**: Multiple natural closing attempts, creates urgency, offers next steps
- **70-89**: At least one clear closing attempt
- **50-69**: Weak or indirect closing attempt
- **0-49**: No closing attempt at all

### Scoring Workflow

1. **Load Conversations**: Query all conversations with their transcript segments
2. **Format Transcript**: Convert segments to readable format
3. **LLM Scoring**: Send to Llama 3.3 with scoring rubric system prompt
4. **Parse Scores**: Extract 5-dimension JSON scores
5. **Store Scores**: Save to `conversation_analysis.scores` JSONB field
6. **Mark Complete**: Set recording status to `COMPLETED`
7. **Update Metrics**: Recalculate daily metrics for salesperson and store

### Metrics Aggregation

After scoring, the system automatically updates `DailyMetrics` records:

```python
{
  "entity_id": "<salesperson_id or store_id>",
  "entity_type": "SALESPERSON|STORE",
  "date": "2025-01-15",
  "conversation_count": 12,
  "avg_score": 78.5,
  "conversion_rate": 45.2
}
```

### Code Example

```python
from src.ai.scorer import score_salesperson_performance, compute_average_scores

# Score single conversation
segments = [...]
scores = score_salesperson_performance(segments)
# Returns: {"greeting_score": 85, "discovery_score": 72, ...}

# Average across multiple conversations
all_scores = [scores1, scores2, scores3]
averages = compute_average_scores(all_scores)
# Returns: {"avg_greeting_score": 82.3, ...}
```

---

## Coaching Notes Generation

### Purpose

Generates specific, actionable coaching feedback for salespeople based on actual conversation moments, referencing SOP-compliant alternatives where applicable.

### Implementation

Coaching notes are generated as part of the **Conversation Analysis** stage (not a separate stage), embedded within the analysis JSON response.

### Coaching Notes Schema

```json
{
  "coaching_notes": "String with specific feedback referencing actual conversation moments and suggesting best-practice SOP responses"
}
```

### Coaching Principles

1. **Conversation-Specific**: References actual moments from the transcript
2. **Constructive**: Balanced feedback highlighting strengths and improvement areas
3. **SOP-Aligned**: Suggests standard operating procedure-compliant alternatives
4. **Actionable**: Provides concrete next steps for improvement
5. **Contextual**: Considers conversation outcome and customer expectations

### Example Coaching Notes

```
"Good job asking about the customer's budget early in the conversation (Discovery Score strength). 
However, when the customer raised price concerns about the premium laptop model, you immediately 
discounted without highlighting the extended warranty benefits. Try acknowledging the concern first: 
'I understand budget is important. Let me show you what's included in that price...' 
This builds trust before addressing the objection. Also, you missed an opportunity to close after 
explaining the financing options—consider adding: 'Would you like to start the application process today?'"
```

### Usage in UI

Coaching notes are displayed in:
- **Recording Detail Page**: Under each conversation's analysis section
- **Brand Dashboard**: Aggregated coaching insights across salespeople
- **Salesperson View**: Personal performance feedback and improvement areas

---

## Semantic Search & RAG

### Purpose

Enables users to search across all conversations by **meaning**, not just keywords, using vector embeddings and pgvector similarity search. This is the core RAG (Retrieval-Augmented Generation) capability.

### Implementation

**Search Service:** `apps/api/src/services/search.py`  
**Search API:** `apps/api/src/api/v1/search.py`  
**Embedding Model:** `nvidia/llama-3.2-nv-embedqa-1b-v2` via NVIDIA NIM API  
**Vector Database:** PostgreSQL with pgvector extension (768-dim vectors)

### Architecture

```
User Query → Embedding Generation → pgvector Similarity Search → Results with Context
     ↓              ↓                        ↓                        ↓
  "Show me      [768-dim vector]     Cosine distance query     Conversations +
  price objections"                                          relevant segments
```

### Search Workflow

1. **Embed Query**: Convert search query to 768-dim vector using NVIDIA Embeddings API
2. **Similarity Search**: Query `transcript_segments` table using pgvector cosine distance
3. **Filter Application**: Apply optional filters (date range, store, salesperson, outcome)
4. **Deduplication**: Group results by conversation, keeping best matching segment
5. **Context Loading**: Load full conversation, analysis, and recording metadata
6. **Return Cards**: Return conversation cards with relevant snippets and similarity scores

### Search API

**Endpoint:** `GET /api/v1/search`

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `q` | string | Yes | Search query (min 1 character) |
| `date_from` | string | No | Filter by start date (ISO format) |
| `date_to` | string | No | Filter by end date (ISO format) |
| `store_id` | string | No | Filter by store UUID |
| `salesperson_id` | string | No | Filter by salesperson UUID |
| `outcome` | string | No | Filter by outcome (`SALE_MADE`, `LOST`, `FOLLOW_UP_NEEDED`) |
| `limit` | int | No | Max results (default 20, max 100) |

**Response:**

```json
{
  "results": [
    {
      "conversation": {
        "id": "uuid",
        "recording_id": "uuid",
        "start_time": 120.5,
        "end_time": 450.2,
        "segment_count": 15,
        "summary": "...",
        "created_at": "2025-01-15T10:30:00Z"
      },
      "analysis": {
        "id": "uuid",
        "intent": "Customer looking for budget laptop",
        "products": ["Laptop XYZ"],
        "objections": [...],
        "outcome": "SALE_MADE",
        "coaching_notes": "...",
        "scores": {...}
      },
      "recording": {...},
      "relevant_segments": [
        {
          "id": "uuid",
          "speaker_label": "A",
          "start_time": 125.0,
          "end_time": 132.5,
          "text": "This laptop is too expensive for my budget."
        }
      ],
      "similarity_score": 0.87
    }
  ],
  "total": 1
}
```

### Embedding Generation

**Service Function:** `generate_and_store_embeddings()`

Automatically generates embeddings for all transcript segments without embeddings:

```python
from src.services.search import generate_and_store_embeddings

# Generate embeddings for a recording
count = await generate_and_store_embeddings(db, recording_id="uuid")
# Returns: number of segments embedded (processed in batches of 32)
```

**Embedding Storage:**
- Stored in `transcript_segments.embedding` column (pgvector 768-dim)
- Also stored in `word_transcripts.embedding` for word-level search
- Generated after transcription stage in the pipeline

### Similarity Search Algorithm

```python
# Cosine distance query using pgvector
seg_query = (
    select(
        TranscriptSegment,
        TranscriptSegment.embedding.cosine_distance(query_embedding).label("distance"),
    )
    .join(Conversation, Conversation.recording_id == TranscriptSegment.recording_id)
    .where(TranscriptSegment.embedding.isnot(None))
    .order_by("distance")
    .limit(limit * 3)  # Over-fetch for deduplication
)
```

### Search Use Cases

| Use Case | Example Query |
|---|---|
| **Objection Analysis** | "Price objections about laptops" |
| **Competitor Mentions** | "Customer mentioned Samsung or Dell" |
| **Closing Techniques** | "How did salespeople close deals?" |
| **Product Inquiries** | "Questions about warranty coverage" |
| **Follow-up Needed** | "Conversations requiring callbacks" |
| **Sales Coaching** | "Missed opportunities to upsell" |

---

## Data Models

### Conversation Analysis

**Table:** `conversation_analysis`  
**File:** `apps/api/src/models/conversation.py`

```python
class ConversationAnalysis(Base):
    id: UUID (PK)
    conversation_id: UUID (FK, unique)
    intent: Text (nullable)
    customer_expectation: Text (nullable)
    products: JSONB (array)
    budget: String(100) (nullable)
    objections: JSONB (array of objects)
    competitors: JSONB (array)
    closing_attempt: Boolean
    outcome: String(50) (nullable)
    loss_reason: Text (nullable)
    confidence: Integer (nullable)
    scores: JSONB (5-dimension scores)
    summary: Text (nullable)
    coaching_notes: Text (nullable)
    created_at: DateTime
```

### Transcript Segment (with Embeddings)

**Table:** `transcript_segments`  
**File:** `apps/api/src/models/transcript.py`

```python
class TranscriptSegment(Base):
    id: UUID (PK)
    recording_id: UUID (FK)
    speaker_label: String(20)
    start_time: Float
    end_time: Float
    text: Text
    embedding: Vector(768) (pgvector)
```

### Daily Metrics

**Table:** `daily_metrics`  
**File:** `apps/api/src/models/metrics.py`

```python
class DailyMetrics(Base):
    id: UUID (PK)
    entity_id: UUID (salesperson or store)
    entity_type: String(20) ("SALESPERSON" or "STORE")
    date: Date
    conversation_count: Integer
    avg_score: Float (nullable)
    conversion_rate: Float
```

---

## Pipeline Integration

### Full Pipeline Stages

```
1. upload_recording → Download audio from storage
2. preprocess_audio → VAD, noise reduction, chunking at silence boundaries
3. transcribe_audio → NVIDIA Riva STT (gRPC) for word-level transcription
4. diarize_speakers → pyannote.audio 3.1 for speaker separation
5. build_turns → Merge words into conversation turns
6. segment_conversations → Split into conversations (60s silence threshold)
7. analyze_conversations → Llama 3.3 analysis (THIS MODULE)
8. score_salesperson → Llama 3.3 scoring (THIS MODULE)
   ↓
   [Post-Pipeline] Embedding generation for semantic search
```

### Analysis Stage (Stage 7)

```python
@celery_app.task(bind=True, max_retries=3, name="analyze_conversations")
def analyze_conversations(self, recording_id: str) -> str:
    # 1. Load conversations
    conversations = _get_conversations_sync(recording_id)
    
    # 2. For each conversation
    for conv in conversations:
        segments = _get_conversation_segments_sync(conv["id"])
        analysis = analyze_conversation_ai(segments)
        
        # 3. Check confidence threshold
        if analysis["confidence"] < MIN_CONFIDENCE_THRESHOLD:
            continue
        
        # 4. Store analysis + coaching notes
        _store_analysis_sync(conv["id"], analysis)
        _update_conversation_summary_sync(conv["id"], analysis["summary"])
    
    return recording_id
```

### Scoring Stage (Stage 8)

```python
@celery_app.task(bind=True, max_retries=3, name="score_salesperson")
def score_salesperson(self, recording_id: str) -> str:
    # 1. Load conversations with segments
    conversations = _get_conversations_with_segments_sync(recording_id)
    
    # 2. Score each conversation
    for conv in conversations:
        scores = score_salesperson_performance(conv["segments"])
        _store_scores_sync(conv["conversation_id"], scores)
    
    # 3. Mark recording complete
    _complete_recording_sync(recording_id)
    
    # 4. Update daily metrics
    _update_daily_metrics_sync(recording_id)
    
    return recording_id
```

### Embedding Generation (Post-Pipeline)

Embeddings are generated automatically after transcription completes:

```python
# Called during pipeline or via manual trigger
await generate_and_store_embeddings(db, recording_id)
```

---

## Configuration

### Environment Variables

**File:** `apps/api/src/config.py`

```bash
# NVIDIA NIM API Configuration
NVIDIA_API_KEY=your-api-key
NVIDIA_BASE_URL=https://ai.api.nvidia.com/v1

# Analysis Model
NVIDIA_ANALYSIS_MODEL=nvidia/llama-3.3-70b-instruct

# Embedding Model
NVIDIA_EMBEDDING_MODEL=nvidia/llama-3.2-nv-embedqa-1b-v2

# Confidence Threshold (0-100)
MIN_CONFIDENCE_THRESHOLD=50

# Database (pgvector required)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/samaa
```

### Pydantic Settings

```python
class Settings(BaseSettings):
    nvidia_api_key: str
    nvidia_base_url: str = "https://ai.api.nvidia.com/v1"
    nvidia_analysis_model: str = "nvidia/llama-3.3-70b-instruct"
    nvidia_embedding_model: str = "nvidia/llama-3.2-nv-embedqa-1b-v2"
    min_confidence_threshold: int = 50
```

### Celery Configuration

```python
# apps/api/src/workers/celery_app.py
celery_app = Celery(
    "samaa",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "src.workers.analysis",    # Analysis task
        "src.workers.scoring",     # Scoring task
        # ... other tasks
    ]
)
```

---

## API Endpoints

### Search Endpoint

```
GET /api/v1/search?q=price+objections&limit=20&outcome=LOST
Authorization: Bearer <token>
```

**Required Permission:** `require_salesperson_up` (any authenticated user)

### Recording Analysis Endpoints

```
GET /api/v1/recordings/{id}/summary
GET /api/v1/recordings/{id}/conversations
GET /api/v1/recordings/{id}/transcript
```

All return analysis and scoring data embedded in responses.

---

## Frontend Integration

### Components Using Analysis/Coaching Data

| Component | Location | Data Used |
|---|---|---|
| **Recording Detail Page** | `apps/web/src/app/(dashboard)/recordings/[id]/page.tsx` | Full analysis, scores, coaching notes |
| **Analysis Detail Component** | `apps/web/src/components/features/analysis-detail.tsx` | Intent, objections, outcome, coaching |
| **Transcript Viewer** | `apps/web/src/components/features/transcript-viewer.tsx` | Role labels, speaker attribution |
| **Search Page** | `apps/web/src/app/(dashboard)/search/page.tsx` | Semantic search results with snippets |
| **Brand Dashboard** | `apps/web/src/app/(dashboard)/brands/[id]/page.tsx` | Aggregated scores, conversion rates |
| **Salesperson Dashboard** | `apps/web/src/app/(dashboard)/salespeople/[id]/page.tsx` | Individual performance metrics |

### Example: Displaying Coaching Notes

```tsx
// In analysis-detail.tsx
{analysis?.coaching_notes && (
  <Card>
    <CardHeader>
      <CardTitle>Coaching Notes</CardTitle>
    </CardHeader>
    <CardContent>
      <p className="text-sm text-charcoal">{analysis.coaching_notes}</p>
    </CardContent>
  </Card>
)}
```

---

## Performance & Optimization

### Analysis Performance

| Metric | Value |
|---|---|
| **Time per Conversation** | 30-120 seconds |
| **Max Tokens** | 2048 (analysis), 512 (scoring) |
| **Temperature** | 0.1 (deterministic) |
| **Retry Attempts** | 3 max with accumulated context |

### Search Performance

| Metric | Value |
|---|---|
| **Embedding Dimension** | 768 |
| **Similarity Algorithm** | Cosine distance (pgvector) |
| **Batch Size** | 32 segments per embedding batch |
| **Over-fetch Factor** | 3x (for deduplication) |
| **Default Limit** | 20 results |

### Optimization Strategies

1. **Batch Embedding**: Process 32 segments per API call
2. **Vector Indexing**: Use pgvector HNSW index for production (not yet implemented)
3. **Caching**: Embeddings stored in DB, regenerated only for new segments
4. **Parallelization**: Analysis runs per-conversation (could be parallelized further)
5. **Confidence Filtering**: Discard low-confidence results early to save storage

---

## Error Handling

### Analysis Errors

| Error Type | Handling |
|---|---|
| **NVIDIA API Failure** | Retry up to 3 times, log error, continue to next conversation |
| **Malformed JSON** | Retry with accumulated context, up to 3 attempts |
| **Low Confidence** | Discard result, log warning, increment failed_count |
| **Empty Segments** | Skip conversation, log warning |
| **Database Error** | Celery retry with exponential backoff (120s default) |

### Search Errors

| Error Type | Handling |
|---|---|
| **Embedding Generation Failure** | Log error, skip batch, continue with next batch |
| **No Embeddings Found** | Return empty results, suggest running embedding generation |
| **Query Too Short** | API validation rejects (min 1 character) |

---

## Future Enhancements

### Planned Improvements

1. **Cross-Conversation RAG**: Use embeddings to find patterns across multiple recordings
2. **Voiceprint-Based Search**: Search by speaker identity (pyannote embeddings)
3. **HNSW Index**: Add pgvector index for faster similarity search at scale
4. **Hybrid Search**: Combine semantic + keyword search (BM25 + vector)
5. **Real-time Analysis**: Streaming analysis during recording (not post-processing)
6. **Custom Model Fine-tuning**: Train domain-specific model on retail sales data
7. **Multi-turn Coaching**: Track coaching progress over time per salesperson
8. **A/B Testing**: Compare coaching note styles and measure impact

### Not Yet Implemented

- [ ] pgvector HNSW index creation
- [ ] Hybrid search (semantic + full-text)
- [ ] Embedding invalidation/re-generation pipeline
- [ ] Voiceprint enrollment integration with search
- [ ] Coaching effectiveness tracking
- [ ] Salesperson improvement trajectory analysis

---

## Troubleshooting

### Common Issues

**Issue:** Analysis returns `None` for all conversations  
**Cause:** NVIDIA API key invalid or quota exceeded  
**Fix:** Check `NVIDIA_API_KEY` in `.env`, verify API dashboard for quota

**Issue:** Search returns empty results  
**Cause:** Embeddings not generated for transcript segments  
**Fix:** Run `generate_and_store_embeddings()` for recordings, check pipeline completion

**Issue:** Low confidence scores across analyses  
**Cause:** Poor audio quality or very short conversations  
**Fix:** Improve recording quality, adjust `MIN_CONFIDENCE_THRESHOLD`

**Issue:** Scoring fails with JSON parse error  
**Cause:** LLM response malformed, retry logic exhausted  
**Fix:** Check NVIDIA model version, adjust temperature (currently 0.1)

---

## References

### Key Files

| File | Purpose |
|---|---|
| `apps/api/src/workers/analysis.py` | Celery task for conversation analysis |
| `apps/api/src/workers/scoring.py` | Celery task for performance scoring |
| `apps/api/src/ai/analyzer.py` | LLM analysis engine with prompt engineering |
| `apps/api/src/ai/scorer.py` | LLM scoring engine with rubric |
| `apps/api/src/services/search.py` | Semantic search service with pgvector |
| `apps/api/src/api/v1/search.py` | Search REST API endpoint |
| `apps/api/src/models/conversation.py` | ConversationAnalysis data model |
| `apps/api/src/models/transcript.py` | TranscriptSegment with embedding vector |
| `apps/api/src/ai/nvidia_client.py` | NVIDIA NIM API client (chat + embeddings) |

### Related Documentation

- [AI Pipeline Report](AI_PIPELINE_REPORT.md) - Full pipeline architecture
- [Pipeline Fixes Summary](docs/PIPELINE_FIXES_SUMMARY.md) - Bug fixes and improvements
- [Product PRD](docs/SAMAA_PRD.md) - Product requirements (AI-06, AI-07)
- [Testing Final Report](docs/TESTING_FINAL_REPORT.md) - Test coverage and results

---

## Glossary

| Term | Definition |
|---|---|
| **RAG** | Retrieval-Augmented Generation - using vector search to retrieve context for AI generation |
| **pgvector** | PostgreSQL extension for vector similarity search |
| **NVIDIA NIM** | NVIDIA Inference Microservices - hosted AI model API |
| **Llama 3.3 70B** | Large language model used for analysis and scoring |
| **Embedding** | 768-dimensional vector representation of text for semantic search |
| **Cosine Distance** | Measure of similarity between two vectors (0 = identical, 1 = opposite) |
| **Conversation Analysis** | Structured business intelligence extracted from sales conversations |
| **Coaching Notes** | AI-generated feedback for salesperson improvement |
| **Performance Scoring** | 5-dimension evaluation of salesperson skills |
| **Celery** | Distributed task queue for asynchronous pipeline execution |

---

*Last updated: June 13, 2026*  
*Version: 1.0.0*
