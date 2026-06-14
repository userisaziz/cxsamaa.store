"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
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
import { Upload, CheckCircle, XCircle, Loader2, FileAudio, Clock, Mic, Inbox, Activity, Zap } from "lucide-react";
import type { Brand, Store, Salesperson, Recording } from "@samaa/shared";

interface UploadItem {
  file: File;
  salespersonId: string;
  salespersonName: string;
  recordedAt: string;
  status: "pending" | "uploading" | "success" | "error";
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

  // Fetch brands
  const {
    data: brands = [],
    isLoading: brandsLoading,
    error: brandsError,
  } = useQuery({
    queryKey: ["brands"],
    queryFn: () => api.get<Brand[]>("/brands"),
  });

  // Fetch stores (filtered by brand)
  const { data: stores = [] } = useQuery({
    queryKey: ["stores", selectedBrandId],
    queryFn: () =>
      api.get<Store[]>(
        `/stores${selectedBrandId ? `?brand_id=${selectedBrandId}` : ""}`
      ),
    enabled: !!selectedBrandId,
  });

  // Fetch salespeople (filtered by store)
  const { data: salespeople = [] } = useQuery({
    queryKey: ["salespeople", selectedStoreId],
    queryFn: () =>
      api.get<Salesperson[]>(
        `/salespeople${selectedStoreId ? `?store_id=${selectedStoreId}` : ""}`
      ),
    enabled: !!selectedStoreId,
  });

  // Fetch today's recordings
  const todayStr = new Date().toISOString().split("T")[0];
  const { data: todayRecordings } = useQuery({
    queryKey: ["recordings", "today"],
    queryFn: () =>
      api.get<{ items: Recording[]; total: number }>(
        `/recordings?page_size=100&date_from=${todayStr}T00:00:00&date_to=${todayStr}T23:59:59`
      ),
    refetchInterval: 10000,
  });

  // Fetch active pipeline recordings
  const { data: activePipeline = [] } = useQuery({
    queryKey: ["pipeline", "active"],
    queryFn: () => api.get<Array<{
      id: string;
      status: string;
      duration_seconds: number | null;
      uploaded_at: string | null;
      file_url: string;
      salesperson_id: string;
    }>>("/recordings/pipeline/active"),
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
    (s: Salesperson) => s.id === selectedSalespersonId
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
      file: selectedFile,
      salespersonId: selectedSalespersonId,
      salespersonName: selectedSalesperson.name,
      recordedAt,
      status: "uploading",
    };

    setUploadQueue((prev) => [uploadItem, ...prev]);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("salesperson_id", selectedSalespersonId);
      formData.append("recorded_at", recordedAt);

      const response = await api.post<Recording>(
        "/recordings/upload",
        formData
      );

      setUploadQueue((prev) =>
        prev.map((item) =>
          item === uploadItem
            ? { ...item, status: "success", recordingId: response.id }
            : item
        )
      );

      // Reset form
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      queryClient.invalidateQueries({ queryKey: ["recordings"] });
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Upload failed";
      setUploadQueue((prev) =>
        prev.map((item) =>
          item === uploadItem
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
                  disabled={brandsLoading}
                  items={brands.map((b: Brand) => ({ label: b.name, value: b.id }))}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue
                      placeholder={
                        brandsLoading
                          ? "Loading..."
                          : brandsError
                            ? "Error loading brands"
                            : brands.length === 0
                              ? "No brands found"
                              : "Select brand"
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {brands.map((b: Brand) => (
                      <SelectItem key={b.id} value={b.id}>
                        {b.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {brandsError && (
                  <p className="text-xs text-destructive">
                    Failed to load brands: {brandsError.message}
                  </p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label>Store</Label>
                <Select
                  value={selectedStoreId}
                  onValueChange={(v) => v && setSelectedStoreId(v)}
                  disabled={!selectedBrandId}
                  items={stores.map((s: Store) => ({ label: s.name, value: s.id }))}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue
                      placeholder={
                        selectedBrandId ? "Select store" : "Select brand first"
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {stores.map((s: Store) => (
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
                  items={salespeople.map((s: Salesperson) => ({ label: `${s.name}${s.device_number ? ` (#${s.device_number})` : ""}`, value: s.id }))}
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
                    {salespeople.map((s: Salesperson) => (
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
            <div className="grid grid-cols-3 gap-3">
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
                      <StatusBadge status={r.status} />
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
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {activePipeline.map((rec) => (
                <div
                  key={rec.id}
                  className="flex items-center justify-between gap-4 rounded-lg border border-border p-3 transition-all hover:bg-surface/50"
                >
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-tag/8">
                      <Loader2 className="h-4 w-4 animate-spin text-brand-tag" />
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
                  <div className="flex items-center gap-3">
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
            <div className="divide-y divide-border">
              {uploadQueue.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${
                      item.status === "uploading"
                        ? "bg-brand-tag/8"
                        : item.status === "success"
                          ? "bg-brand-green-soft"
                          : "bg-destructive/8"
                    }`}>
                      {item.status === "uploading" && (
                        <Loader2 className="h-4 w-4 animate-spin text-brand-tag" />
                      )}
                      {item.status === "success" && (
                        <CheckCircle className="h-4 w-4 text-brand-green-deep" />
                      )}
                      {item.status === "error" && (
                        <XCircle className="h-4 w-4 text-destructive" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink truncate">
                        {item.file.name}
                      </p>
                      <p className="text-xs text-steel">
                        {item.salespersonName}{" "}
                        <span className="text-stone font-mono">
                          {new Date(item.recordedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </p>
                    </div>
                  </div>
                  <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    item.status === "uploading"
                      ? "bg-brand-tag/8 text-brand-tag"
                      : item.status === "success"
                        ? "bg-brand-green-soft text-brand-green-deep"
                        : "bg-destructive/8 text-destructive"
                  }`}>
                    {item.status === "uploading"
                      ? "Uploading"
                      : item.status === "success"
                        ? "Done"
                        : item.error || "Failed"}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
