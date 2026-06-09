"use client";

import { useQuery } from "@tanstack/react-query";
import type { Conversation, ConversationAnalysis, TranscriptSegment } from "@samaa/shared";
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
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function ConversationDrawer({ conversation, open, onOpenChange }: ConversationDrawerProps) {
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
      <SheetContent className="w-[480px] overflow-y-auto sm:max-w-[480px]">
        {conversation && (
          <>
            <SheetHeader>
              <SheetTitle>
                Conversation · {formatTime(conversation.start_time)} – {formatTime(conversation.end_time)}
              </SheetTitle>
              <SheetDescription>
                {conversation.segment_count} transcript segments
              </SheetDescription>
            </SheetHeader>

            <div className="mt-6 space-y-4">
              {/* AI Summary */}
              {analysis?.summary && (
                <div className="rounded-md bg-muted p-3">
                  <p className="text-sm leading-relaxed">{analysis.summary}</p>
                </div>
              )}

              {/* Outcome & Intent */}
              <div className="flex flex-wrap items-center gap-3">
                {analysis?.intent && (
                  <div className="flex items-center gap-1.5">
                    <Target className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{analysis.intent}</span>
                  </div>
                )}
                {outcomeConfig && OutcomeIcon && (
                  <div className={`flex items-center gap-1.5 ${outcomeConfig.className}`}>
                    <OutcomeIcon className="h-4 w-4" />
                    <span className="text-sm font-medium">{outcomeConfig.label}</span>
                  </div>
                )}
                {analysis?.closing_attempt && (
                  <Badge variant="outline" className="text-xs border-brand-green/30 text-brand-green-deep">
                    Closing Attempted
                  </Badge>
                )}
              </div>

              {/* Products & Budget */}
              {(analysis?.products?.length || analysis?.budget) && (
                <div className="space-y-2">
                  {analysis.budget && (
                    <p className="text-sm">
                      <span className="font-medium">Budget:</span> {analysis.budget}
                    </p>
                  )}
                  {analysis.products && analysis.products.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {analysis.products.map((p, i) => (
                        <Badge key={i} variant="secondary">
                          {p}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Objections */}
              {analysis?.objections && analysis.objections.length > 0 && (
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1.5">
                    <AlertTriangle className="h-4 w-4 text-amber-500" />
                    <span className="text-sm font-medium">Objections</span>
                  </div>
                  <ul className="ml-5 space-y-1">
                    {analysis.objections.map((o, i) => (
                      <li key={i} className="text-sm text-muted-foreground">
                        {o}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Coaching Notes */}
              {analysis?.coaching_notes && (
                <div className="flex items-start gap-2 rounded-lg bg-amber-50 p-3 border border-amber-100">
                  <Brain className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                  <p className="text-sm text-amber-800">{analysis.coaching_notes}</p>
                </div>
              )}

              {/* Score Breakdown */}
              {analysis?.scores && (
                <>
                  <Separator />
                  <div>
                    <h4 className="text-sm font-medium mb-2">Performance Scores</h4>
                    <div className="grid grid-cols-5 gap-2 text-center">
                      {Object.entries(analysis.scores).map(([key, val]) => (
                        <div key={key} className="space-y-1">
                          <div className="text-lg font-bold">
                            {typeof val === "number" ? val.toFixed(0) : "—"}
                          </div>
                          <div className="text-[10px] text-muted-foreground capitalize">
                            {key.replace("_score", "").replace("_", " ")}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              <Separator />

              {/* Conversation Transcript */}
              <div>
                <h4 className="text-sm font-medium mb-2">Transcript</h4>
                <TranscriptViewer segments={convSegments} />
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
