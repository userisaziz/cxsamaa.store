"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StatusBadge } from "@/components/status-badge";
import { Upload, CheckCircle, XCircle, Loader2, FileAudio, Clock, Mic, Inbox, Activity, Zap, Trash2 } from "lucide-react";
import { PipelineStepper } from "@/components/pipeline-stepper";
import { PipelineActionButtons } from "@/components/pipeline-action-buttons";
import type { Recording } from "@samaa/shared";

interface UploadItem {
  id: string; // Unique ID for state updates
  file: File;
  salespersonId: string;
  salespersonName: string;
  recordedAt: string;
  status: "pending" | "uploading" | "success" | "error";
  progress: number; // 0-100
  error?: string;
  recordingId?: string;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return "";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatRecordedTime(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

export default function OperationsPage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedBrandId, setSelectedBrandId] = useState<string>("");
  const [selectedStoreId, setSelectedStoreId] = useState<string>("");
  const [selectedSalespersonId, setSelectedSalespersonId] = useState<string>("");
  const [recordedDate, setRecordedDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [recordedTime, setRecordedTime] = useState<string>(
    new Date().toTimeString().slice(0, 5)
  );
  const [uploadQueue, setUploadQueue] = useState<UploadItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Fetch complete hierarchy in single call
  const {
    data: hierarchyData,
    isLoading: hierarchyLoading,
    error: hierarchyError,
  } = useQuery({
    queryKey: ["hierarchy"],
    queryFn: () => api.get<{
      brands: Array<{
        id: string;
        name: string;
        description: string | null;
        stores: Array<{
          id: string;
          name: string;
          location: string | null;
          salespeople: Array<{
            id: string;
            name: string;
            device_number: string | null;
          }>;
        }>;
      }>;
    }>("/hierarchy"),
  });

  // Extract flat lists from hierarchy for compatibility with existing logic
  const brands = hierarchyData?.brands ?? [];
  const stores = selectedBrandId 
    ? (brands.find(b => b.id === selectedBrandId)?.stores ?? [])
    : [];
  const salespeople = selectedStoreId
    ? (stores.find(s => s.id === selectedStoreId)?.salespeople ?? [])
    : [];

  // Fetch today's recordings
  const todayStr = new Date().toISOString().split("T")[0];
  const { data: todayRecordings } = useQuery({
    queryKey: ["recordings", "today"],
    queryFn: () =>
      api.get<{ items: Recording[]; total: number }>(
        `/recordings?page_size=100&date_from=${todayStr}T00:00:00&date_to=${todayStr}T23:59:59`
      ),
    refetchInterval: 30000,
  });

  // Fetch active pipeline recordings with pipeline_state
  const { data: activePipeline = [] } = useQuery({
    queryKey: ["pipeline", "active"],
    queryFn: () => api.get<Array<{
      id: string;
      status: string;
      duration_seconds: number | null;
      uploaded_at: string | null;
      file_url: string;
      salesperson_id: string;
      pipeline_state: {
        current_stage?: string;
        completed_stages?: string[];
        failed_stage?: string | null;
        error_message?: string | null;
        stage_timestamps?: Record<string, string>;
        retry_count?: Record<string, number>;
      };
    }>>('/recordings/pipeline/active'),
    refetchInterval: 3000, // Poll every 3 seconds for real-time updates
  });

  // Reset cascading selectors
  useEffect(() => {
    setSelectedStoreId("");
    setSelectedSalespersonId("");
  }, [selectedBrandId]);

  useEffect(() => {
    setSelectedSalespersonId("");
  }, [selectedStoreId]);

  const selectedSalesperson = salespeople.find(
    (s) => s.id === selectedSalespersonId
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && isValidAudioFile(file)) {
      setSelectedFile(file);
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && isValidAudioFile(file)) {
      setSelectedFile(file);
    }
  };

