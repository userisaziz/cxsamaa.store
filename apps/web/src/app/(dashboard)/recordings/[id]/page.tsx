"use client";

import { useState, useMemo, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  Recording,
  TranscriptSegment,
  Conversation,
  ConversationAnalysis,
  RecordingSummaryResponse,
  Salesperson,
  Store,
  StructuredObjection,
} from "@samaa/shared";
import { api } from "@/lib/api-client";
import { StatusBadge } from "@/components/status-badge";
import { KPICard } from "@/components/kpi-card";
import { TranscriptViewer } from "@/components/features/transcript-viewer";
import { WaveformPlayer, WaveformPlayerHandle } from "@/components/features/waveform-player";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Mic,
  MessageSquare,
  Target,
  AlertTriangle,
  ArrowLeft,
  CheckCircle,
  XCircle,
  Clock,
  Brain,
  Swords,
  DollarSign,
  Package,
  Inbox,
  TrendingUp,
  BarChart3,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from "recharts";

const OUTCOME_CONFIG: Record<
  string,
  { label: string; icon: React.ElementType; className: string }
> = {
  SALE_MADE: {
    label: "Sale Made",
    icon: CheckCircle,
    className: "text-brand-green-deep",
  },
  LOST: { label: "Lost", icon: XCircle, className: "text-destructive" },
  FOLLOW_UP_NEEDED: {
    label: "Follow-up Needed",
    icon: Clock,
    className: "text-amber-600",
  },
};

function formatDuration(seconds: number | null): string {
  if (!seconds) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 py-3 text-sm text-steel">
      <Inbox className="h-4 w-4" />
      <span>{message}</span>
    </div>
  );
}

