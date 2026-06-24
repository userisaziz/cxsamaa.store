"use client";

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import WaveSurfer from "wavesurfer.js";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface WaveformPlayerHandle {
  seekTo: (seconds: number) => void;
}

interface WaveformPlayerProps {
  recordingId: string;
  /** When provided, loads only the conversation audio segment. */
  conversationId?: string;
  /** Compact variant for use in cards and drawers. */
  compact?: boolean;
  onTimeUpdate?: (currentTime: number) => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export const WaveformPlayer = forwardRef<WaveformPlayerHandle, WaveformPlayerProps>(
  function WaveformPlayer({ recordingId, conversationId, compact, onTimeUpdate }, ref) {
    const containerRef = useRef<HTMLDivElement>(null);
    const wavesurferRef = useRef<WaveSurfer | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [isReady, setIsReady] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Expose seekTo via ref
    useImperativeHandle(ref, () => ({
      seekTo: (seconds: number) => {
        if (wavesurferRef.current && duration > 0) {
          wavesurferRef.current.seekTo(seconds / duration);
        }
      },
    }));

    // Build the audio URL
    const audioUrl = conversationId
      ? `${API_URL}/conversations/${conversationId}/audio`
      : `${API_URL}/recordings/${recordingId}/audio`;

    // Initialize wavesurfer
    useEffect(() => {
      if (!containerRef.current) return;

      const height = compact ? 40 : 80;

      const ws = WaveSurfer.create({
        container: containerRef.current,
        waveColor: "#d1d5db",
        progressColor: "#00d4a4",
        cursorColor: "#1a1a1a",
        cursorWidth: 1,
        barWidth: 2,
        barGap: 1.5,
        barRadius: 2,
        height,
        normalize: true,
        // Use MediaElement backend for streaming - doesn't load entire file into memory
        backend: "MediaElement",
      });

      wavesurferRef.current = ws;

      ws.on("ready", () => {
        setIsReady(true);
        setDuration(ws.getDuration());
        setError(null);
      });

      ws.on("error", (err) => {
        console.error("WaveSurfer error:", err);
        setError("Failed to load audio");
        setIsReady(false);
      });

      ws.on("play", () => setIsPlaying(true));
      ws.on("pause", () => setIsPlaying(false));
      ws.on("finish", () => setIsPlaying(false));

      ws.on("timeupdate", (time: number) => {
        setCurrentTime(time);
        onTimeUpdate?.(time);
      });

      // Load audio with authentication
      // For MediaElement backend, we fetch with auth headers and create a blob URL
      const token = localStorage.getItem("access_token");
      fetch(audioUrl, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
        .then((response) => {
          if (!response.ok) throw new Error("Failed to load audio");
          return response.blob();
        })
        .then((blob) => {
          const blobUrl = URL.createObjectURL(blob);
          ws.load(blobUrl);
        })
        .catch(() => setError("Failed to load audio"));

      return () => {
        ws.destroy();
        wavesurferRef.current = null;
      };
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [audioUrl]);

    const togglePlayPause = useCallback(() => {
      wavesurferRef.current?.playPause();
    }, []);

    if (error) {
      return (
        <div className={`flex items-center gap-3 rounded-xl border border-border bg-surface px-4 text-sm text-steel ${compact ? "py-2" : "py-3"}`}>
          <svg className="h-4 w-4 shrink-0 text-brand-error" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </div>
      );
    }

    const btnSize = compact ? "h-8 w-8" : "h-10 w-10";

    return (
      <div className={`rounded-xl border border-border bg-card ${compact ? "p-2.5" : "p-4"}`}>
        <div className={`flex items-center ${compact ? "gap-2.5" : "gap-4"}`}>
          {/* Play / Pause button */}
          <button
            onClick={togglePlayPause}
            disabled={!isReady}
            className={`flex ${btnSize} shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-opacity disabled:opacity-40`}
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? (
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="4" width="4" height="16" rx="1" />
                <rect x="14" y="4" width="4" height="16" rx="1" />
              </svg>
            ) : (
              <svg className="ml-0.5 h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="6,3 20,12 6,21" />
              </svg>
            )}
          </button>

          {/* Waveform container */}
          <div ref={containerRef} className="flex-1 min-w-0" />

          {/* Time display */}
          <div className="shrink-0 text-xs font-mono text-steel tabular-nums">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>
        </div>
      </div>
    );
  },
);
