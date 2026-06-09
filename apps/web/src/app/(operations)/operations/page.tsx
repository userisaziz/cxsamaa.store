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
import { Upload, CheckCircle, XCircle, Loader2, FileAudio } from "lucide-react";
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
  const { data: brands = [] } = useQuery({
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

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-[28px] font-semibold tracking-tight text-ink leading-tight">Upload Recording</h1>
        <p className="mt-1 text-sm text-steel">
          Upload audio recordings for salespeople. Select the hierarchy, pick a
          file, and upload.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Upload Form */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-lg">New Upload</CardTitle>
            <CardDescription>
              Select brand, store, and salesperson, then upload an audio file.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Cascading Selectors */}
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label>Brand</Label>
                <Select
                  value={selectedBrandId}
                  onValueChange={(v) => v && setSelectedBrandId(v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select brand" />
                  </SelectTrigger>
                  <SelectContent>
                    {brands.map((b: Brand) => (
                      <SelectItem key={b.id} value={b.id}>
                        {b.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label>Store</Label>
                <Select
                  value={selectedStoreId}
                  onValueChange={(v) => v && setSelectedStoreId(v)}
                  disabled={!selectedBrandId}
                >
                  <SelectTrigger>
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
                >
                  <SelectTrigger>
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
              className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
                isDragging
                  ? "border-brand-green bg-brand-green-soft"
                  : selectedFile
                    ? "border-brand-green bg-brand-green-soft"
                    : "border-border hover:border-brand-green/50 hover:bg-surface"
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
                  <FileAudio className="h-8 w-8 text-brand-green-deep" />
                  <div>
                    <p className="text-sm font-medium text-ink">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-steel">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                  <CheckCircle className="h-5 w-5 text-brand-green-deep" />
                </div>
              ) : (
                <>
                  <Upload className="mb-2 h-8 w-8 text-steel" />
                  <p className="text-sm font-medium text-ink">
                    Drag & drop audio file here
                  </p>
                  <p className="text-xs text-steel">
                    or click to browse (WAV, MP3, M4A)
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
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Today&apos;s Uploads</CardTitle>
            <CardDescription>{todayStr}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-lg bg-brand-green-soft p-3 text-center">
                <p className="text-2xl font-semibold text-brand-green-deep">
                  {completedCount}
                </p>
                <p className="text-xs text-brand-green-deep">Completed</p>
              </div>
              <div className="rounded-lg bg-blue-50 p-3 text-center">
                <p className="text-2xl font-semibold text-blue-700">
                  {processingCount}
                </p>
                <p className="text-xs text-blue-600">Processing</p>
              </div>
              <div className="rounded-lg bg-destructive/10 p-3 text-center">
                <p className="text-2xl font-semibold text-destructive">
                  {failedCount}
                </p>
                <p className="text-xs text-destructive">Failed</p>
              </div>
            </div>

            {/* Recent uploads list */}
            {recordings.length > 0 && (
              <div className="mt-4 space-y-2">
                <p className="text-xs font-medium uppercase tracking-wide text-steel">
                  Recent
                </p>
                {recordings.slice(0, 5).map((r: Recording) => (
                  <div
                    key={r.id}
                    className="flex items-center justify-between rounded-md border border-border p-2"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-ink">
                        {r.file_url.split("/").pop() || r.file_url}
                      </p>
                      <p className="text-xs text-steel">
                        {r.salesperson_id.slice(0, 8)}...
                      </p>
                    </div>
                    <StatusBadge status={r.status} />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Upload Queue */}
      {uploadQueue.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="text-lg">Upload Queue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {uploadQueue.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between rounded-md border border-border p-3"
                >
                  <div className="flex items-center gap-3">
                    {item.status === "uploading" && (
                      <Loader2 className="h-4 w-4 animate-spin text-brand-tag" />
                    )}
                    {item.status === "success" && (
                      <CheckCircle className="h-4 w-4 text-brand-green-deep" />
                    )}
                    {item.status === "error" && (
                      <XCircle className="h-4 w-4 text-destructive" />
                    )}
                    <div>
                      <p className="text-sm font-medium text-ink">
                        {item.file.name}
                      </p>
                      <p className="text-xs text-steel">
                        {item.salespersonName} &middot;{" "}
                        {new Date(item.recordedAt).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs font-medium text-steel">
                    {item.status === "uploading"
                      ? "Uploading..."
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
