"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api-client";
import type { Recording } from "@samaa/shared";
import { StatusBadge } from "@/components/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
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
import { Mic, ChevronLeft, ChevronRight, RefreshCw, Eye, Download, Inbox } from "lucide-react";
import { Input } from "@/components/ui/input";
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

function TableSkeleton() {
  return (
    <div className="space-y-3 py-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-2">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-12" />
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-5 w-20 rounded-full" />
          <div className="flex-1" />
          <Skeleton className="h-8 w-16 rounded-lg" />
        </div>
      ))}
    </div>
  );
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
    <div className="space-y-6 lg:space-y-8 p-4 sm:p-6 lg:p-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4 sm:pb-6">
        <div>
          <h1 className="text-[22px] sm:text-[28px] font-semibold tracking-tight text-ink leading-tight">Audio Sources</h1>
          <p className="mt-1 text-sm text-steel">
            <span className="font-mono">{data?.total ?? 0}</span> uploaded audio files · <Link href="/conversations" className="text-brand-green-deep hover:underline font-medium">View all conversations →</Link>
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
            Export CSV
          </Button>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <Card className="shadow-none border-border">
        <CardContent className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 flex-wrap py-4">
          <Select value={statusFilter} onValueChange={(v) => v && setStatusFilter(v)}>
            <SelectTrigger className="w-full sm:w-[180px]">
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
            <label className="text-sm text-steel">From:</label>
            <Input
              type="date"
              value={dateFrom}
              onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
              className="h-9 w-auto"
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-steel">To:</label>
            <Input
              type="date"
              value={dateTo}
              onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
              className="h-9 w-auto"
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
        </CardContent>
      </Card>

      {/* Recordings Table */}
      <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mic className="h-4 w-4 text-steel" />
            Audio Recordings
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton />
          ) : recordings.length > 0 ? (
            <>
              <div className="overflow-x-auto -mx-6 sm:mx-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Recorded</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Duration</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Status</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Conversations</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recordings.map((rec) => (
                    <TableRow key={rec.id}>
                      <TableCell className="text-steel font-mono text-[13px]">
                        {rec.recorded_at ? formatDate(rec.recorded_at) : formatDate(rec.uploaded_at)}
                      </TableCell>
                      <TableCell className="font-mono text-sm">{formatDuration(rec.duration_seconds)}</TableCell>
                      <TableCell>
                        <StatusBadge status={rec.status} />
                      </TableCell>
                      <TableCell className="text-steel text-sm">
                        {rec.status === "COMPLETED" ? (
                          <Link href={`/recordings/${rec.id}`} className="text-brand-green-deep hover:underline">
                            View conversations
                          </Link>
                        ) : (
                          <span className="text-stone">Processing...</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          {rec.status === "COMPLETED" && (
                            <Link href={`/recordings/${rec.id}`}>
                              <Button variant="ghost" size="sm">
                                <Eye className="mr-1 h-4 w-4" />
                                Details
                              </Button>
                            </Link>
                          )}
                          {(rec.status === "FAILED" || rec.status === "UPLOADED") && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                api.post(`/recordings/${rec.id}/reprocess`).then(() => refetch());
                              }}
                            >
                              Reprocess
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-4 border-t border-border mt-4">
                  <p className="text-sm text-steel">
                    Page <span className="font-mono font-medium text-ink">{page}</span> of <span className="font-mono font-medium text-ink">{totalPages}</span>
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
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Inbox className="h-10 w-10 text-stone/40 mb-3" />
              <p className="text-sm font-medium text-steel">No audio sources found</p>
              <p className="text-xs text-stone mt-1">
                Upload audio files to start analyzing customer conversations, or <Link href="/conversations" className="text-brand-green-deep hover:underline">view all conversations →</Link>
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
