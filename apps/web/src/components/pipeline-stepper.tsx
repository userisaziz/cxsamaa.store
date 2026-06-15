"use client";

import { CheckCircle, Loader2, XCircle, Circle } from "lucide-react";

const STAGE_ORDER = [
  "preprocess",
  "stt",
  "diarization",
  "turns",
  "roles",
  "segmentation",
  "stitch",
  "analyze",
  "scoring",
];

const STAGE_LABELS: Record<string, string> = {
  preprocess: "Preprocess",
  stt: "Transcription",
  diarization: "Diarization",
  turns: "Turns",
  roles: "Roles",
  segmentation: "Segmentation",
  stitch: "Stitch",
  analyze: "Analysis",
  scoring: "Scoring",
};

interface PipelineStepperProps {
  pipelineState: {
    current_stage?: string;
    completed_stages?: string[];
    failed_stage?: string | null;
    error_message?: string | null;
    stage_timestamps?: Record<string, string>;
  };
  compact?: boolean;
}

export function PipelineStepper({ pipelineState, compact = false }: PipelineStepperProps) {
  const completedStages = pipelineState.completed_stages || [];
  const currentStage = pipelineState.current_stage;
  const failedStage = pipelineState.failed_stage;
  const errorMessage = pipelineState.error_message;

  const isCompleted = (stage: string) => completedStages.includes(stage);
  const isCurrent = (stage: string) => currentStage === stage && !failedStage;
  const isFailed = (stage: string) => failedStage === stage;
  const isPending = (stage: string) =>
    !isCompleted(stage) && !isCurrent(stage) && !isFailed(stage);

  if (compact) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-1">
          {STAGE_ORDER.map((stage) => {
            if (isCompleted(stage)) {
              return (
                <div key={stage} title={`${STAGE_LABELS[stage]} - Completed`}>
                  <CheckCircle className="h-3.5 w-3.5 text-brand-green-deep" />
                </div>
              );
            }
            if (isFailed(stage)) {
              return (
                <div key={stage} title={`${STAGE_LABELS[stage]} - Failed: ${errorMessage}`}>
                  <XCircle className="h-3.5 w-3.5 text-destructive" />
                </div>
              );
            }
            if (isCurrent(stage)) {
              return (
                <div key={stage} title={`${STAGE_LABELS[stage]} - In Progress`}>
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-brand-tag" />
                </div>
              );
            }
            return (
              <div key={stage} title={`${STAGE_LABELS[stage]} - Pending`}>
                <Circle className="h-3.5 w-3.5 text-stone" />
              </div>
            );
          })}
        </div>

        {/* Error message in compact mode */}
        {failedStage && errorMessage && (
          <div className="flex items-start gap-1.5 rounded-md border border-destructive/30 bg-destructive/5 px-2 py-1.5">
            <XCircle className="h-3 w-3 text-destructive shrink-0 mt-0.5" />
            <div className="min-w-0 flex-1">
              <p className="text-[11px] font-medium text-destructive">
                Failed at {STAGE_LABELS[failedStage]}
              </p>
              <p className="text-[10px] text-destructive/80 mt-0.5 font-mono break-words">
                {errorMessage}
              </p>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Progress bar */}
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <div className="flex h-2 w-full overflow-hidden rounded-full bg-surface">
            {STAGE_ORDER.map((stage, index) => {
              const width = `${100 / STAGE_ORDER.length}%`;
              if (isCompleted(stage)) {
                return (
                  <div
                    key={stage}
                    className="bg-brand-green-deep transition-all duration-300"
                    style={{ width }}
                  />
                );
              }
              if (isFailed(stage)) {
                return (
                  <div
                    key={stage}
                    className="bg-destructive transition-all duration-300"
                    style={{ width }}
                  />
                );
              }
              if (isCurrent(stage)) {
                return (
                  <div
                    key={stage}
                    className="bg-gradient-to-r from-brand-tag to-brand-green animate-pulse transition-all duration-300"
                    style={{ width }}
                  />
                );
              }
              return (
                <div
                  key={stage}
                  className="bg-surface transition-all duration-300"
                  style={{ width }}
                />
              );
            })}
          </div>
        </div>
        <span className="text-xs font-semibold text-ink font-mono shrink-0">
          {completedStages.length}/{STAGE_ORDER.length}
        </span>
      </div>

      {/* Stage icons */}
      <div className="grid grid-cols-9 gap-1">
        {STAGE_ORDER.map((stage) => {
          const completed = isCompleted(stage);
          const failed = isFailed(stage);
          const current = isCurrent(stage);
          const pending = isPending(stage);

          return (
            <div
              key={stage}
              className="flex flex-col items-center gap-1"
              title={`${STAGE_LABELS[stage]}${failed ? ` - Failed: ${errorMessage}` : ""}`}
            >
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full transition-all duration-200 ${
                  completed
                    ? "bg-brand-green-soft"
                    : failed
                    ? "bg-destructive/10"
                    : current
                    ? "bg-brand-tag/15"
                    : "bg-surface"
                }`}
              >
                {completed && (
                  <CheckCircle className="h-4 w-4 text-brand-green-deep" />
                )}
                {failed && <XCircle className="h-4 w-4 text-destructive" />}
                {current && (
                  <Loader2 className="h-4 w-4 animate-spin text-brand-tag" />
                )}
                {pending && <Circle className="h-4 w-4 text-stone" />}
              </div>
              <span className="text-[10px] font-medium text-steel text-center leading-tight">
                {STAGE_LABELS[stage]}
              </span>
            </div>
          );
        })}
      </div>

      {/* Error message */}
      {failedStage && errorMessage && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-3">
          <div className="flex items-start gap-2">
            <XCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-semibold text-destructive">
                Failed at {STAGE_LABELS[failedStage]}
              </p>
              <p className="text-xs text-destructive/80 mt-0.5 font-mono">
                {errorMessage}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
