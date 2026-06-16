"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
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
import { Mic, ChevronLeft, ChevronRight, RefreshCw, Inbox } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { PipelineActionButtons } from "@/components/pipeline-action-buttons";
import { useQueryClient } from "@tanstack/react-query";

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

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function OperationsHistoryPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("ALL");
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
  if (dateFrom) {
    queryParams.set("date_from", `${dateFrom}T00:00:00`);
  }
  if (dateTo) {
    queryParams.set("date_to", `${dateTo}T23:59:59`);
  }

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["operations-recordings", statusFilter, page, dateFrom, dateTo],
    queryFn: () =>
      api.get<{
        items: Recording[];
        total: number;
        page: number;
        total_pages: number;
      }>(`/recordings?${queryParams.toString()}`),
    refetchInterval: (query) => {
      const recordings = query.state.data?.items ?? [];
      const isProcessing = recordings.some((r) =>
        [
          "UPLOADED",
          "PREPROCESSING",
          "TRANSCRIBING",
          "DIARIZING",
          "SEGMENTING",
          "ANALYZING",
          "SCORING",
        ].includes(r.status)
      );
      return isProcessing ? 5000 : false;
    },
  });

  const recordings = data?.items ?? [];
  const totalPages = data?.total_pages ?? 1;

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4 sm:pb-6">
        <div>
          <h1 className="text-[22px] sm:text-[28px] font-semibold tracking-tight text-ink leading-tight">
            Upload History
          </h1>
          <p className="mt-1 text-sm text-steel">
            <span className="font-mono">{data?.total ?? 0}</span> recordings found
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 flex-wrap rounded-lg border border-border bg-card p-4">
        <Select
          value={statusFilter}
          onValueChange={(v) => {
            if (v) {
              setStatusFilter(v);
              setPage(1);
            }
          }}
        >
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
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setPage(1);
            }}
            className="h-9 rounded-lg border border-input bg-background px-3 text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-steel">To:</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              setPage(1);
            }}
            className="h-9 rounded-lg border border-input bg-background px-3 text-sm"
          />
        </div>
      </div>

      {/* Recordings Table */}
      <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mic className="h-4 w-4" />
            All Uploads
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-5 flex-[3]" />
                  <Skeleton className="h-5 flex-[2]" />
                  <Skeleton className="h-5 flex-[2]" />
                  <Skeleton className="h-5 w-16 hidden sm:block" />
                  <Skeleton className="h-5 w-20 hidden sm:block" />
                  <Skeleton className="h-6 w-24 rounded-full" />
                </div>
              ))}
            </div>
          ) : (
            <>
              <div className="overflow-x-auto -mx-6 sm:mx-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">File</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Recorded</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Uploaded</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Format</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Size</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Status</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recordings.map((rec: Recording) => (
                    <TableRow key={rec.id}>
                      <TableCell className="font-medium">
                        {rec.file_url.split("/").pop() || rec.file_url}
                      </TableCell>
                      <TableCell className="text-steel font-mono text-sm">
                        {rec.recorded_at ? formatDate(rec.recorded_at) : "\u2014"}
                      </TableCell>
                      <TableCell className="text-steel font-mono text-sm">
                        {formatDate(rec.uploaded_at)}
                      </TableCell>
                      <TableCell className="text-steel font-mono text-sm">{rec.format}</TableCell>
                      <TableCell className="text-steel font-mono text-sm">
                        {rec.file_size
                          ? `${(rec.file_size / 1024 / 1024).toFixed(1)} MB`
                          : "\u2014"}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={rec.status} />
                      </TableCell>
                      <TableCell className="text-right">
                        <PipelineActionButtons
                          recordingId={rec.id}
                          status={rec.status}
                          pipelineState={rec.pipeline_state ?? undefined}
                          onAction={() => queryClient.invalidateQueries({ queryKey: ["operations-recordings"] })}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                  {recordings.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} className="py-12">
                        <div className="flex flex-col items-center justify-center text-center">
                          <Inbox className="h-10 w-10 text-stone/40 mb-3" />
                          <p className="text-sm font-medium text-steel">No recordings found</p>
                          <p className="text-xs text-stone mt-1">Try adjusting your filters or date range</p>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-4">
                  <p className="text-sm text-steel font-mono">
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
