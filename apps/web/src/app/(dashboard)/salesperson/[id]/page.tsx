"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type {
  Salesperson,
  SalespersonPerformance,
  Recording,
  Store,
  AnalyticsOverviewResponse,
} from "@samaa/shared";
import { KPICard } from "@/components/kpi-card";
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
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Breadcrumbs } from "@/components/breadcrumbs";
import {
  ArrowLeft,
  Users,
  MessageSquare,
  TrendingUp,
  Award,
  Target,
  BarChart3,
  Eye,
  Inbox,
} from "lucide-react";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from "recharts";
import { ConversionGauge } from "@/components/charts/conversion-gauge";
import { ScoreTrend } from "@/components/charts/score-trend";
import { DateRangeFilter } from "@/components/date-range-filter";
import type { DateRange } from "@/components/date-range-filter";

const SKILL_LABELS: Record<string, string> = {
  avg_greeting_score: "Greeting",
  avg_discovery_score: "Discovery",
  avg_product_knowledge_score: "Product Knowledge",
  avg_objection_handling_score: "Objection Handling",
  avg_closing_score: "Closing",
};

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

function getScoreColor(score: number | null): string {
  if (score == null) return "text-steel";
  if (score >= 80) return "text-brand-green-deep";
  if (score >= 60) return "text-amber-700";
  return "text-destructive";
}

function getScoreBg(score: number | null): string {
  if (score == null) return "bg-muted";
  if (score >= 80) return "bg-brand-green";
  if (score >= 60) return "bg-brand-warn";
  return "bg-brand-error";
}

function getScoreBadgeClass(score: number | null | undefined): string {
  if (score == null) return "border-border text-steel bg-muted";
  if (score >= 80) return "border-brand-green/30 text-brand-green-deep bg-brand-green-soft";
  if (score >= 60) return "border-brand-warn/30 text-amber-700 bg-amber-50";
  return "border-brand-error/20 text-destructive bg-destructive/10";
}

function getDateRange(days: number): DateRange {
  const now = new Date();
  const to = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
  const from = new Date(now);
  from.setDate(from.getDate() - days);
  from.setHours(0, 0, 0, 0);
  return { from, to };
}

