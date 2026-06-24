"use client";

import { useMemo, useRef } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import type {
  Conversation,
  ConversationAnalysis,
  TranscriptSegment,
  Salesperson,
  Store,
} from "@samaa/shared";
import { api } from "@/lib/api-client";
import { WaveformPlayer, WaveformPlayerHandle } from "@/components/features/waveform-player";
import { TranscriptViewer } from "@/components/features/transcript-viewer";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  ArrowLeft,
  MessageSquare,
  Target,
  Brain,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Package,
  DollarSign,
  Swords,
  Download,
} from "lucide-react";
import Link from "next/link";

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

export default function ConversationDetailPage() {
  const params = useParams();
  const conversationId = params.id as string;
  const playerRef = useRef<WaveformPlayerHandle>(null);

  // Fetch conversation
  const { data: conversation, isLoading: conversationLoading } = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => api.get<Conversation>(`/conversations/${conversationId}`),
    enabled: !!conversationId,
  });

  // Fetch analysis
  const { data: analysis } = useQuery({
    queryKey: ["conversation-analysis", conversationId],
    queryFn: () =>
      api.get<ConversationAnalysis>(`/conversations/${conversationId}/analysis`),
    enabled: !!conversationId,
  });

  // Fetch transcript
  const { data: transcript } = useQuery({
    queryKey: ["conversation-transcript", conversationId],
    queryFn: async () => {
      // Get recording transcript and filter for this conversation
      const allSegments = await api.get<TranscriptSegment[]>(
        `/recordings/${conversation?.recording_id}/transcript`,
      );
      if (!conversation) return [];
      
      // Filter segments within conversation time range and convert to 0-relative
      return allSegments
        .filter(
          (seg) =>
            seg.start_time < conversation.end_time + 1.0 &&
            seg.end_time > conversation.start_time - 1.0,
        )
        .map((seg) => ({
          ...seg,
          start_time: Math.max(0, seg.start_time - conversation.start_time),
          end_time: Math.max(0, seg.end_time - conversation.start_time),
        }));
    },
    enabled: !!conversation?.recording_id,
  });

  // Fetch salesperson
  const { data: salesperson } = useQuery({
    queryKey: ["salesperson", conversation?.salesperson_id],
    queryFn: () =>
      api.get<Salesperson>(`/salespeople/${conversation?.salesperson_id}`),
    enabled: !!conversation?.salesperson_id,
  });

  // Fetch store
  const { data: store } = useQuery({
    queryKey: ["store", salesperson?.store_id],
    queryFn: () => api.get<Store>(`/stores/${salesperson?.store_id}`),
    enabled: !!salesperson?.store_id,
  });

  const outcomeConfig = analysis?.outcome
    ? OUTCOME_CONFIG[analysis.outcome]
    : null;
  const OutcomeIcon = outcomeConfig?.icon;

  const hasProducts = analysis?.products && analysis.products.length > 0;
  const hasObjections = analysis?.objections && analysis.objections.length > 0;
  const hasCompetitors = analysis?.competitors && analysis.competitors.length > 0;
  const isLost = analysis?.outcome === "LOST";

  if (conversationLoading) {
    return (
      <div className="flex flex-col h-full p-4 sm:p-6 lg:p-8">
        <div className="shrink-0 space-y-6">
          <Skeleton className="h-4 w-48" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-48" />
          </div>
          <Card>
            <CardContent className="pt-6 space-y-4">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-32 w-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (!conversation) {
    return (
      <div className="flex flex-col h-full p-4 sm:p-6 lg:p-8 items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="py-12 text-center">
            <MessageSquare className="h-12 w-12 text-steel mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-ink mb-2">
              Conversation Not Found
            </h2>
            <p className="text-sm text-steel mb-4">
              The conversation you're looking for doesn't exist or has been removed.
            </p>
            <Link href="/conversations">
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Conversations
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full p-4 sm:p-6 lg:p-8">
      {/* Header Section */}
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
              href: salesperson ? `/salesperson/${salesperson.id}` : undefined,
            },
            {
              label: "Conversations",
              href: "/conversations",
            },
            {
              label: `Conversation ${conversationId.slice(0, 8)}`,
            },
          ]}
        />

        {/* Back button + Header */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <Link href={`/recordings/${conversation.recording_id}?conv=${conversation.id}`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-1 h-4 w-4" />
              Back to Recording
            </Button>
          </Link>
          <div className="flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-[22px] sm:text-[28px] font-semibold tracking-tight text-ink leading-tight">
                Conversation Details
              </h1>
              {outcomeConfig && OutcomeIcon && (
                <Badge
                  variant="outline"
                  className={`text-sm ${outcomeConfig.className}`}
                >
                  <OutcomeIcon className="mr-1 h-4 w-4" />
                  {outcomeConfig.label}
                </Badge>
              )}
            </div>
            <p className="mt-1 text-sm text-steel">
              {formatDuration(conversation.duration_seconds)} ·{" "}
              {conversation.segment_count} segments · Recorded{" "}
              {conversation.recorded_at
                ? new Date(conversation.recorded_at).toLocaleDateString()
                : "—"}
            </p>
          </div>
          {analysis && (
            <Button variant="outline" size="sm">
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
          )}
        </div>

        {/* Audio Player */}
        <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
          <CardContent className="pt-6">
            <WaveformPlayer
              ref={playerRef}
              recordingId={conversation.recording_id}
              conversationId={conversation.id}
            />
          </CardContent>
        </Card>

        {/* Quick Stats */}
        {analysis && (
          <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
            {analysis.intent && (
              <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
                <CardHeader className="flex flex-row items-center justify-between pb-1">
                  <CardTitle className="text-sm font-medium text-steel">
                    Intent
                  </CardTitle>
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-green-soft">
                    <Target className="h-4.5 w-4.5 text-brand-green-deep" />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-base font-medium text-ink">
                    {analysis.intent}
                  </p>
                </CardContent>
              </Card>
            )}

            {analysis.budget && (
              <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
                <CardHeader className="flex flex-row items-center justify-between pb-1">
                  <CardTitle className="text-sm font-medium text-steel">
                    Budget
                  </CardTitle>
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-green-soft">
                    <DollarSign className="h-4.5 w-4.5 text-brand-green-deep" />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-base font-medium text-ink">
                    {analysis.budget}
                  </p>
                </CardContent>
              </Card>
            )}

            {analysis.confidence != null && (
              <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
                <CardHeader className="flex flex-row items-center justify-between pb-1">
                  <CardTitle className="text-sm font-medium text-steel">
                    Confidence
                  </CardTitle>
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-green-soft">
                    <CheckCircle className="h-4.5 w-4.5 text-brand-green-deep" />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold font-mono text-brand-green-deep">
                    {analysis.confidence}%
                  </p>
                </CardContent>
              </Card>
            )}

            {analysis.closing_attempt && (
              <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
                <CardHeader className="flex flex-row items-center justify-between pb-1">
                  <CardTitle className="text-sm font-medium text-steel">
                    Closing
                  </CardTitle>
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-green-soft">
                    <Target className="h-4.5 w-4.5 text-brand-green-deep" />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-base font-medium text-brand-green-deep">
                    Attempted
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>

      {/* Scrollable Content Area */}
      <div className="mt-6 space-y-6">
        {analysis && (
          <>
            {/* Analysis Details */}
            <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
              <CardHeader>
                <CardTitle className="text-base font-medium text-ink">
                  Analysis Details
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Products */}
                {hasProducts && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-1.5">
                      <Package className="h-4 w-4 text-emerald-500" />
                      <span className="text-sm font-medium text-ink">
                        Products Discussed
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2 ml-6">
                      {analysis.products.map((p, i) => (
                        <Badge key={i} variant="secondary" className="text-xs">
                          {p}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Competitors */}
                {hasCompetitors && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-1.5">
                      <Swords className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium text-ink">
                        Competitors
                      </span>
                    </div>
                    <p className="text-sm text-steel ml-6">
                      {analysis.competitors.join(", ")}
                    </p>
                  </div>
                )}

                {/* Objections */}
                {hasObjections && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-1.5">
                      <AlertTriangle className="h-4 w-4 text-amber-500" />
                      <span className="text-sm font-medium text-ink">
                        Objections ({analysis.objections.length})
                      </span>
                    </div>
                    <ul className="ml-6 space-y-2">
                      {analysis.objections.map((o, i) => (
                        <li key={i}>
                          {typeof o === "string" ? (
                            <span className="text-sm text-ink">{o}</span>
                          ) : (
                            <div className="space-y-1">
                              <p className="text-sm font-medium text-ink">
                                {o.issue}
                              </p>
                              <p className="text-xs text-steel">
                                Response: {o.response}
                              </p>
                            </div>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Loss Reason */}
                {isLost && analysis.loss_reason && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-1.5">
                      <XCircle className="h-4 w-4 text-destructive" />
                      <span className="text-sm font-medium text-destructive">
                        Loss Reason
                      </span>
                    </div>
                    <p className="text-sm text-ink ml-6 leading-relaxed">
                      {analysis.loss_reason}
                    </p>
                  </div>
                )}

                {/* Summary */}
                {analysis.summary && (
                  <>
                    <Separator />
                    <div className="space-y-2">
                      <span className="text-sm font-medium text-ink">
                        Summary
                      </span>
                      <p className="text-sm text-steel leading-relaxed">
                        {analysis.summary}
                      </p>
                    </div>
                  </>
                )}

                {/* Coaching Notes */}
                {analysis.coaching_notes && (
                  <div className="rounded-lg bg-amber-50 p-4 border border-amber-100">
                    <div className="flex items-start gap-2">
                      <Brain className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                      <div>
                        <span className="text-sm font-medium text-amber-900 block mb-1">
                          Coaching Notes
                        </span>
                        <p className="text-sm text-amber-800 leading-relaxed">
                          {analysis.coaching_notes}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Score Breakdown */}
                {analysis.scores && (
                  <>
                    <Separator />
                    <div className="space-y-3">
                      <span className="text-sm font-medium text-ink">
                        Performance Scores
                      </span>
                      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                        {Object.entries(analysis.scores).map(
                          ([key, value]) => {
                            const label = key
                              .replace("_score", "")
                              .replace(/_/g, " ")
                              .replace(/\b\w/g, (l) => l.toUpperCase());
                            return (
                              <Card key={key}>
                                <CardContent className="pt-4">
                                  <div className="space-y-2">
                                    <p className="text-xs text-steel">
                                      {label}
                                    </p>
                                    <p className="text-2xl font-bold font-mono text-ink">
                                      {value}
                                    </p>
                                    <div className="h-2 bg-surface rounded-full overflow-hidden">
                                      <div
                                        className="h-full bg-brand-green-deep transition-all"
                                        style={{ width: `${value}%` }}
                                      />
                                    </div>
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
              </CardContent>
            </Card>
          </>
        )}

        {/* Transcript Section */}
        {transcript && transcript.length > 0 && (
          <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <CardTitle className="text-base font-medium text-ink">
                Transcript
              </CardTitle>
              <span className="text-xs text-steel">
                {transcript.length} segments
              </span>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg border border-hairline bg-canvas p-4">
                <TranscriptViewer
                  segments={transcript}
                  salespersonName={salesperson?.name}
                  onSegmentClick={(seg) => {
                    // Seek audio player to segment start time
                    if (playerRef.current) {
                      playerRef.current.seekTo(seg.start_time);
                    }
                  }}
                />
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
