"use client";

import { useEffect, useMemo, useRef } from "react";
import type { TranscriptSegment, Conversation } from "@samaa/shared";
import { cn } from "@/lib/utils";

const SPEAKER_COLORS: Record<string, string> = {
  SPEAKER_00: "text-blue-600",
  SPEAKER_01: "text-brand-green-deep",
  SPEAKER_02: "text-purple-600",
  SPEAKER_03: "text-amber-600",
  UNKNOWN: "text-stone",
};

function getSpeakerColor(label: string): string {
  return SPEAKER_COLORS[label] || "text-stone";
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface TranscriptViewerProps {
  segments: TranscriptSegment[];
  conversations?: Conversation[];
  activeConversationId?: string | null;
  currentTime?: number;
  onSegmentClick?: (segment: TranscriptSegment) => void;
  onConversationHighlight?: (conversationId: string) => void;
}

export function TranscriptViewer({
  segments,
  conversations,
  activeConversationId,
  currentTime,
  onSegmentClick,
}: TranscriptViewerProps) {
  // Group segments by conversation time ranges
  const segmentsWithConversation = useMemo(() => {
    if (!conversations?.length) return segments.map((s) => ({ ...s, conversationId: null }));
    return segments.map((seg) => {
      const conv = conversations.find(
        (c) => seg.start_time >= c.start_time && seg.end_time <= c.end_time,
      );
      return { ...seg, conversationId: conv?.id ?? null };
    });
  }, [segments, conversations]);

  const activeSegmentRef = useRef<HTMLDivElement>(null);

  // Auto-scroll active segment into view
  useEffect(() => {
    if (activeSegmentRef.current) {
      activeSegmentRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [currentTime]);

  if (segments.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-steel">
        No transcript available
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {segmentsWithConversation.map((seg) => {
        const isActiveConversation = activeConversationId && seg.conversationId === activeConversationId;
        const isActiveTime =
          currentTime !== undefined &&
          currentTime >= seg.start_time &&
          currentTime < seg.end_time;
        const isActive = isActiveConversation || isActiveTime;
        return (
          <div
            key={seg.id}
            ref={isActiveTime ? activeSegmentRef : undefined}
            className={cn(
              "flex gap-3 rounded-md px-3 py-2 text-sm transition-colors hover:bg-accent/50 cursor-pointer",
              isActiveConversation && "bg-accent",
              isActiveTime && !isActiveConversation && "bg-brand-green-soft/60",
            )}
            onClick={() => onSegmentClick?.(seg)}
          >
            <span className="shrink-0 font-mono text-xs text-steel pt-0.5">
              {formatTime(seg.start_time)}
            </span>
            <span
              className={cn(
                "shrink-0 w-20 text-xs font-semibold pt-0.5",
                getSpeakerColor(seg.speaker_label),
              )}
            >
              {seg.speaker_label.replace("SPEAKER_", "S")}
            </span>
            <span className="flex-1">{seg.text}</span>
          </div>
        );
      })}
    </div>
  );
}
