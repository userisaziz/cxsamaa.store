"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Loader2, Play, RotateCcw, AlertCircle, ChevronRight } from "lucide-react";
import { api } from "@/lib/api-client";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface PipelineActionButtonsProps {
  recordingId: string;
  status: string;
  pipelineState?: {
    current_stage?: string;
    failed_stage?: string | null;
    completed_stages?: string[];
  };
  onAction?: () => void;
}

export function PipelineActionButtons({
  recordingId,
  status,
  pipelineState,
  onAction,
}: PipelineActionButtonsProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleRetryFailedStage = async () => {
    setIsLoading(true);
    try {
      await api.post(
        `/recordings/${recordingId}/retry-failed-stage`,
        {}
      );
      toast.success("Pipeline retry initiated", {
        description: `Retrying failed stage for recording ${recordingId.slice(0, 8)}...`,
      });
      onAction?.();
    } catch (error) {
      console.error("Failed to retry failed stage:", error);
      toast.error("Failed to retry stage", {
        description: "Please check the logs or contact support.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleResumeFromStage = async (stageName: string) => {
    setIsLoading(true);
    try {
      await api.post(
        `/recordings/${recordingId}/resume-pipeline`,
        { from_stage: stageName }
      );
      toast.success("Pipeline resumed", {
        description: `Resuming from ${stageName} stage...`,
      });
      onAction?.();
    } catch (error) {
      console.error(`Failed to resume from ${stageName}:`, error);
      toast.error("Failed to resume pipeline", {
        description: "Please check the recording status and try again.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartPipeline = async (forceRerun = false) => {
    setIsLoading(true);
    try {
      await api.post(
        `/recordings/${recordingId}/start-pipeline?force_rerun=${forceRerun}`,
        {}
      );
      toast.success("Pipeline started", {
        description: forceRerun 
          ? "Reprocessing recording from beginning..." 
          : "Processing recording...",
      });
      onAction?.();
    } catch (error) {
      console.error("Failed to start pipeline:", error);
      toast.error("Failed to start pipeline", {
        description: "Check the recording status or try force rerun.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const failedStage = pipelineState?.failed_stage;
  const completedStages = pipelineState?.completed_stages || [];
  const currentStage = pipelineState?.current_stage;
  const STAGE_ORDER = [
    "preprocess", "stt", "diarization", "turns", "roles", 
    "segmentation", "stitch", "analyze", "scoring"
  ];

  const isUploaded = status === "UPLOADED" || currentStage === "UPLOADED";
  const isFailed = status === "FAILED" || !!failedStage;
  const isCompleted = status === "COMPLETED";
  const isProcessing = !isUploaded && !isFailed && !isCompleted;

  // Get next stage after current
  const currentIndex = STAGE_ORDER.indexOf(currentStage || "");
  const nextStage = currentIndex >= 0 && currentIndex < STAGE_ORDER.length - 1 
    ? STAGE_ORDER[currentIndex + 1] 
    : null;

  // Dynamic button rendering based on pipeline state
  const renderStageActions = () => {
    // Uploading stage: Start processing
    if (isUploaded) {
      return (
        <Button
          size="sm"
          onClick={() => handleStartPipeline(false)}
          disabled={isLoading}
          className="gap-1.5"
        >
          {isLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5" />
          )}
          Start Processing
        </Button>
      );
    }

    // Failed stage: Show retry + resume options
    if (isFailed && failedStage) {
      return (
        <div className="flex items-center gap-2">
          {/* Smart retry from failed stage */}
          <Button
            size="sm"
            onClick={handleRetryFailedStage}
            disabled={isLoading}
            className="gap-1.5 bg-amber-500 hover:bg-amber-600 text-white"
          >
            {isLoading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <AlertCircle className="h-3.5 w-3.5" />
            )}
            Retry from {failedStage}
          </Button>

          {/* Manual stage selection */}
          <StageSelector />
        </div>
      );
    }

    // Completed: Show force rerun
    if (isCompleted) {
      return (
        <div className="flex items-center gap-2">
          <StageSelector />
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleStartPipeline(true)}
            disabled={isLoading}
            className="gap-1.5"
          >
            {isLoading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RotateCcw className="h-3.5 w-3.5" />
            )}
            Force Rerun All
          </Button>
        </div>
      );
    }

    // Processing: Show skip to next stage option
    if (isProcessing && currentStage && nextStage) {
      return (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleResumeFromStage(nextStage)}
            disabled={isLoading}
            className="gap-1.5"
          >
            {isLoading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
            Skip to {nextStage}
          </Button>
          <StageSelector />
        </div>
      );
    }

    // Processing without next stage: Only show stage selector
    if (isProcessing && currentStage) {
      return <StageSelector />;
    }

    return null;
  };

  // Reusable stage selector dropdown
  const StageSelector = () => (
    <DropdownMenu>
      <DropdownMenuTrigger>
        <Button
          size="sm"
          variant="outline"
          disabled={isLoading}
          className="gap-1.5"
        >
          {isLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5" />
          )}
          Resume from...
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {STAGE_ORDER.map((stage) => {
          const isStageCompleted = completedStages.includes(stage);
          const isStageFailed = failedStage === stage;
          const isCurrentStage = currentStage === stage;
          return (
            <DropdownMenuItem
              key={stage}
              onClick={() => handleResumeFromStage(stage)}
              disabled={isLoading}
              className="flex items-center gap-2"
            >
              <div
                className={`h-2 w-2 rounded-full ${
                  isStageFailed
                    ? "bg-destructive"
                    : isStageCompleted
                    ? "bg-brand-green"
                    : isCurrentStage
                    ? "bg-amber-500 animate-pulse"
                    : "bg-muted"
                }`}
              />
              <span className="capitalize">{stage}</span>
              {isStageFailed && (
                <span className="ml-auto text-xs text-destructive">Failed</span>
              )}
              {isStageCompleted && (
                <span className="ml-auto text-xs text-brand-green">✓</span>
              )}
              {isCurrentStage && (
                <span className="ml-auto text-xs text-amber-500">Current</span>
              )}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );

  // Don't show buttons for unknown states
  if (!isUploaded && !isFailed && !isCompleted && !currentStage) {
    return null;
  }

  return (
    <div className="flex items-center gap-2">
      {renderStageActions()}
    </div>
  );
}
