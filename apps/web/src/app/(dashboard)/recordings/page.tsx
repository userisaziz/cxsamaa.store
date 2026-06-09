"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api-client";
import type { Recording } from "@samaa/shared";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Mic, ChevronLeft, ChevronRight, RefreshCw, Eye, Download } from "lucide-react";
import Link from "next/link";

const STATUSES = [
  { value: "ALL", label: "All Statuses" },
  { value: "UPLOADED", label: "Uploaded" },
  { value: "PREPROCESSING", label: "Preprocessing" },
  { value: "TRANSCRIBING", label: "Transcribing" },
  { value: "DIARIZING", label: "Diarizing" },
  { value: "SEGMENTING", label: "Segmenting" },
  { value: "ANALYZING", label: "Analyzing" },
  { value: "SCORING", label: "Scoring" },
  { value: "COMPLETED", label: "Completed" },
  { value: "FAILED", label: "Failed" },
];

function formatDuration(seconds: number | null): string {
  if (!seconds) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function RecordingsPage() {
  const searchParams = useSearchParams();
  const initialSalespersonFilter = searchParams.get("salesperson_id") || "";

  const [statusFilter, setStatusFilter] = useState("ALL");
  const [salespersonFilter] = useState(initialSalespersonFilter);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const queryParams = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (statusFilter !== "ALL") {
    queryParams.set("status", statusFilter);
  }
  if (salespersonFilter) {
    queryParams.set("salesperson_id", salespersonFilter);
  }
  if (dateFrom) {
    queryParams.set("date_from", dateFrom);
  }
  if (dateTo) {
    queryParams.set("date_to", dateTo);
  }

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["recordings", statusFilter, page, dateFrom, dateTo],
    queryFn: () =>
      api.get<{ items: Recording[]; total: number; page: number; total_pages: number }>(
        `/recordings?${queryParams.toString()}`,
      ),
    refetchInterval: (query) => {
      // Auto-refresh while any recording is processing
      const recordings = query.state.data?.items ?? [];
      const isProcessing = recordings.some((r) =>
        ["UPLOADED", "PREPROCESSING", "TRANSCRIBING", "DIARIZING", "SEGMENTING", "ANALYZING", "SCORING"].includes(r.status),
      );
      return isProcessing ? 5000 : false;
    },
  });

  const recordings = data?.items ?? [];
  const totalPages = data?.total_pages ?? 1;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Recordings</h1>
          <p className="text-sm text-steel">
            {data?.total ?? 0} total recordings
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const url = `${process.env.NEXT_PUBLIC_API_URL}/recordings/export/recordings`;
              window.open(url, "_blank");
            }}
          >
            <Download className="mr-2 h-4 w-4" />
            CSV
          </Button>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center gap-4 flex-wrap">
        <Select value={statusFilter} onValueChange={(v) => v && setStatusFilter(v)}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            {STATUSES.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex items-center gap-2">
          <label className="text-sm text-muted-foreground">From:</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-muted-foreground">To:</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          />
        </div>
        {(dateFrom || dateTo) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => { setDateFrom(""); setDateTo(""); setPage(1); }}
          >
            Clear dates
          </Button>
        )}
      </div>

      {/* Recordings Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mic className="h-4 w-4" />
            Audio Recordings
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Recorded</TableHead>
                    <TableHead>Uploaded</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Format</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recordings.map((rec) => (
                    <TableRow key={rec.id}>
                      <TableCell className="text-muted-foreground">
                        {rec.recorded_at ? formatDate(rec.recorded_at) : "—"}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDate(rec.uploaded_at)}
                      </TableCell>
                      <TableCell>{formatDuration(rec.duration_seconds)}</TableCell>
                      <TableCell className="text-muted-foreground">{rec.format}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {rec.file_size ? `${(rec.file_size / 1024 / 1024).toFixed(1)} MB` : "—"}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={rec.status} />
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          {rec.status === "COMPLETED" && (
                            <Link href={`/recordings/${rec.id}`}>
                              <Button variant="ghost" size="sm">
                                <Eye className="mr-1 h-4 w-4" />
                                View
                              </Button>
                            </Link>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              if (rec.status === "FAILED" || rec.status === "UPLOADED") {
                                api.post(`/recordings/${rec.id}/reprocess`).then(() => refetch());
                              }
                            }}
                            disabled={rec.status === "COMPLETED"}
                          >
                            {rec.status === "COMPLETED" ? "Done" : "Reprocess"}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {recordings.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                        No recordings found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-4">
                  <p className="text-sm text-muted-foreground">
                    Page {page} of {totalPages}
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