export default function RecordingDetailPage() {
  const params = useParams();
  const recordingId = params.id as string;
  const queryClient = useQueryClient();

  // Refs to waveform players for each conversation
  const playerRefs = useRef<Map<string, WaveformPlayerHandle>>(new Map());

  // Fetch recording
  const { data: recording } = useQuery({
    queryKey: ["recording", recordingId],
    queryFn: () => api.get<Recording>(`/recordings/${recordingId}`),
    enabled: !!recordingId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && !["COMPLETED", "FAILED"].includes(status) ? 5000 : false;
    },
  });

  // Fetch summary
  const { data: summary } = useQuery({
    queryKey: ["recording-summary", recordingId],
    queryFn: () =>
      api.get<RecordingSummaryResponse>(`/recordings/${recordingId}/summary`),
    enabled: !!recordingId && recording?.status === "COMPLETED",
  });

  // Fetch transcript
  const { data: transcript } = useQuery({
    queryKey: ["recording-transcript", recordingId],
    queryFn: () =>
      api.get<TranscriptSegment[]>(`/recordings/${recordingId}/transcript`),
    enabled: !!recordingId,
  });

  // Fetch conversations
  const { data: conversations } = useQuery({
    queryKey: ["recording-conversations", recordingId],
    queryFn: () =>
      api.get<Conversation[]>(`/recordings/${recordingId}/conversations`),
    enabled: !!recordingId,
  });

  // Fetch analyses for all conversations
  const analysisQueries = useQuery({
    queryKey: [
      "recording-analyses",
      recordingId,
      conversations?.map((c) => c.id),
    ],
    queryFn: async () => {
      if (!conversations?.length)
        return new Map<string, ConversationAnalysis>();
      const results = await Promise.all(
        conversations.map(async (conv) => {
          try {
            const analysis = await api.get<ConversationAnalysis>(
              `/conversations/${conv.id}/analysis`,
            );
            return [conv.id, analysis] as const;
          } catch {
            return [conv.id, null] as const;
          }
        }),
      );
      return new Map(
        results.filter(
          ([, a]) => a !== null,
        ) as Iterable<[string, ConversationAnalysis]>,
      );
    },
    enabled: !!conversations?.length,
  });

  const analyses =
    analysisQueries.data ?? new Map<string, ConversationAnalysis>();

  // Pre-compute per-conversation transcript segments
  const segmentsByConversation = useMemo(() => {
    if (!transcript || !conversations) return new Map<string, TranscriptSegment[]>();
    const map = new Map<string, TranscriptSegment[]>();
    for (const conv of conversations) {
      map.set(
        conv.id,
        transcript.filter(
          (seg) =>
            seg.start_time >= conv.start_time &&
            seg.end_time <= conv.end_time,
        ),
      );
    }
    return map;
  }, [transcript, conversations]);

  const handleRoleCorrection = useCallback(
    async (speakerLabel: string, correctedRole: string) => {
      try {
        await api.patch(`/recordings/${recordingId}/speaker-role`, {
          speaker_label: speakerLabel,
          corrected_role: correctedRole,
        });
        queryClient.invalidateQueries({
          queryKey: ["recording-transcript", recordingId],
        });
      } catch (err) {
        console.error("Failed to correct speaker role:", err);
      }
    },
    [recordingId, queryClient],
  );

  // Compute outcome distribution for charts
  const outcomeDistribution = useMemo(() => {
    if (!conversations || !analyses.size) return [];
    
    const counts = { SALE_MADE: 0, LOST: 0, FOLLOW_UP_NEEDED: 0 };
    conversations.forEach(conv => {
      const analysis = analyses.get(conv.id);
      if (analysis?.outcome && counts.hasOwnProperty(analysis.outcome)) {
        counts[analysis.outcome as keyof typeof counts]++;
      }
    });

    return Object.entries(counts)
      .filter(([_, count]) => count > 0)
      .map(([outcome, count]) => ({
        name: OUTCOME_CONFIG[outcome]?.label || outcome,
        value: count,
        color: outcome === "SALE_MADE" ? "oklch(0.65 0.2 165)" : 
               outcome === "LOST" ? "oklch(0.6 0.25 25)" : 
               "oklch(0.75 0.18 85)",
      }));
  }, [conversations, analyses]);

  // Compute score breakdown across all conversations
  const scoreBreakdown = useMemo(() => {
    if (!analyses.size) return [];
    
    const scoreTotals = {
      greeting: 0,
      discovery: 0,
      product_knowledge: 0,
      objection_handling: 0,
      closing: 0,
    };
    let countWithScores = 0;

    analyses.forEach(analysis => {
      if (analysis.scores) {
        countWithScores++;
        scoreTotals.greeting += analysis.scores.greeting_score ?? 0;
        scoreTotals.discovery += analysis.scores.discovery_score ?? 0;
        scoreTotals.product_knowledge += analysis.scores.product_knowledge_score ?? 0;
        scoreTotals.objection_handling += analysis.scores.objection_handling_score ?? 0;
        scoreTotals.closing += analysis.scores.closing_score ?? 0;
      }
    });

    if (countWithScores === 0) return [];

    return [
      { name: "Greeting", score: Math.round(scoreTotals.greeting / countWithScores) },
      { name: "Discovery", score: Math.round(scoreTotals.discovery / countWithScores) },
      { name: "Product Knowledge", score: Math.round(scoreTotals.product_knowledge / countWithScores) },
      { name: "Objection Handling", score: Math.round(scoreTotals.objection_handling / countWithScores) },
      { name: "Closing", score: Math.round(scoreTotals.closing / countWithScores) },
    ];
  }, [analyses]);

  function getBarColor(score: number): string {
    if (score >= 80) return "oklch(0.65 0.2 165)"; // brand-green-deep
    if (score >= 60) return "oklch(0.75 0.18 85)"; // amber
    if (score > 0) return "oklch(0.65 0.25 30)"; // orange
    return "oklch(0.75 0 0)"; // gray
  }

  // Fetch salesperson info
  const { data: salesperson } = useQuery({
    queryKey: ["salesperson-for-recording", recording?.salesperson_id],
    queryFn: () => api.get<Salesperson>(`/salespeople/${recording?.salesperson_id}`),
    enabled: !!recording?.salesperson_id,
  });

  // Fetch store info
  const { data: store } = useQuery({
    queryKey: ["store-for-recording", salesperson?.store_id],
    queryFn: () => api.get<Store>(`/stores/${salesperson?.store_id}`),
    enabled: !!salesperson?.store_id,
  });

  return (
    <div className="flex flex-col h-full p-4 sm:p-6 lg:p-8">
      {/* Header Section - Fixed at top */}
      <div className="shrink-0 space-y-4">
        {/* Breadcrumbs */}
        <Breadcrumbs
          items={[
            {
              label: store?.name || "Store",
              href: store ? `/store/${store.id}` : undefined,
            },
            {
              label: salesperson?.name || "Salesperson",
              href: salesperson
                ? `/salesperson/${salesperson.id}`
                : undefined,
            },
            {
              label: recording
                ? new Date(recording.uploaded_at).toLocaleDateString()
                : "Interaction",
            },
          ]}
        />

        {/* Back button + Header */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <Link
            href={
              salesperson ? `/salesperson/${salesperson.id}` : "/recordings"
            }
          >
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-1 h-4 w-4" />
              Back
            </Button>
          </Link>
          <div className="flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-[22px] sm:text-[28px] font-semibold tracking-tight text-ink leading-tight">
                Interactions
              </h1>
              {recording && <StatusBadge status={recording.status} />}
            </div>
            <p className="mt-1 text-sm text-steel">
              {recording && (
                <>
                  {formatDuration(recording.duration_seconds)} · {recording.format}
                  {recording.processed_at &&
                    ` · Processed ${new Date(recording.processed_at).toLocaleDateString()}`}
                </>
              )}
            </p>
          </div>
        </div>

        {/* Summary Cards */}
        {summary && (
          <>
            <div className="grid gap-3 grid-cols-1 sm:grid-cols-2">
              <KPICard
                title="Conversations"
                value={summary.total_conversations}
                icon={MessageSquare}
              />
              <KPICard
                title="Missed Opportunities"
                value={summary.missed_opportunities}
                icon={Mic}
              />
            </div>

            <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
              <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
                <CardHeader className="flex flex-row items-center justify-between pb-1">
                  <CardTitle className="text-sm font-medium text-steel">
                    Top Intent
                  </CardTitle>
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-green-soft">
                    <Target className="h-4.5 w-4.5 text-brand-green-deep" />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-base font-medium text-ink">
                    {summary.top_intent || "—"}
                  </p>
                </CardContent>
              </Card>

              <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
                <CardHeader className="flex flex-row items-center justify-between pb-1">
                  <CardTitle className="text-sm font-medium text-steel">
                    Success Rate
                  </CardTitle>
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-green-soft">
                    <CheckCircle className="h-4.5 w-4.5 text-brand-green-deep" />
                  </div>
                </CardHeader>
                <CardContent>
                  {(() => {
                    const saleCount = conversations?.filter(c => {
                      const a = analyses.get(c.id);
                      return a?.outcome === "SALE_MADE";
                    }).length ?? 0;
                    const totalWithOutcome = conversations?.filter(c => {
                      const a = analyses.get(c.id);
                      return a?.outcome;
                    }).length ?? 0;
                    const rate = totalWithOutcome > 0 ? Math.round((saleCount / totalWithOutcome) * 100) : 0;
                    
                    return (
                      <div className="space-y-1">
                        <p className="text-2xl font-bold font-mono text-brand-green-deep">
                          {totalWithOutcome > 0 ? `${rate}%` : "—"}
                        </p>
                        <p className="text-xs text-steel">
                          {saleCount} sales from {totalWithOutcome} conversations
                        </p>
                      </div>
                    );
                  })()}
                </CardContent>
              </Card>

              <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
                <CardHeader className="flex flex-row items-center justify-between pb-1">
                  <CardTitle className="text-sm font-medium text-steel">
                    Top Objection
                  </CardTitle>
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-green-soft">
                    <AlertTriangle className="h-4.5 w-4.5 text-brand-green-deep" />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-base font-medium text-ink">
                    {summary.top_objection || "—"}
                  </p>
                </CardContent>
              </Card>
            </div>
          </>
        )}

        
      </div>

      {/* Scrollable Content Area */}
      {conversations && conversations.length > 0 && (
        <div className="mt-6 space-y-4">
          <h2 className="text-lg font-semibold text-ink shrink-0">
            {conversations.length} Conversation{conversations.length !== 1 && "s"}
          </h2>

          {conversations.map((conv, idx) => {
            const analysis = analyses.get(conv.id);
            const isExpanded = true;
            const convSegments = segmentsByConversation.get(conv.id) ?? [];
            const outcomeConfig = analysis?.outcome
              ? OUTCOME_CONFIG[analysis.outcome]
              : null;
            const OutcomeIcon = outcomeConfig?.icon;
            const hasProducts =
              analysis?.products && analysis.products.length > 0;
            const hasObjections =
              analysis?.objections && analysis.objections.length > 0;
            const hasCompetitors =
              analysis?.competitors && analysis.competitors.length > 0;
            const isLost = analysis?.outcome === "LOST";

            return (
              <Card
                key={conv.id}
                className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)] overflow-hidden"
              >
                  <CardContent className="space-y-6">
                    {/* Header Info */}
                    <div className="flex items-center gap-3 flex-wrap pb-4 border-b border-hairline">
                      <CardTitle className="text-base font-medium text-ink">
                        Conversation {idx + 1}
                      </CardTitle>
                      <span className="text-xs text-steel font-mono">
                        {formatTime(conv.start_time)} – {formatTime(conv.end_time)}
                      </span>
                      {outcomeConfig && OutcomeIcon && (
                        <Badge
                          variant="outline"
                          className={`text-xs ${outcomeConfig.className}`}
                        >
                          <OutcomeIcon className="mr-1 h-3 w-3" />
                          {outcomeConfig.label}
                        </Badge>
                      )}
                      <span className="ml-auto text-xs text-steel">
                        {conv.segment_count} segments ·{" "}
                        {formatDuration(conv.end_time - conv.start_time)}
                      </span>
                    </div>
                    {/* Analysis Section */}
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                      {/* Left Column - Audio & Analysis */}
                      <div className="space-y-4">
                        {/* Compact Audio Player */}
                        <WaveformPlayer
                          ref={(el) => {
                            if (el) playerRefs.current.set(conv.id, el);
                            else playerRefs.current.delete(conv.id);
                          }}
                          recordingId={conv.recording_id}
                          conversationId={conv.id}
                          compact
                        />

                        {/* Quick Analysis Row */}
                        {analysis && (
                          <div className="flex flex-wrap items-center gap-3">
                            {analysis.intent && (
                              <div className="flex items-center gap-1.5">
                                <Target className="h-3.5 w-3.5 text-muted-foreground" />
                                <span className="text-xs text-ink">
                                  {analysis.intent}
                                </span>
                              </div>
                            )}
                            {analysis.closing_attempt && (
                              <Badge
                                variant="outline"
                                className="text-xs border-brand-green/30 text-brand-green-deep bg-brand-green/5"
                              >
                                Closing Attempted
                              </Badge>
                            )}
                            {analysis.budget && (
                              <div className="flex items-center gap-1.5">
                                <DollarSign className="h-3.5 w-3.5 text-muted-foreground" />
                                <span className="text-xs text-ink">
                                  Budget: {analysis.budget}
                                </span>
                              </div>
                            )}
                            {analysis.confidence != null && (
                              <Badge variant="outline" className="text-xs">
                                {analysis.confidence}% conf.
                              </Badge>
                            )}
                          </div>
                        )}

                        {/* Products */}
                        {hasProducts && (
                          <div className="flex flex-wrap items-center gap-1.5">
                            <Package className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                            {analysis.products.map((p, i) => (
                              <Badge
                                key={i}
                                variant="secondary"
                                className="text-xs"
                              >
                                {p}
                              </Badge>
                            ))}
                          </div>
                        )}

                        {/* Loss Reason */}
                        {isLost && analysis?.loss_reason && (
                          <div className="rounded-lg border border-destructive/15 bg-destructive/3 p-3">
                            <div className="flex items-center gap-1.5 mb-1">
                              <XCircle className="h-3.5 w-3.5 text-destructive" />
                              <span className="text-xs font-medium text-destructive">
                                Loss Reason
                              </span>
                            </div>
                            <p className="text-sm text-ink leading-relaxed">
                              {analysis.loss_reason}
                            </p>
                          </div>
                        )}

                        {/* Objections */}
                        {hasObjections && (
                          <div className="rounded-lg bg-amber-50/50 p-3 border border-amber-200/50 space-y-1.5">
                            <div className="flex items-center gap-1.5">
                              <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                              <span className="text-xs font-medium text-amber-900">
                                Objections ({analysis.objections.length})
                              </span>
                            </div>
                            <ul className="ml-5 space-y-0.5">
                              {analysis.objections.map((o, i) => (
                                <li
                                  key={i}
                                  className="text-xs text-amber-800"
                                >
                                  {typeof o === "string"
                                    ? o
                                    : (o as StructuredObjection).issue}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Competitors */}
                        {hasCompetitors && (
                          <div className="flex items-center gap-1.5">
                            <Swords className="h-3.5 w-3.5 text-muted-foreground" />
                            <span className="text-xs text-ink">
                              Competitors: {analysis.competitors.join(", ")}
                            </span>
                          </div>
                        )}

                        {/* Summary */}
                        {analysis?.summary && (
                          <>
                            <Separator />
                            <div>
                              <h4 className="text-xs font-medium text-steel mb-1">
                                Summary
                              </h4>
                              <p className="text-sm text-ink leading-relaxed">
                                {analysis.summary}
                              </p>
                            </div>
                          </>
                        )}

                        {/* Coaching Notes */}
                        {analysis?.coaching_notes && (
                          <div className="rounded-lg bg-amber-50 p-3 border border-amber-100">
                            <div className="flex items-start gap-2">
                              <Brain className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                              <div>
                                <h4 className="text-xs font-medium text-amber-900 mb-0.5">
                                  Coaching Notes
                                </h4>
                                <p className="text-sm text-amber-800 leading-relaxed">
                                  {analysis.coaching_notes}
                                </p>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Score Breakdown */}
                        {analysis?.scores && (
                          <>
                            <Separator />
                            <div className="space-y-3">
                              <h4 className="text-xs font-medium text-steel">
                                Performance Scores
                              </h4>
                              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                                {Object.entries(analysis.scores).map(
                                  ([key, val]) => {
                                    const score =
                                      typeof val === "number" ? val : 0;
                                    const label = key
                                      .replace("_score", "")
                                      .replace("_", " ");
                                    const scoreColor =
                                      score >= 80
                                        ? "text-brand-green-deep"
                                        : score >= 60
                                          ? "text-amber-700"
                                          : score > 0
                                            ? "text-orange-600"
                                            : "text-stone";
                                    const bgColor =
                                      score >= 80
                                        ? "bg-brand-green-soft"
                                        : score >= 60
                                          ? "bg-amber-50"
                                          : score > 0
                                            ? "bg-orange-50"
                                            : "bg-muted";
                                    return (
                                      <Card
                                        key={key}
                                        className={`shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)] ${bgColor}`}
                                      >
                                        <CardContent className="p-3 text-center space-y-2">
                                          <div className={`text-2xl font-bold font-mono ${scoreColor}`}>
                                            {typeof val === "number"
                                              ? val.toFixed(0)
                                              : "—"}
                                          </div>
                                          <div className="text-xs text-steel capitalize">
                                            {label}
                                          </div>
                                          <div className="w-full h-1.5 rounded-full bg-canvas overflow-hidden">
                                            <div
                                              className={`h-full rounded-full transition-all duration-500 ${
                                                score >= 80
                                                  ? "bg-brand-green"
                                                  : score >= 60
                                                    ? "bg-amber-500"
                                                    : score > 0
                                                      ? "bg-orange-500"
                                                      : "bg-gray-300"
                                              }`}
                                              style={{
                                                width: `${score}%`,
                                              }}
                                            />
                                          </div>
                                        </CardContent>
                                      </Card>
                                    );
                                  },
                                )}
                              </div>
                            </div>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Transcript Section - Full width, no constraints */}
                    <div>
                      <h4 className="text-xs font-medium text-steel mb-3 flex items-center justify-between">
                        <span>Transcript</span>
                        <span className="text-[10px] text-muted-foreground font-normal">
                          {convSegments.length} segments
                        </span>
                      </h4>
                      <div className="rounded-lg border border-hairline bg-canvas p-4">
                        <TranscriptViewer
                          segments={convSegments}
                          salespersonName={salesperson?.name}
                          onRoleCorrection={handleRoleCorrection}
                          onSegmentClick={(seg) => {
                            // Seek audio player to segment start time
                            const player = playerRefs.current.get(conv.id);
                            if (player) {
                              player.seekTo(seg.start_time);
                            }
                          }}
                        />
                      </div>
                    </div>
                  </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Empty state when no conversations found */}
      {conversations && conversations.length === 0 && recording?.status === "COMPLETED" && (
        <div className="flex-1 flex items-center justify-center">
          <Card className="w-full">
            <CardContent className="py-12 text-center">
              <MessageSquare className="h-8 w-8 text-steel mx-auto mb-2" />
              <p className="text-sm text-steel">
                No conversations detected in this recording
              </p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