export default function SalespersonDetailPage() {
  const params = useParams();
  const salespersonId = params.id as string;

  // Date range state (default: last 30 days)
  const [dateRange, setDateRange] = useState<DateRange>(() => getDateRange(30));

  // Fetch salesperson profile
  const { data: salesperson } = useQuery({
    queryKey: ["salesperson", salespersonId],
    queryFn: () => api.get<Salesperson>(`/salespeople/${salespersonId}`),
    enabled: !!salespersonId,
  });

  // Fetch performance data
  const { data: performance } = useQuery({
    queryKey: ["salesperson-performance", salespersonId],
    queryFn: () =>
      api.get<SalespersonPerformance>(
        `/salespeople/${salespersonId}/performance`,
      ),
    enabled: !!salespersonId,
  });

  // Fetch recent recordings
  const { data: recordingsData } = useQuery({
    queryKey: ["salesperson-recordings", salespersonId],
    queryFn: () =>
      api.get<{ items: Recording[]; total: number }>(
        `/recordings?salesperson_id=${salespersonId}&page_size=10`,
      ),
    enabled: !!salespersonId,
  });

  // Fetch store info for breadcrumb
  const { data: store } = useQuery({
    queryKey: ["store-for-salesperson", salesperson?.store_id],
    queryFn: () => api.get<Store>(`/stores/${salesperson?.store_id}`),
    enabled: !!salesperson?.store_id,
  });

  // Fetch salesperson analytics with date range
  const { data: analytics } = useQuery({
    queryKey: ["analytics-overview", "salesperson", salespersonId, dateRange.from.toISOString(), dateRange.to.toISOString()],
    queryFn: () =>
      api.get<AnalyticsOverviewResponse>(
        `/analytics/overview?salesperson_id=${salespersonId}` +
        `&date_from=${dateRange.from.toISOString().split("T")[0]}` +
        `&date_to=${dateRange.to.toISOString().split("T")[0]}`
      ),
    enabled: !!salespersonId,
  });

  const recordings = recordingsData?.items ?? [];

  // Build radar chart data from performance scores
  const radarData = performance
    ? Object.entries(SKILL_LABELS).map(([key, label]) => ({
        skill: label,
        score: performance[key as keyof SalespersonPerformance] as number | null ?? 0,
      }))
    : [];

  const overallScore = performance?.avg_overall_score;
  const conversionRate = performance?.conversion_rate;

  return (
    <div className="space-y-6 lg:space-y-8 p-4 sm:p-6 lg:p-8">
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          { label: store?.name || "Store", href: store ? `/store/${store.id}` : undefined },
          { label: salesperson?.name || "Salesperson" },
        ]}
      />

      {/* Back button + Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 flex-1">
          <Link href={store ? `/store/${store.id}` : "/salespeople"}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-1 h-4 w-4" />
              Back
            </Button>
          </Link>
          <div className="flex-1 border-b border-border pb-4 sm:pb-6">
            <h1 className="text-[22px] sm:text-[28px] font-semibold tracking-tight text-ink leading-tight">
              {salesperson?.name || "Salesperson"}
            </h1>
            <p className="mt-1 text-sm text-steel">
              {[salesperson?.role, salesperson?.shift, salesperson?.email]
                .filter(Boolean)
                .join(" · ") || "Sales team member"}
            </p>
          </div>
        </div>
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <DateRangeFilter value={dateRange} onChange={setDateRange} />
          {overallScore != null && (
            <Badge
              variant="outline"
              className={`text-lg px-4 py-2 font-bold font-mono ${getScoreBadgeClass(overallScore)}`}
            >
              {overallScore.toFixed(0)} / 100
            </Badge>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Total Conversations"
          value={performance?.total_conversations ?? 0}
          icon={MessageSquare}
          description={performance?.total_conversations ? "Analyzed interactions" : "No conversations yet"}
        />
        <KPICard
          title="Avg Overall Score"
          value={overallScore != null ? overallScore.toFixed(1) : "—"}
          icon={Award}
          description={overallScore != null ? "Across all skills" : "No scores available"}
        />
        <KPICard
          title="Conversion Rate"
          value={conversionRate != null ? `${conversionRate.toFixed(0)}%` : "—"}
          icon={Target}
          description={conversionRate != null ? "Sales conversion" : "No data yet"}
        />
        <KPICard
          title="Interactions"
          value={recordingsData?.total ?? 0}
          icon={BarChart3}
          description={recordingsData?.total ? "Total uploads" : "No recordings uploaded"}
        />
      </div>

      {/* Skill Scores + Radar Chart */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Skill Breakdown */}
        <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Award className="h-4 w-4 text-steel" />
              Skill Scores
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!performance ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Inbox className="h-10 w-10 text-stone/40 mb-3" />
                <p className="text-sm font-medium text-steel">
                  Performance data will appear once conversations are analyzed.
                </p>
              </div>
            ) : performance.total_conversations === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Inbox className="h-10 w-10 text-stone/40 mb-3" />
                <p className="text-sm font-medium text-steel">
                  No conversations found for this salesperson
                </p>
                <p className="text-xs text-stone mt-2">
                  Upload recordings to start tracking performance.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {Object.entries(SKILL_LABELS).map(([key, label]) => {
                  const score = performance[
                    key as keyof SalespersonPerformance
                  ] as number | null;
                  return (
                    <div key={key} className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-charcoal">{label}</span>
                        <span className={`text-sm font-semibold font-mono w-8 text-right ${getScoreColor(score)}`}>
                          {score != null ? score.toFixed(0) : "—"}
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${getScoreBg(score)}`}
                          style={{ width: `${score ?? 0}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
                <Separator />
                <div className="flex items-center justify-between pt-1">
                  <span className="text-sm font-medium text-ink">Overall</span>
                  <Badge variant="outline" className={`font-mono font-semibold ${getScoreBadgeClass(overallScore)}`}>
                    {overallScore != null ? overallScore.toFixed(1) : "—"}
                  </Badge>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Radar Chart */}
        <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-steel" />
              Skill Radar
            </CardTitle>
          </CardHeader>
          <CardContent>
            {radarData.some((d) => d.score > 0) ? (
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData}>
                    <PolarGrid className="stroke-muted" />
                    <PolarAngleAxis
                      dataKey="skill"
                      className="text-xs fill-muted-foreground"
                    />
                    <PolarRadiusAxis
                      angle={90}
                      domain={[0, 100]}
                      className="text-xs fill-muted-foreground"
                    />
                    <Radar
                      name="Score"
                      dataKey="score"
                      stroke="hsl(var(--primary))"
                      fill="hsl(var(--primary))"
                      fillOpacity={0.2}
                      strokeWidth={2}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-[280px] flex flex-col items-center justify-center text-center">
                <Inbox className="h-10 w-10 text-stone/40 mb-3" />
                <p className="text-sm text-steel">Skill radar will render when analysis data is available</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Conversion Gauge + Score Trend */}
      <div className="grid gap-6 lg:grid-cols-2">
        <ConversionGauge
          value={conversionRate ?? null}
          title="Conversion Rate"
          label={performance?.total_conversations ? `${performance.total_conversations} conversations` : undefined}
        />
        <ScoreTrend
          data={analytics?.score_trend ?? []}
          title="Score Trend"
        />
      </div>

      {/* Recent Interactions */}
      <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-steel" />
              Recent Conversations
            </CardTitle>
            <Link href={`/conversations?salesperson_id=${salespersonId}`}>
              <Button variant="ghost" size="sm">
                View all
                <Eye className="ml-1 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          {recordings.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Date</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Duration</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Format</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Status</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recordings.map((rec) => (
                  <TableRow 
                    key={rec.id} 
                    className="group cursor-pointer hover:bg-accent/50 transition-colors"
                    onClick={() => rec.status === "COMPLETED" && (window.location.href = `/recordings/${rec.id}`)}
                  >
                    <TableCell className="text-steel font-mono text-[13px]">
                      {formatDate(rec.uploaded_at)}
                    </TableCell>
                    <TableCell className="font-mono text-sm">{formatDuration(rec.duration_seconds)}</TableCell>
                    <TableCell className="text-steel">{rec.format}</TableCell>
                    <TableCell>
                      <StatusBadge status={rec.status} />
                    </TableCell>
                    <TableCell className="text-right">
                      {rec.status === "COMPLETED" && (
                        <Link href={`/recordings/${rec.id}`}>
                          <Button variant="ghost" size="sm">
                            <Eye className="mr-1 h-4 w-4" />
                            View
                          </Button>
                        </Link>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Inbox className="h-10 w-10 text-stone/40 mb-3" />
              <p className="text-sm text-steel">No recordings found yet.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
