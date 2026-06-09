"use client";

import { Badge } from "@/components/ui/badge";
import type { RecordingStatus } from "@samaa/shared";

const statusConfig: Record<RecordingStatus, { label: string; className: string }> = {
  UPLOADED: { label: "Uploaded", className: "bg-stone/10 text-slate border-stone/20" },
  PREPROCESSING: { label: "Preprocessing", className: "bg-brand-tag/10 text-brand-tag border-brand-tag/20" },
  TRANSCRIBING: { label: "Transcribing", className: "bg-brand-tag/10 text-brand-tag border-brand-tag/20" },
  DIARIZING: { label: "Diarizing", className: "bg-brand-tag/10 text-brand-tag border-brand-tag/20" },
  SEGMENTING: { label: "Segmenting", className: "bg-brand-tag/10 text-brand-tag border-brand-tag/20" },
  ANALYZING: { label: "Analyzing", className: "bg-brand-tag/10 text-brand-tag border-brand-tag/20" },
  SCORING: { label: "Scoring", className: "bg-brand-tag/10 text-brand-tag border-brand-tag/20" },
  COMPLETED: { label: "Completed", className: "bg-brand-green-soft text-brand-green-deep border-brand-green/30" },
  FAILED: { label: "Failed", className: "bg-destructive/10 text-destructive border-destructive/20" },
};

export function StatusBadge({ status }: { status: RecordingStatus }) {
  const config = statusConfig[status] || {
    label: status,
    className: "bg-gray-100 text-gray-800 border-gray-200",
  };

  return (
    <Badge variant="outline" className={config.className}>
      {config.label}
    </Badge>
  );
}
