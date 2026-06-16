// Shared TypeScript types matching backend Pydantic schemas

import type { Role, RecordingStatus, Outcome } from "./constants";

// --- Auth ---
export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  brand_id: string | null;
  store_id: string | null;
}

export interface LoginResponse extends TokenResponse {
  user: UserResponse;
}

// --- Brand ---
export interface Brand {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateBrandRequest {
  name: string;
  description?: string;
}

export interface UpdateBrandRequest {
  name?: string;
  description?: string;
}

// --- Store ---
export interface Store {
  id: string;
  brand_id: string;
  name: string;
  location: string | null;
  working_hours: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface CreateStoreRequest {
  name: string;
  brand_id: string;
  location?: string;
  working_hours?: Record<string, unknown>;
}

// --- Salesperson ---
export interface Salesperson {
  id: string;
  store_id: string;
  name: string;
  email: string | null;
  role: string | null;
  shift: string | null;
  device_number: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateSalespersonRequest {
  store_id: string;
  name: string;
  email?: string;
  role?: string;
  shift?: string;
  device_number?: string;
}

export interface SalespersonPerformance {
  salesperson_id: string;
  name: string;
  total_conversations: number;
  avg_greeting_score: number | null;
  avg_discovery_score: number | null;
  avg_product_knowledge_score: number | null;
  avg_objection_handling_score: number | null;
  avg_closing_score: number | null;
  avg_overall_score: number | null;
  conversion_rate: number | null;
}

// --- Recording ---
export interface Recording {
  id: string;
  salesperson_id: string;
  file_url: string;
  file_size: number | null;
  duration_seconds: number | null;
  format: string;
  status: RecordingStatus;
  error_message: string | null;
  uploaded_at: string;
  recorded_at: string | null;
  processed_at: string | null;
  pipeline_state?: {
    current_stage?: string;
    completed_stages?: string[];
    failed_stage?: string | null;
    error_message?: string | null;
    stage_timestamps?: Record<string, string>;
    retry_count?: Record<string, number>;
  } | null;
}

export interface RecordingStatusResponse {
  id: string;
  status: RecordingStatus;
  error_message: string | null;
}

export interface RecordingSummaryResponse {
  id: string;
  status: string;
  duration_seconds: number | null;
  total_conversations: number;
  top_intent: string | null;
  top_objection: string | null;
  missed_opportunities: number;
  outcomes: Record<string, number>;
  avg_confidence: number | null;
}

// --- Transcript ---
export interface TranscriptSegment {
  id: string;
  recording_id: string;
  speaker_label: string;
  role_label?: string | null;
  role_confidence?: number | null;
  start_time: number;
  end_time: number;
  text: string;
}

// --- Conversation ---
export interface Conversation {
  id: string;
  recording_id: string;
  start_time: number;
  end_time: number;
  segment_count: number;
  summary: string | null;
  created_at: string;
}

export interface ConversationListItem {
  id: string;
  recording_id: string;
  salesperson_id: string | null;
  start_time: number;
  end_time: number;
  duration_seconds: number | null;
  segment_count: number;
  summary: string | null;
  recorded_at: string | null;
  created_at: string;
  outcome: string | null;
  confidence: number | null;
  intent: string | null;
  scores: Record<string, number> | null;
}

export interface StructuredObjection {
  category: string;
  issue: string;
  response: string;
}

export interface ConversationAnalysis {
  id: string;
  conversation_id: string;
  intent: string | null;
  customer_expectation: string | null;
  products: string[];
  budget: string | null;
  objections: Array<string | StructuredObjection>;
  competitors: string[];
  closing_attempt: boolean;
  outcome: Outcome | null;
  loss_reason: string | null;
  confidence: number | null;
  scores: PerformanceScores | null;
  summary: string | null;
  coaching_notes: string | null;
  created_at: string;
}

export interface PerformanceScores {
  greeting_score: number;
  discovery_score: number;
  product_knowledge_score: number;
  objection_handling_score: number;
  closing_score: number;
}

// --- Metrics ---
export interface DailyMetrics {
  id: string;
  entity_id: string;
  entity_type: string;
  date: string;
  conversation_count: number;
  avg_score: number | null;
  conversion_rate: number | null;
}

export interface WeeklyMetrics {
  id: string;
  entity_id: string;
  entity_type: string;
  week_start: string;
  conversation_count: number;
  avg_score: number | null;
  conversion_rate: number | null;
  top_objection: string | null;
}

// --- Search ---
export interface SearchParams {
  q: string;
  date_from?: string;
  date_to?: string;
  store_id?: string;
  salesperson_id?: string;
  outcome?: Outcome;
}

export interface SearchResult {
  conversation: Conversation;
  analysis: ConversationAnalysis | null;
  relevant_segments: TranscriptSegment[];
  similarity_score: number;
}

// --- Paginated Response ---
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// --- Analytics ---
export interface OutcomeCount {
  outcome: string;
  count: number;
}

export interface ObjectionCount {
  objection: string;
  count: number;
}

export interface FunnelStage {
  stage: string;
  count: number;
}

export interface TrendPoint {
  date: string;
  avg_score: number | null;
  conversion_rate: number | null;
  conversation_count: number;
}

export interface StoreComparisonItem {
  store_id: string;
  store_name: string;
  avg_score: number | null;
  conversion_rate: number | null;
  total_conversations: number;
}

export interface AnalyticsOverviewResponse {
  outcome_distribution: OutcomeCount[];
  top_objections: ObjectionCount[];
  funnel_stages: FunnelStage[];
  score_trend: TrendPoint[];
  volume_trend: TrendPoint[];
  store_comparison: StoreComparisonItem[];
  total_conversations: number;
  avg_confidence: number | null;
  conversion_rate: number | null;
}

export interface SalespersonComparisonItem {
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

export interface AnalyticsSalespeopleResponse {
  salespeople: SalespersonComparisonItem[];
}