  function isValidAudioFile(file: File): boolean {
    const validTypes = [
      "audio/wav",
      "audio/mpeg",
      "audio/mp3",
      "audio/mp4",
      "audio/x-m4a",
      "audio/m4a",
    ];
    const validExtensions = [".wav", ".mp3", ".m4a"];
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
    return validTypes.includes(file.type) || validExtensions.includes(ext);
  }

  const handleUpload = async () => {
    if (!selectedFile || !selectedSalespersonId || !selectedSalesperson) return;

    const recordedAt = `${recordedDate}T${recordedTime}:00`;

    const uploadItem: UploadItem = {
      id: `upload-${Date.now()}-${selectedFile.name}`,
      file: selectedFile,
      salespersonId: selectedSalespersonId,
      salespersonName: selectedSalesperson.name,
      recordedAt,
      status: "uploading",
      progress: 0,
    };

    setUploadQueue((prev) => [uploadItem, ...prev]);

    try {
      // Step 1: Get pre-signed upload URL from API
      const presignData = await api.post<{
        upload_url: string;
        recording_id: string;
        file_key: string;
      }>("/recordings/presign-upload", {
        filename: selectedFile.name,
        content_type: selectedFile.type,
        salesperson_id: selectedSalespersonId,
        recorded_at: recordedAt,
      });

      // Step 2: Upload directly to R2 (bypasses API server)
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        
        // Set timeout for large files (10 minutes for 9-hour audio)
        xhr.timeout = 600000; // 10 minutes in milliseconds
        
        xhr.open("PUT", presignData.upload_url);
        xhr.setRequestHeader("Content-Type", selectedFile.type);

        console.log('🚀 Starting R2 upload:', {
          fileSize: selectedFile.size,
          fileName: selectedFile.name,
          fileType: selectedFile.type,
          uploadUrl: presignData.upload_url.substring(0, 80) + '...'
        });

        // Track upload progress
        xhr.upload.addEventListener("progress", (e) => {
          if (e.lengthComputable) {
            const percentComplete = Math.round((e.loaded / e.total) * 100);
            console.log(`📊 Upload progress: ${percentComplete}% (${Math.round(e.loaded / 1024 / 1024)}MB / ${Math.round(e.total / 1024 / 1024)}MB)`);
            setUploadQueue((prev) =>
              prev.map((item) =>
                item.id === uploadItem.id ? { ...item, progress: percentComplete } : item
              )
            );
          } else {
            console.log('📊 Upload progress: Length not computable', { loaded: e.loaded });
          }
        });

        xhr.upload.addEventListener('loadstart', () => {
          console.log('✅ Upload started');
        });

        xhr.upload.addEventListener('loadend', () => {
          console.log('🏁 Upload loadend event fired');
        });

        xhr.onload = () => {
          console.log('✅ Upload completed:', {
            status: xhr.status,
            statusText: xhr.statusText,
            response: xhr.responseText.substring(0, 200)
          });
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve();
          } else {
            // Log detailed error for debugging
            console.error('R2 upload failed:', {
              status: xhr.status,
              statusText: xhr.statusText,
              response: xhr.responseText,
              url: presignData.upload_url.substring(0, 100)
            });
            reject(new Error(`R2 upload failed: ${xhr.status} ${xhr.statusText}. Check browser console for details.`));
          }
        };

        xhr.onerror = () => {
          console.error('❌ R2 network error:', {
            url: presignData.upload_url.substring(0, 100),
            readyState: xhr.readyState,
            status: xhr.status
          });
          reject(new Error('Network error during R2 upload. This is likely a CORS issue - contact support.'));
        };
        
        xhr.ontimeout = () => {
          console.error('⏱️ R2 upload timeout after 10 minutes');
          reject(new Error('R2 upload timeout - file too large or network too slow'));
        };

        xhr.send(selectedFile);
        console.log('📤 File sent to R2');
      });

      // Step 3: Confirm upload and start pipeline
      const response = await api.post<Recording>(
        `/recordings/${presignData.recording_id}/confirm-upload`,
        { file_size: selectedFile.size }
      );

      setUploadQueue((prev) =>
        prev.map((item) =>
          item.id === uploadItem.id
            ? { ...item, status: "success", progress: 100, recordingId: response.id }
            : item
        )
      );

      // Reset form
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      
      // Immediately refresh both recordings and active pipeline to show the new upload in processing
      queryClient.invalidateQueries({ queryKey: ["recordings"] });
      queryClient.invalidateQueries({ queryKey: ["pipeline", "active"] });
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Upload failed";
      setUploadQueue((prev) =>
        prev.map((item) =>
          item.id === uploadItem.id
            ? { ...item, status: "error", error: errorMsg }
            : item
        )
      );
    }
  };

  const recordings = todayRecordings?.items ?? [];
  const completedCount = recordings.filter(
    (r: Recording) => r.status === "COMPLETED"
  ).length;
  const processingCount = recordings.filter(
    (r: Recording) => !["COMPLETED", "FAILED"].includes(r.status)
  ).length;
  const failedCount = recordings.filter((r: Recording) => r.status === "FAILED").length;
  const uploadedCount = recordings.filter((r: Recording) => r.status === "UPLOADED").length;

  const handlePipelineAction = () => {
    queryClient.invalidateQueries({ queryKey: ["pipeline", "active"] });
    queryClient.invalidateQueries({ queryKey: ["recordings"] });
  };

  const handleDeleteRecording = async (recordingId: string) => {
    if (!confirm("Are you sure you want to delete this recording? This action cannot be undone.")) {
      return;
    }

    try {
      await api.delete(`/recordings/${recordingId}`);
      toast.success("Recording deleted successfully", {
        description: "The recording and all associated data have been removed.",
      });
      queryClient.invalidateQueries({ queryKey: ["pipeline", "active"] });
      queryClient.invalidateQueries({ queryKey: ["recordings"] });
    } catch (error) {
      console.error("Failed to delete recording:", error);
      toast.error("Failed to delete recording", {
        description: "Please try again or contact support if the issue persists.",
      });
    }
  };

  const handleReuploadRecording = async (recordingId: string) => {
    if (!confirm("Generate a new upload URL for this recording? The previous file (if any) will be overwritten.")) {
      return;
    }

    try {
      const response = await api.post(`/recordings/${recordingId}/re-upload`);
      const { upload_url, file_key } = response;

      toast.info("Upload URL generated", {
        description: "Please select an audio file to upload.",
      });

      // Prompt user to select file
      const fileInput = document.createElement("input");
      fileInput.type = "file";
      fileInput.accept = "audio/*";
      
      fileInput.onchange = async (e: Event) => {
        const target = e.target as HTMLInputElement;
        const file = target.files?.[0];
        if (!file) return;

        try {
          // Upload to R2
          await fetch(upload_url, {
            method: "PUT",
            body: file,
            headers: {
              "Content-Type": file.type,
            },
          });

          // Confirm upload
          await api.post(`/recordings/${recordingId}/confirm-upload`, {
            file_size: file.size,
          });

          toast.success("File uploaded successfully!", {
            description: "Recording is ready for processing.",
            icon: "🎵",
          });
          queryClient.invalidateQueries({ queryKey: ["pipeline", "active"] });
          queryClient.invalidateQueries({ queryKey: ["recordings"] });
        } catch (error) {
          console.error("Failed to upload file:", error);
          toast.error("Failed to upload file", {
            description: "Please try again or check the file format.",
          });
        }
      };

      fileInput.click();
    } catch (error) {
      console.error("Failed to generate upload URL:", error);
      toast.error("Failed to generate upload URL", {
        description: "Please try again or contact support.",
      });
    }
  };

  const todayFormatted = new Date().toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      {/* Page Header */}
      <div className="border-b border-border pb-5 sm:pb-6 mb-5 sm:mb-6">
        <h1 className="text-[28px] font-semibold tracking-[-0.02em] text-ink leading-tight">
          Upload Recording
        </h1>
        <p className="mt-1.5 text-sm text-slate">
          Select the brand, store, and salesperson hierarchy, then upload an audio file for analysis.
        </p>
      </div>

      <div className="grid gap-5 lg:gap-6 lg:grid-cols-5">
        {/* Upload Form */}
        <Card className="lg:col-span-3 shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
          <CardHeader>
            <CardTitle>New Upload</CardTitle>
            <CardDescription>
              Select brand, store, and salesperson, then upload an audio file.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Cascading Selectors */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="space-y-1.5">
                <Label>Brand</Label>
                <Select
                  value={selectedBrandId}
                  onValueChange={(v) => v && setSelectedBrandId(v)}
                  disabled={hierarchyLoading}
                  items={brands.map((b) => ({ label: b.name, value: b.id }))}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue
                      placeholder={
                        hierarchyLoading
                          ? "Loading..."
                          : hierarchyError
                            ? "Error loading hierarchy"
                            : brands.length === 0
                              ? "No brands found"
                              : "Select brand"
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {brands.map((b) => (
                      <SelectItem key={b.id} value={b.id}>
                        {b.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {hierarchyError && (
                  <p className="text-xs text-destructive">
                    Failed to load hierarchy: {hierarchyError.message}
                  </p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label>Store</Label>
                <Select
                  value={selectedStoreId}
                  onValueChange={(v) => v && setSelectedStoreId(v)}
                  disabled={!selectedBrandId}
                  items={stores.map((s) => ({ label: s.name, value: s.id }))}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue
                      placeholder={
                        selectedBrandId ? "Select store" : "Select brand first"
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {stores.map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label>Salesperson</Label>
                <Select
                  value={selectedSalespersonId}
                  onValueChange={(v) => v && setSelectedSalespersonId(v)}
                  disabled={!selectedStoreId}
                  items={salespeople.map((s) => ({ label: `${s.name}${s.device_number ? ` (#${s.device_number})` : ""}`, value: s.id }))}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue
                      placeholder={
                        selectedStoreId
                          ? "Select salesperson"
                          : "Select store first"
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {salespeople.map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.name}
                        {s.device_number ? ` (#${s.device_number})` : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Date/Time */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Recorded Date</Label>
                <Input
                  type="date"
                  value={recordedDate}
                  onChange={(e) => setRecordedDate(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Recorded Time</Label>
                <Input
                  type="time"
                  value={recordedTime}
                  onChange={(e) => setRecordedTime(e.target.value)}
                />
              </div>
            </div>

            {/* File Drop Zone */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`group relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-all duration-200 ${
                isDragging
                  ? "border-brand-green bg-brand-green-soft scale-[1.01]"
                  : selectedFile
                    ? "border-brand-green/60 bg-brand-green-soft/50"
                    : "border-border hover:border-steel/40 hover:bg-surface"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".wav,.mp3,.m4a,audio/*"
                onChange={handleFileSelect}
                className="hidden"
              />
              {selectedFile ? (
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-green-soft">
                    <FileAudio className="h-5 w-5 text-brand-green-deep" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-ink">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-steel font-mono">
                      {formatFileSize(selectedFile.size)}
                    </p>
                  </div>
                  <CheckCircle className="h-5 w-5 text-brand-green-deep" />
                </div>
              ) : (
                <>
                  <div className={`mb-3 flex h-12 w-12 items-center justify-center rounded-xl transition-colors duration-200 ${
                    isDragging ? "bg-brand-green-soft" : "bg-surface"
                  }`}>
                    <Upload className={`h-5 w-5 transition-colors duration-200 ${
                      isDragging ? "text-brand-green-deep" : "text-steel"
                    }`} />
                  </div>
                  <p className="text-sm font-medium text-ink">
                    {isDragging ? "Drop file to upload" : "Drag and drop audio file"}
                  </p>
                  <p className="mt-0.5 text-xs text-steel">
                    or click to browse. Supports WAV, MP3, M4A
                  </p>
                </>
              )}
            </div>

            {/* Upload Button */}
            <Button
              onClick={handleUpload}
              disabled={
                !selectedFile ||
                !selectedSalespersonId ||
                uploadQueue.some((u) => u.status === "uploading")
              }
              size="lg"
              className="w-full"
            >
              {uploadQueue.some((u) => u.status === "uploading") ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload Recording
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Today's Summary */}
        <Card className="lg:col-span-2 shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
          <CardHeader>
            <CardTitle>Today&apos;s Uploads</CardTitle>
            <CardDescription>{todayFormatted}</CardDescription>
          </CardHeader>
          <CardContent>
            {/* Stat boxes */}
            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg bg-surface p-3 text-center">
                <p className="text-2xl font-semibold text-steel font-mono">
                  {uploadedCount}
                </p>
                <p className="text-[11px] font-medium text-steel mt-0.5">Uploaded</p>
              </div>
              <div className="rounded-lg bg-brand-green-soft p-3 text-center">
                <p className="text-2xl font-semibold text-brand-green-deep font-mono">
                  {completedCount}
                </p>
                <p className="text-[11px] font-medium text-brand-green-deep mt-0.5">Completed</p>
              </div>
              <div className="rounded-lg bg-brand-tag/8 p-3 text-center">
                <p className="text-2xl font-semibold text-brand-tag font-mono">
                  {processingCount}
                </p>
                <p className="text-[11px] font-medium text-brand-tag mt-0.5">Processing</p>
              </div>
              <div className="rounded-lg bg-destructive/8 p-3 text-center">
                <p className="text-2xl font-semibold text-destructive font-mono">
                  {failedCount}
                </p>
                <p className="text-[11px] font-medium text-destructive mt-0.5">Failed</p>
              </div>
            </div>

            {/* Recent uploads list */}
            {recordings.length > 0 ? (
              <div className="mt-5 space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-widest text-steel">
                  Recent
                </p>
                {recordings.slice(0, 6).map((r: Recording) => {
                  const fileName = r.file_url.split("/").pop() || r.file_url;
                  return (
                    <div
                      key={r.id}
                      className="flex items-center justify-between gap-3 rounded-lg border border-border p-2.5 transition-colors hover:bg-surface/50"
                    >
                      <div className="flex items-center gap-2.5 min-w-0 flex-1">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-surface">
                          <Mic className="h-3.5 w-3.5 text-steel" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-ink leading-snug">
                            {fileName}
                          </p>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <Clock className="h-3 w-3 text-stone shrink-0" />
                            <p className="text-xs text-steel font-mono">
                              {formatRecordedTime(r.recorded_at)}
                              {r.duration_seconds ? ` / ${formatDuration(r.duration_seconds)}` : ""}
                            </p>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={r.status} />
                        <PipelineActionButtons
                          recordingId={r.id}
                          status={r.status}
                          pipelineState={r.pipeline_state ?? undefined}
                          onAction={handlePipelineAction}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-surface mb-3">
                  <Inbox className="h-5 w-5 text-stone" />
                </div>
                <p className="text-sm font-medium text-slate">No uploads today</p>
                <p className="text-xs text-steel mt-0.5">
                  Files you upload will appear here with their pipeline status
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Active Pipeline Monitor */}
      {activePipeline.length > 0 && (
        <Card className="mt-6 shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)] border-l-4 border-l-brand-green">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-brand-green-deep" />
              <CardTitle>Active Pipeline Processing</CardTitle>
              <span className="ml-auto flex items-center gap-1.5 rounded-full bg-brand-green-soft px-2.5 py-1 text-xs font-medium text-brand-green-deep">
                <Zap className="h-3 w-3" />
                {activePipeline.length} active
              </span>
            </div>
            <CardDescription>
              Recordings currently being processed through the AI pipeline
            </CardDescription>
            
            {/* Bulk cleanup button */}
            {activePipeline.filter((r) => r.status === "PENDING_UPLOAD" || r.status === "FAILED").length > 0 && (
              <div className="mt-3 flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    const pendingFailed = activePipeline.filter(
                      (r) => r.status === "PENDING_UPLOAD" || r.status === "FAILED"
                    );
                    if (
                      !confirm(
                        `Delete ${pendingFailed.length} PENDING/FAILED recordings? This cannot be undone.`
                      )
                    ) {
                      return;
                    }
                    
                    // Delete all pending/failed recordings
                    for (const rec of pendingFailed) {
                      try {
                        await api.delete(`/recordings/${rec.id}`);
                      } catch (error) {
                        console.error(`Failed to delete ${rec.id}:`, error);
                      }
                    }
                    
                    toast.success("Cleanup complete", {
                      description: `${pendingFailed.length} recording${pendingFailed.length === 1 ? '' : 's'} deleted successfully.`,
                    });
                    queryClient.invalidateQueries({ queryKey: ["pipeline", "active"] });
                    queryClient.invalidateQueries({ queryKey: ["recordings"] });
                  }}
                  className="text-xs"
                >
                  <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                  Cleanup All PENDING/FAILED ({activePipeline.filter((r) => r.status === "PENDING_UPLOAD" || r.status === "FAILED").length})
                </Button>
              </div>
            )}
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {activePipeline.map((rec) => (
                <div
                  key={rec.id}
                  className="flex flex-col gap-3 rounded-lg border border-border p-4 transition-all hover:bg-surface/50"
                >
                  {/* Header with ID and status */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                        rec.status === "FAILED" 
                          ? "bg-destructive/10" 
                          : rec.status === "PENDING_UPLOAD"
                          ? "bg-surface"
                          : "bg-brand-tag/8"
                      }`}>
                        {rec.status === "FAILED" ? (
                          <XCircle className="h-4 w-4 text-destructive" />
                        ) : rec.status === "PENDING_UPLOAD" ? (
                          <Inbox className="h-4 w-4 text-stone" />
                        ) : (
                          <Loader2 className="h-4 w-4 animate-spin text-brand-tag" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-ink font-mono truncate">
                          {rec.id.slice(0, 8)}...
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <Clock className="h-3 w-3 text-stone shrink-0" />
                          <p className="text-xs text-steel font-mono">
                            {rec.duration_seconds ? `${Math.floor(rec.duration_seconds / 60)}:${(rec.duration_seconds % 60).toString().padStart(2, "0")}` : "Calculating..."}
                          </p>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={rec.status as any} />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          window.open(`/recordings/${rec.id}`, "_blank");
                        }}
                      >
                        View
                      </Button>
                    </div>
                  </div>

                  {/* Pipeline Stepper */}
                  {rec.pipeline_state && (
                    <PipelineStepper 
                      pipelineState={rec.pipeline_state} 
                      compact
                    />
                  )}

                  {/* Error Details for FAILED recordings */}
                  {rec.status === "FAILED" && (
                    <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-3">
                      <div className="flex items-start gap-2">
                        <XCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-semibold text-destructive mb-1">
                            Pipeline Failed at {rec.pipeline_state?.failed_stage || "Unknown Stage"}
                          </p>
                          {rec.pipeline_state?.error_message ? (
                            <p className="text-xs text-destructive/90 font-mono break-words leading-relaxed">
                              {rec.pipeline_state.error_message}
                            </p>
                          ) : (
                            <p className="text-xs text-destructive/70 italic">
                              No error details available. Check server logs for more information.
                            </p>
                          )}
                          {rec.pipeline_state?.retry_count && (
                            <div className="mt-2 flex items-center gap-1.5">
                              <span className="text-[10px] text-destructive/70">Retry attempts:</span>
                              {Object.entries(rec.pipeline_state.retry_count).map(([stage, count]) => (
                                <span
                                  key={stage}
                                  className="rounded bg-destructive/10 px-1.5 py-0.5 text-[10px] font-mono text-destructive"
                                >
                                  {stage}: {count}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Action buttons for UPLOADED/FAILED/COMPLETED */}
                  <PipelineActionButtons
                    recordingId={rec.id}
                    status={rec.status}
                    pipelineState={rec.pipeline_state}
                    onAction={handlePipelineAction}
                  />

                  {/* Delete and Re-upload buttons for PENDING_UPLOAD/FAILED */}
                  {(rec.status === "PENDING_UPLOAD" || rec.status === "FAILED") && (
                    <div className="flex items-center gap-2 pt-2 border-t border-border">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleReuploadRecording(rec.id)}
                        className="text-xs"
                      >
                        <Upload className="h-3.5 w-3.5 mr-1.5" />
                        Re-upload File
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDeleteRecording(rec.id)}
                        className="text-xs text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                        Delete
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Upload Queue */}
      {uploadQueue.length > 0 && (
        <Card className="mt-6 shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
          <CardHeader>
            <CardTitle>Upload Queue</CardTitle>
            <CardDescription>
              {uploadQueue.filter((u) => u.status === "uploading").length > 0
                ? `${uploadQueue.filter((u) => u.status === "uploading").length} uploading`
                : "All uploads complete"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {uploadQueue.map((item, idx) => (
                <div
                  key={idx}
                  className={`rounded-lg border p-3 transition-all duration-300 ${
                    item.status === "uploading"
                      ? "border-brand-tag/40 bg-brand-tag/5"
                      : item.status === "success"
                        ? "border-brand-green/40 bg-brand-green-soft/30"
                        : "border-destructive/40 bg-destructive/5"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-all duration-300 ${
                        item.status === "uploading"
                          ? "bg-brand-tag/15"
                          : item.status === "success"
                            ? "bg-brand-green-soft"
                            : "bg-destructive/10"
                      }`}>
                        {item.status === "uploading" && (
                          <Loader2 className="h-5 w-5 animate-spin text-brand-tag" />
                        )}
                        {item.status === "success" && (
                          <CheckCircle className="h-5 w-5 text-brand-green-deep" />
                        )}
                        {item.status === "error" && (
                          <XCircle className="h-5 w-5 text-destructive" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-ink truncate">
                          {item.file.name}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <p className="text-xs text-steel">
                            {item.salespersonName}
                          </p>
                          <span className="text-stone">•</span>
                          <p className="text-xs text-stone font-mono">
                            {new Date(item.recordedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </p>
                          <span className="text-stone">•</span>
                          <p className="text-xs text-stone font-mono">
                            {formatFileSize(item.file.size)}
                          </p>
                        </div>

                        {/* Progress bar for uploading */}
                        {item.status === "uploading" && (
                          <div className="mt-2.5">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs font-medium text-brand-tag">
                                Uploading...
                              </span>
                              <span className="text-xs font-semibold text-brand-tag font-mono">
                                {item.progress}%
                              </span>
                            </div>
                            <div className="h-2 w-full overflow-hidden rounded-full bg-brand-tag/15">
                              <div
                                className="h-full rounded-full bg-gradient-to-r from-brand-tag to-brand-green transition-all duration-300 ease-out"
                                style={{ width: `${item.progress}%` }}
                              />
                            </div>
                          </div>
                        )}

                        {/* Success message */}
                        {item.status === "success" && (
                          <div className="mt-2 flex items-center gap-1.5">
                            <CheckCircle className="h-3.5 w-3.5 text-brand-green-deep" />
                            <span className="text-xs font-medium text-brand-green-deep">
                              Upload complete — Ready for processing
                            </span>
                          </div>
                        )}

                        {/* Error message */}
                        {item.status === "error" && (
                          <div className="mt-2 flex items-start gap-1.5">
                            <XCircle className="h-3.5 w-3.5 text-destructive shrink-0 mt-0.5" />
                            <span className="text-xs text-destructive">
                              {item.error || "Upload failed"}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Status badge */}
                    <div className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${
                      item.status === "uploading"
                        ? "bg-brand-tag/15 text-brand-tag"
                        : item.status === "success"
                          ? "bg-brand-green-soft text-brand-green-deep"
                          : "bg-destructive/10 text-destructive"
                    }`}>
                      {item.status === "uploading"
                        ? `${item.progress}%`
                        : item.status === "success"
                          ? "Done"
                          : "Failed"}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
