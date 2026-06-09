"use client";

import type { Conversation, ConversationAnalysis } from "@samaa/shared";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const OUTCOME_COLORS: Record<string, string> = {
  SALE_MADE: "bg-brand-green",
  LOST: "bg-red-400",
  FOLLOW_UP_NEEDED: "bg-amber-400",
};

interface ConversationTimelineProps {
  conversations: Conversation[];
  analyses?: Map<string, ConversationAnalysis>;
  recordingDuration?: number | null;
  activeConversationId?: string | null;
  onConversationClick?: (conversation: Conversation) => void;
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export function ConversationTimeline({
  conversations,
  analyses,
  recordingDuration,
  activeConversationId,
  onConversationClick,
}: ConversationTimelineProps) {
  if (conversations.length === 0) return null;

  const totalDuration = recordingDuration || conversations[conversations.length - 1]?.end_time || 1;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>0:00</span>
        <span className="font-medium">{conversations.length} conversations detected</span>
        <span>{formatTime(totalDuration)}</span>
      </div>
      <div className="relative h-10 w-full rounded-md bg-muted">
        {conversations.map((conv) => {
          const left = (conv.start_time / totalDuration) * 100;
          const width = ((conv.end_time - conv.start_time) / totalDuration) * 100;
          const analysis = analyses?.get(conv.id);
          const outcome = analysis?.outcome;
          const barColor = outcome ? OUTCOME_COLORS[outcome] || "bg-blue-400" : "bg-blue-400";
          const isActive = activeConversationId === conv.id;

          return (
            <Tooltip key={conv.id}>
              <TooltipTrigger
                render={<button
                  className={cn(
                    "absolute top-1 h-8 rounded-sm transition-all cursor-pointer",
                    barColor,
                    isActive ? "ring-2 ring-brand-green ring-offset-1 opacity-100" : "opacity-70",
                  )}
                  style={{ left: `${left}%`, width: `${Math.max(width, 0.5)}%` }}
                  onClick={() => onConversationClick?.(conv)}
                />}
              />
              <TooltipContent>
                <p className="text-xs">
                  {formatTime(conv.start_time)} – {formatTime(conv.end_time)}
                </p>
                {conv.summary && <p className="text-xs text-muted-foreground mt-1 max-w-[200px] truncate">{conv.summary}</p>}
                {outcome && <p className="text-xs mt-1">Outcome: {outcome.replace(/_/g, " ")}</p>}
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
}
