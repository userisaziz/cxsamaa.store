"use client";

import { useQuery } from "@tanstack/react-query";
import type { Conversation, ConversationAnalysis, TranscriptSegment, StructuredObjection } from "@samaa/shared";
import { api } from "@/lib/api-client";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { TranscriptViewer } from "./transcript-viewer";
import { WaveformPlayer } from "./waveform-player";
import { Brain, Target, AlertTriangle, CheckCircle, XCircle, Clock } from "lucide-react";

const SPEAKER_COLORS: Record<string, string> = {
  SPEAKER_00: "text-blue-600",
  SPEAKER_01: "text-emerald-600",
  SPEAKER_02: "text-purple-600",
  SPEAKER_03: "text-amber-600",
  UNKNOWN: "text-gray-500",
};

const OUTCOME_CONFIG: Record<string, { label: string; icon: React.ElementType; className: string }> = {
  SALE_MADE: { label: "Sale Made", icon: CheckCircle, className: "text-brand-green-deep" },
  LOST: { label: "Lost", icon: XCircle, className: "text-destructive" },
  FOLLOW_UP_NEEDED: { label: "Follow-up Needed", icon: Clock, className: "text-amber-600" },
};

interface ConversationDrawerProps {
  conversation: Conversation | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  salespersonName?: string;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function ConversationDrawer({ conversation, open, onOpenChange, salespersonName }: ConversationDrawerProps) {
  const convId = conversation?.id;

  const { data: analysis } = useQuery({
    queryKey: ["conversation-analysis", convId],
    queryFn: () => api.get<ConversationAnalysis>(`/conversations/${convId}/analysis`),
    enabled: !!convId,
  });

  const { data: transcriptSegments } = useQuery({
    queryKey: ["recording-transcript", conversation?.recording_id],
    queryFn: () => api.get<TranscriptSegment[]>(`/recordings/${conversation?.recording_id}/transcript`),
    enabled: !!conversation?.recording_id,
  });

  // Filter segments within this conversation's time range
  const convSegments = transcriptSegments?.filter(
    (seg) =>
      seg.start_time >= (conversation?.start_time ?? 0) &&
      seg.end_time <= (conversation?.end_time ?? Infinity),
  ) ?? [];

  const outcomeConfig = analysis?.outcome ? OUTCOME_CONFIG[analysis.outcome] : null;
  const OutcomeIcon = outcomeConfig?.icon;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[480px] overflow-y-auto sm:max-w-[480px] p-6">
        {conversation && (
          <>
            <SheetHeader className="mb-6">
              <SheetTitle className="text-lg">
                Conversation · {formatTime(conversation.start_time)} – {formatTime(conversation.end_time)}
              </SheetTitle>
              <SheetDescription className="text-sm">
                {conversation.segment_count} transcript segments · {Math.round(conversation.end_time - conversation.start_time)}s duration
              </SheetDescription>
            </SheetHeader>

            <div className="space-y-6">
              {/* Conversation Audio Player */}
              <WaveformPlayer
                recordingId={conversation.recording_id}
                conversationId={conversation.id}
                compact
              />

              {/* AI Summary */}
              {analysis?.summary && (
                <div className="rounded-lg bg-muted/50 p-4 border border-border/50">
                  <p className="text-sm leading-relaxed text-charcoal">{analysis.summary}</p>
                </div>
              )}

              {/* Outcome & Intent */}
              {(analysis?.intent || outcomeConfig || analysis?.closing_attempt) && (
                <div className="rounded-lg bg-surface p-4 border border-hairline space-y-3">
                  <div className="flex flex-wrap items-center gap-3">
                    {analysis?.intent && (
                      <div className="flex items-center gap-1.5">
                        <Target className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm text-ink">{analysis.intent}</span>
                      </div>
                    )}
                    {outcomeConfig && OutcomeIcon && (
                      <div className={`flex items-center gap-1.5 ${outcomeConfig.className}`}>
                        <OutcomeIcon className="h-4 w-4" />
                        <span className="text-sm font-medium">{outcomeConfig.label}</span>
                      </div>
                    )}
                  </div>
                  {analysis?.closing_attempt && (
                    <Badge variant="outline" className="text-xs border-brand-green/30 text-brand-green-deep bg-brand-green/5">
                      Closing Attempted
                    </Badge>
                  )}
                </div>
              )}

              {/* Products & Budget */}
              {(analysis?.products?.length || analysis?.budget) && (
                <div className="rounded-lg bg-surface p-4 border border-hairline space-y-3">
                  <h4 className="text-sm font-medium text-ink">Details</h4>
                  <div className="space-y-2">
                    {analysis.budget && (
                      <p className="text-sm text-charcoal">
                        <span className="font-medium text-ink">Budget:</span> {analysis.budget}
                      </p>
                    )}
                    {analysis.products && analysis.products.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {analysis.products.map((p, i) => (
                          <Badge key={i} variant="secondary" className="bg-surface-soft text-charcoal">
                            {p}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Objections */}
              {analysis?.objections && analysis.objections.length > 0 && (
                <div className="rounded-lg bg-amber-50/50 p-4 border border-amber-200/50 space-y-2">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    <span className="text-sm font-medium text-amber-900">Objections ({analysis.objections.length})</span>
                  </div>
                  <ul className="space-y-1.5 ml-6">
                    {analysis.objections.map((o, i) => (
                      <li key={i} className="text-sm text-amber-800 leading-relaxed">
                        {typeof o === "string" ? o : (o as StructuredObjection).issue}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Coaching Notes */}
              {analysis?.coaching_notes && (
                <div className="rounded-lg bg-amber-50/50 p-4 border border-amber-200/50">
                  <div className="flex items-start gap-3">
                    <Brain className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-medium text-amber-900 mb-1">Coaching Notes</h4>
                      <p className="text-sm text-amber-800 leading-relaxed">{analysis.coaching_notes}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Score Breakdown */}
              {analysis?.scores && (
                <div className="rounded-lg bg-surface p-5 border border-hairline space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-ink">Performance Scores</h4>
                    <Badge variant="outline" className="text-xs">
                      {Object.values(analysis.scores).filter((v) => typeof v === "number" && v > 0).length}/{Object.keys(analysis.scores).length} scored
                    </Badge>
                  </div>
                  
                  <div className="space-y-3">
                    {Object.entries(analysis.scores).map(([key, val]) => {
                      const score = typeof val === "number" ? val : 0;
                      const label = key.replace("_score", "").replace("_", " ");
                      const scoreColor = score >= 80 ? "bg-brand-green" : score >= 60 ? "bg-amber-500" : score > 0 ? "bg-orange-500" : "bg-gray-300";
                      const textColor = score >= 80 ? "text-brand-green-deep" : score >= 60 ? "text-amber-700" : score > 0 ? "text-orange-700" : "text-gray-500";
                      
                      return (
                        <div key={key} className="space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-charcoal capitalize">{label}</span>
                            <span className={`text-sm font-semibold ${textColor}`}>
                              {typeof val === "number" ? `${val.toFixed(0)}%` : "—"}
                            </span>
                          </div>
                          <div className="h-2 w-full rounded-full bg-canvas border border-hairline/50 overflow-hidden">
                            <div 
                              className={`h-full rounded-full transition-all duration-300 ${scoreColor}`}
                              style={{ width: `${score}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Conversation Transcript */}
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-ink">Transcript</h4>
                <div className="rounded-lg border border-hairline bg-canvas p-4">
                  <TranscriptViewer segments={convSegments} salespersonName={salespersonName} />
                </div>
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
