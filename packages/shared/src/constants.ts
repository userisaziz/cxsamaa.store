// Shared constants for CXSAMAA platform

export const ROLES = {
  SUPER_ADMIN: "SUPER_ADMIN",
  BRAND_ADMIN: "BRAND_ADMIN",
  STORE_MANAGER: "STORE_MANAGER",
  SALESPERSON: "SALESPERSON",
  OPERATOR: "OPERATOR",
} as const;

export type Role = (typeof ROLES)[keyof typeof ROLES];

export const RECORDING_STATUSES = {
  UPLOADED: "UPLOADED",
  PREPROCESSING: "PREPROCESSING",
  TRANSCRIBING: "TRANSCRIBING",
  DIARIZING: "DIARIZING",
  SEGMENTING: "SEGMENTING",
  ANALYZING: "ANALYZING",
  SCORING: "SCORING",
  COMPLETED: "COMPLETED",
  FAILED: "FAILED",
} as const;

export type RecordingStatus =
  (typeof RECORDING_STATUSES)[keyof typeof RECORDING_STATUSES];

export const OUTCOMES = {
  SALE_MADE: "SALE_MADE",
  LOST: "LOST",
  FOLLOW_UP_NEEDED: "FOLLOW_UP_NEEDED",
} as const;

export type Outcome = (typeof OUTCOMES)[keyof typeof OUTCOMES];

export const AUDIO_FORMATS = ["WAV", "MP3", "M4A"] as const;
export type AudioFormat = (typeof AUDIO_FORMATS)[number];

export const MIN_AUDIO_DURATION_SECONDS = 60;
export const MAX_AUDIO_DURATION_SECONDS = 12 * 60 * 60; // 12 hours
