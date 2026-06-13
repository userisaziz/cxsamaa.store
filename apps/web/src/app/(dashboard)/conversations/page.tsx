"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api-client";
import type { ConversationListItem } from "@samaa/shared";
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
import { MessageSquare, ChevronLeft, ChevronRight, RefreshCw, Eye, Inbox } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const OUTCOMES = [
  { value: "ALL", label: "All Outcomes" },
  { value: "SALE_MADE", label: "Sale Made" },
  { value: "LOST", label: "Lost" },
  { value: "FOLLOW_UP", label: "Follow Up" },
  { value: "NO_PURCHASE", label: "No Purchase" },
];

function formatDuration(seconds: number | null): string {
  if (!seconds) return "—";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatTimeRange(start: number, end: number): string {
  const format = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };
  return `${format(start)} – ${format(end)}`;
}

function OutcomeBadge({ outcome }: { outcome: string | null }) {
  if (!outcome) return <span className="text-xs text-muted-foreground">—</span>;

  const colorMap: Record<string, string> = {
    SALE_MADE: "bg-brand-green-soft text-brand-green-deep",
    LOST: "bg-destructive/10 text-destructive",
    FOLLOW_UP: "bg-brand-tag/10 text-brand-tag",
    NO_PURCHASE: "bg-secondary text-steel",
  };

  return (
    <span className={cn("inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium", colorMap[outcome] || "bg-secondary text-steel")}>
      {outcome.replace("_", " ")}
    </span>
  );
}

function TableSkeleton() {
  return (
    <div className="space-y-3 py-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-2">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-4 w-32" />
          <div className="flex-1" />
          <Skeleton className="h-8 w-16 rounded-lg" />
        </div>
      ))}
    </div>
  );
}

export default function ConversationsPage() {
  const searchParams = useSearchParams();
  const initialSalespersonFilter = searchParams.get("salesperson_id") || "";

  const [outcomeFilter, setOutcomeFilter] = useState("ALL");
  const [salespersonFilter] = useState(initialSalespersonFilter);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const queryParams = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (outcomeFilter !== "ALL") {
    queryParams.set("outcome", outcomeFilter);
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

  const { data, isLoading } = useQuery({
    queryKey: ["conversations", outcomeFilter, page, dateFrom, dateTo],
    queryFn: () =>
      api.get<{ items: ConversationListItem[]; total: number; page: number; total_pages: number }>(
        `/conversations?${queryParams.toString()}`,
      ),
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      // Auto-refresh if any conversation's parent recording is still processing
      // (simplified — in practice you'd track recording status separately)
      return false;
    },
  });

  const conversations = data?.items ?? [];
  const totalPages = data?.total_pages ?? 1;
  const total = data?.total ?? 0;

  return (
    <div className="space-y-6 lg:space-y-8 p-4 sm:p-6 lg:p-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4 sm:pb-6">
        <div>
          <h1 className="text-[22px] sm:text-[28px] font-semibold tracking-tight text-ink leading-tight">Conversations</h1>
          <p className="mt-1 text-sm text-steel">
            <span className="font-mono">{total}</span> total customer interactions
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Filter Bar */}
      <Card className="shadow-none border-border">
        <CardContent className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 flex-wrap py-4">
          <Select value={outcomeFilter} onValueChange={(v) => v && setOutcomeFilter(v)}>
            <SelectTrigger className="w-full sm:w-[180px]">
              <SelectValue placeholder="Filter by outcome" />
            </SelectTrigger>
            <SelectContent>
              {OUTCOMES.map((s) => (
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

      {/* Conversations Table */}
      <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-steel" />
            Customer Interactions
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton />
          ) : conversations.length > 0 ? (
            <>
              <div className="overflow-x-auto -mx-6 sm:mx-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Recorded</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Time Range</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Duration</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Segments</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Intent</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Outcome</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Score</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Summary</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {conversations.map((conv) => {
                    const recordingLink = `/recordings/${conv.recording_id}?conv=${conv.id}`;
                    return (
                      <TableRow 
                        key={conv.id} 
                        className="group cursor-pointer hover:bg-accent/50 transition-colors"
                        onClick={() => {
                          window.location.href = recordingLink;
                        }}
                      >
                        <TableCell className="text-steel font-mono text-[13px]">
                          {formatDateTime(conv.recorded_at)}
                        </TableCell>
                        <TableCell className="font-mono text-[13px] text-charcoal">
                          {formatTimeRange(conv.start_time, conv.end_time)}
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {formatDuration(conv.duration_seconds)}
                        </TableCell>
                        <TableCell className="text-steel font-mono text-sm">
                          {conv.segment_count}
                        </TableCell>
                        <TableCell className="text-ink text-sm max-w-[200px] truncate">
                          {conv.intent || "—"}
                        </TableCell>
                        <TableCell>
                          <OutcomeBadge outcome={conv.outcome} />
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {conv.confidence ? `${conv.confidence}%` : "—"}
                        </TableCell>
                        <TableCell className="text-steel text-sm max-w-[240px] truncate">
                          {conv.summary || "—"}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm" className="opacity-70 group-hover:opacity-100 transition-opacity">
                            <Eye className="mr-1 h-4 w-4" />
                            View
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
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
              <p className="text-sm font-medium text-steel">No conversations found</p>
              <p className="text-xs text-stone mt-1">Try adjusting your filters or upload new audio files.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
