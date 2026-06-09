"use client";

import { useState, useMemo } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import type {
  Recording,
  TranscriptSegment,
  Conversation,
  ConversationAnalysis,
  RecordingSummaryResponse,
  Salesperson,
  Store,
} from "@samaa/shared";
import { api } from "@/lib/api-client";
import { StatusBadge } from "@/components/status-badge";
import { KPICard } from "@/components/kpi-card";
import { TranscriptViewer } from "@/components/features/transcript-viewer";
import { ConversationTimeline } from "@/components/features/conversation-timeline";
import { AIInsightsPanel } from "@/components/features/ai-insights-panel";
import { ConversationDrawer } from "@/components/features/conversation-drawer";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Mic, MessageSquare, Target, AlertTriangle, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

function formatDuration(seconds: number | null): string {
  if (!seconds) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export default function RecordingDetailPage() {
  const params = useParams();
  const recordingId = params.id as string;

  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [drawerConversation, setDrawerConversation] = useState<Conversation | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

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
    queryFn: () => api.get<RecordingSummaryResponse>(`/recordings/${recordingId}/summary`),
    enabled: !!recordingId && recording?.status === "COMPLETED",
  });

  // Fetch transcript
  const { data: transcript } = useQuery({
    queryKey: ["recording-transcript", recordingId],
    queryFn: () => api.get<TranscriptSegment[]>(`/recordings/${recordingId}/transcript`),
    enabled: !!recordingId,
  });

  // Fetch conversations
  const { data: conversations } = useQuery({
    queryKey: ["recording-conversations", recordingId],
    queryFn: () => api.get<Conversation[]>(`/recordings/${recordingId}/conversations`),
    enabled: !!recordingId,
  });

  // Fetch analyses for all conversations
  const analysisQueries = useQuery({
    queryKey: ["recording-analyses", recordingId, conversations?.map((c) => c.id)],
    queryFn: async () => {
      if (!conversations?.length) return new Map<string, ConversationAnalysis>();
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
      return new Map(results.filter(([, a]) => a !== null) as Iterable<[string, ConversationAnalysis]>);
    },
    enabled: !!conversations?.length,
  });

  const analyses = analysisQueries.data ?? new Map<string, ConversationAnalysis>();

  // Fetch salesperson info for breadcrumb
  const { data: salesperson } = useQuery({
    queryKey: ["salesperson-for-recording", recording?.salesperson_id],
    queryFn: () => api.get<Salesperson>(`/salespeople/${recording?.salesperson_id}`),
    enabled: !!recording?.salesperson_id,
  });

  // Fetch store info for breadcrumb
  const { data: store } = useQuery({
    queryKey: ["store-for-recording", salesperson?.store_id],
    queryFn: () => api.get<Store>(`/stores/${salesperson?.store_id}`),
    enabled: !!salesperson?.store_id,
  });

  function handleConversationClick(conv: Conversation) {
    setActiveConversationId((prev) => (prev === conv.id ? null : conv.id));
  }

  function handleConversationOpen(conv: Conversation) {
    setDrawerConversation(conv);
    setDrawerOpen(true);
  }

  return (
    <div className="space-y-8 p-8">
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          { label: store?.name || "Store", href: store ? `/store/${store.id}` : undefined },
          { label: salesperson?.name || "Salesperson", href: salesperson ? `/salesperson/${salesperson.id}` : undefined },
          { label: recording ? new Date(recording.uploaded_at).toLocaleDateString() : "Recording" },
        ]}
      />

      {/* Back button + Header */}
      <div className="flex items-center gap-4">
        <Link href={salesperson ? `/salesperson/${salesperson.id}` : "/recordings"}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back
          </Button>
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-[28px] font-semibold tracking-tight text-ink leading-tight">Recording Detail</h1>
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
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <KPICard
            title="Conversations"
            value={summary.total_conversations}
            icon={MessageSquare}
          />
          <KPICard
            title="Top Intent"
            value={summary.top_intent || "—"}
            icon={Target}
          />
          <KPICard
            title="Top Objection"
            value={summary.top_objection || "—"}
            icon={AlertTriangle}
          />
          <KPICard
            title="Missed Opportunities"
            value={summary.missed_opportunities}
            icon={Mic}
          />
        </div>
      )}

      {/* Conversation Timeline */}
      {conversations && conversations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Conversation Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            <ConversationTimeline
              conversations={conversations}
              analyses={analyses}
              recordingDuration={recording?.duration_seconds}
              activeConversationId={activeConversationId}
              onConversationClick={handleConversationClick}
            />
            <p className="mt-2 text-xs text-muted-foreground text-center">
              Click a segment to highlight · Double-click to open details
            </p>
          </CardContent>
        </Card>
      )}

      {/* Transcript + AI Insights */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Transcript Viewer */}
        <Card className="max-h-[600px] overflow-y-auto">
          <CardHeader>
            <CardTitle>Transcript</CardTitle>
          </CardHeader>
          <CardContent>
            <TranscriptViewer
              segments={transcript ?? []}
              conversations={conversations}
              activeConversationId={activeConversationId}
              onSegmentClick={(seg) => {
                // Find which conversation this segment belongs to
                const conv = conversations?.find(
                  (c) => seg.start_time >= c.start_time && seg.end_time <= c.end_time,
                );
                if (conv) {
                  setActiveConversationId(conv.id);
                }
              }}
            />
          </CardContent>
        </Card>

        {/* AI Insights Panel */}
        <Card className="max-h-[600px] overflow-y-auto">
          <CardHeader>
            <CardTitle>AI Insights</CardTitle>
          </CardHeader>
          <CardContent>
            <AIInsightsPanel
              conversations={conversations ?? []}
              analyses={analyses}
              activeConversationId={activeConversationId}
              onConversationClick={handleConversationOpen}
            />
          </CardContent>
        </Card>
      </div>

      {/* Conversation Detail Drawer */}
      <ConversationDrawer
        conversation={drawerConversation}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
      />
    </div>
  );
}
