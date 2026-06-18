"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { Store, Salesperson, SalespersonPerformance } from "@samaa/shared";
import { KPICard } from "@/components/kpi-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { KPICardsSkeleton, ChartsSkeleton, TableSkeleton } from "@/components/loading-skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { cn } from "@/lib/utils";
import { Users, Mic, TrendingUp, AlertTriangle, Inbox, Target, Trophy } from "lucide-react";
import type { AnalyticsOverviewResponse, AnalyticsSalespeopleResponse } from "@samaa/shared";
import { OutcomeDonut } from "@/components/charts/outcome-donut";
import { ConversionGauge } from "@/components/charts/conversion-gauge";
import { ScoreTrend } from "@/components/charts/score-trend";
import { VolumeTrend } from "@/components/charts/volume-trend";
import { PerformanceBar } from "@/components/charts/performance-bar";
import { SkillRadarCompare } from "@/components/charts/skill-radar-compare";
import { ObjectionTreemap } from "@/components/charts/objection-treemap";
import { SkillHeatmap } from "@/components/charts/skill-heatmap";
import { SalesFunnel } from "@/components/charts/sales-funnel";
import { DateRangeFilter } from "@/components/date-range-filter";
import type { DateRange } from "@/components/date-range-filter";

export default function StoreDashboardPage() {
  const params = useParams();
  const storeId = params.id as string;

  // Date range state (default: last 30 days)
  const [dateRange, setDateRange] = useState<DateRange>(() => {
    const now = new Date();
    const to = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
    const from = new Date(now);
    from.setDate(from.getDate() - 30);
    from.setHours(0, 0, 0, 0);
    return { from, to };
  });

  const { data: store, isLoading: storeLoading } = useQuery({
    queryKey: ["store", storeId],
    queryFn: () => api.get<Store>(`/stores/${storeId}`),
    enabled: !!storeId,
  });

  const { data: salespeople } = useQuery({
    queryKey: ["salespeople", "store", storeId],
    queryFn: () => api.get<Salesperson[]>(`/salespeople?store_id=${storeId}`),
    enabled: !!storeId,
  });

  // Fetch performance for each salesperson
  const performanceQueries = useQuery({
    queryKey: ["store-performances", storeId, salespeople?.map((s) => s.id)],
    queryFn: async () => {
      if (!salespeople?.length) return new Map<string, SalespersonPerformance>();
      const results = await Promise.all(
        salespeople.map(async (sp) => {
          try {
            const perf = await api.get<SalespersonPerformance>(
              `/salespeople/${sp.id}/performance`,
            );
            return [sp.id, perf] as const;
          } catch {
            return [sp.id, null] as const;
          }
        }),
      );
      return new Map(
        results.filter(([, p]) => p !== null) as Iterable<[string, SalespersonPerformance]>,
      );
    },
    enabled: !!salespeople?.length,
  });

  const performances = performanceQueries.data ?? new Map<string, SalespersonPerformance>();

  // Fetch store metrics from dedicated endpoint
  const { data: storeMetrics } = useQuery({
    queryKey: ["store-metrics", storeId],
    queryFn: () => api.get<{ avg_performance_score: number | null; conversion_rate: number | null; top_objection: string | null; total_conversations: number }>(`/stores/${storeId}/metrics`),
    enabled: !!storeId,
  });

  // Compute store-level aggregates
  const perfValues = Array.from(performances.values());
  const avgStoreScore = storeMetrics?.avg_performance_score ?? (
    perfValues.length > 0
      ? perfValues.reduce((sum, p) => sum + (p.avg_overall_score ?? 0), 0) / perfValues.length
      : null
  );
  const totalConversations = storeMetrics?.total_conversations ?? perfValues.reduce((sum, p) => sum + p.total_conversations, 0);

  // Use top objection from store metrics
  const topObjection = storeMetrics?.top_objection || "—";

  // Build ranked salespeople list
  const rankedSalespeople = useMemo(() => {
    if (!salespeople?.length) return [];
    
    return salespeople
      .map((sp) => ({
        ...sp,
        performance: performances.get(sp.id) || null,
      }))
      .filter((sp) => sp.performance?.avg_overall_score != null)
      .sort((a, b) => {
        const scoreA = a.performance?.avg_overall_score ?? 0;
        const scoreB = b.performance?.avg_overall_score ?? 0;
        return scoreB - scoreA; // Highest score first
      })
      .map((sp, index) => ({
        ...sp,
        rank: index + 1,
      }));
  }, [salespeople, performances]);

  // Fetch analytics overview + salespeople comparison with date range
  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ["analytics-overview", "store", storeId, dateRange.from.toISOString(), dateRange.to.toISOString()],
    queryFn: () =>
      api.get<AnalyticsOverviewResponse>(
        `/analytics/overview?store_id=${storeId}` +
        `&date_from=${dateRange.from.toISOString().split("T")[0]}` +
        `&date_to=${dateRange.to.toISOString().split("T")[0]}`
      ),
    enabled: !!storeId,
  });
  const { data: salespeopleComparison } = useQuery({
    queryKey: ["analytics-salespeople", "store", storeId, dateRange.from.toISOString(), dateRange.to.toISOString()],
    queryFn: () =>
      api.get<AnalyticsSalespeopleResponse>(
        `/analytics/salespeople-comparison?store_id=${storeId}` +
        `&date_from=${dateRange.from.toISOString().split("T")[0]}` +
        `&date_to=${dateRange.to.toISOString().split("T")[0]}`
      ),
    enabled: !!storeId,
  });

  return (
    <div className="space-y-4 sm:space-y-6 lg:space-y-8 px-4 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
      {/* Breadcrumbs */}
      {storeLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-4 w-32" />
        </div>
      ) : (
      <Breadcrumbs
        items={[
          { label: store?.name || "Store" },
        ]}
      />
      )}

      {/* Store Header */}
      {storeLoading ? (
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 border-b border-border pb-4 sm:pb-6">
          <div className="space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32" />
          </div>
          <Skeleton className="h-10 w-48" />
        </div>
      ) : (
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 border-b border-border pb-4 sm:pb-6">
        <div>
          <h1 className="text-[22px] sm:text-[28px] font-semibold tracking-tight text-ink leading-tight">{store?.name || "Store"}</h1>
          <p className="mt-1 text-sm text-steel">{store?.location || ""}</p>
        </div>
        <DateRangeFilter value={dateRange} onChange={setDateRange} />
      </div>
      )}

      {/* KPI Cards */}
      {storeLoading ? (
        <KPICardsSkeleton count={4} />
      ) : (
      <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Performance Score"
          value={avgStoreScore != null ? avgStoreScore.toFixed(1) : "—"}
          icon={TrendingUp}
          description="Average across salespeople"
        />
        <KPICard
          title="Interactions"
          value={totalConversations}
          icon={Mic}
          description="Total analyzed"
        />
        <KPICard
          title="Salespeople"
          value={salespeople?.length ?? 0}
          icon={Users}
          description="Active in this store"
        />
        <KPICard
          title="Deal Closure Rate"
          value={storeMetrics?.conversion_rate != null ? `${storeMetrics.conversion_rate.toFixed(0)}%` : "—"}
          icon={Target}
          description="Sales success rate"
        />
      </div>
      )}

      {/* Analytics Charts */}
      {analyticsLoading ? (
        <ChartsSkeleton count={6} />
      ) : (
      <div className="space-y-4">
        {/* Row 1: Outcome Donut + Deal Closure Gauge */}
        <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
          <OutcomeDonut data={analytics?.outcome_distribution ?? []} />
          <ConversionGauge
            value={analytics?.conversion_rate ?? null}
            label={`${analytics?.total_conversations ?? 0} conversations`}
          />
        </div>
        
        {/* Sales Funnel */}
        <SalesFunnel data={analytics?.funnel_stages ?? []} title="Sales Pipeline" />

        {/* Row 2: Score Trend + Volume Trend */}
        <div className="grid gap-4 lg:grid-cols-2">
          <ScoreTrend data={analytics?.score_trend ?? []} />
          <VolumeTrend data={analytics?.volume_trend ?? []} />
        </div>

        {/* Row 3: Sales Performance Bar (within-store ranking) */}
        <PerformanceBar data={salespeopleComparison?.salespeople ?? []} />

        {/* Row 4: Skill Radar Comparison + Top Objections Treemap */}
        <div className="grid gap-4 lg:grid-cols-2">
          <SkillRadarCompare data={salespeopleComparison?.salespeople ?? []} />
          <ObjectionTreemap data={analytics?.top_objections ?? []} />
        </div>

        {/* Row 5: Team Skill Heatmap */}
        <SkillHeatmap data={salespeopleComparison?.salespeople ?? []} />
      </div>
      )}

      {/* Salesperson Performance Table with Rankings */}
      <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Trophy className="h-4 w-4 text-brand-green-deep" />
            Salesperson Rankings
          </CardTitle>
        </CardHeader>
        <CardContent>
          {storeLoading ? (
            <TableSkeleton rows={5} columns={7} />
          ) : salespeople && salespeople.length > 0 ? (
            <div className="overflow-x-auto -mx-4 sm:-mx-6 lg:mx-0">
              <div className="min-w-[450px] sm:min-w-[700px]">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel w-16">Rank</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Name</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel hidden sm:table-cell">Role</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel hidden md:table-cell">Shift</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel text-right">Avg Score</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel text-right hidden sm:table-cell">Interactions</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel text-right">Deal Closure</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {salespeople.map((sp) => {
                  const perf = performances.get(sp.id);
                  const rankData = rankedSalespeople.find((r) => r.id === sp.id);
                  const rank = rankData?.rank;
                  
                  return (
                    <TableRow 
                      key={sp.id} 
                      className="group cursor-pointer hover:bg-accent/50 transition-colors"
                      onClick={() => window.location.href = `/salesperson/${sp.id}`}
                    >
                      <TableCell>
                        {rank ? (
                          <div
                            className={cn(
                              "flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold",
                              rank === 1 && "bg-brand-green text-white",
                              rank === 2 && "bg-slate-400 text-white",
                              rank === 3 && "bg-amber-600 text-white",
                              rank > 3 && "bg-muted text-steel",
                            )}
                          >
                            {rank}
                          </div>
                        ) : (
                          <span className="text-stone text-sm">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Link
                          href={`/salesperson/${sp.id}`}
                          className="font-medium text-primary hover:underline"
                        >
                          {sp.name}
                        </Link>
                      </TableCell>
                      <TableCell className="text-steel hidden sm:table-cell">{sp.role || "—"}</TableCell>
                      <TableCell className="text-steel hidden md:table-cell">{sp.shift || "—"}</TableCell>
                      <TableCell className="text-right">
                        {perf?.avg_overall_score != null ? (
                          <Badge
                            variant="outline"
                            className={cn(
                              "font-mono",
                              perf.avg_overall_score >= 80
                                ? "border-brand-green/30 text-brand-green-deep bg-brand-green-soft"
                                : perf.avg_overall_score >= 60
                                  ? "border-brand-warn/30 text-amber-700 bg-amber-50"
                                  : "border-brand-error/20 text-destructive bg-destructive/10"
                            )}
                          >
                            {perf.avg_overall_score.toFixed(0)}
                          </Badge>
                        ) : (
                          <span className="text-steel font-mono text-sm">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm hidden sm:table-cell">
                        {perf?.total_conversations ?? 0}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {perf?.conversion_rate != null ? (
                          <span className={cn(
                            "font-medium",
                            perf.conversion_rate >= 50
                              ? "text-brand-green-deep"
                              : perf.conversion_rate >= 30
                                ? "text-amber-700"
                                : "text-steel"
                          )}>
                            {perf.conversion_rate.toFixed(0)}%
                          </span>
                        ) : (
                          <span className="text-steel">—</span>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Inbox className="h-10 w-10 text-stone/40 mb-3" />
              <p className="text-sm font-medium text-steel">No salespeople in this store</p>
              <p className="text-xs text-stone mt-1">Add team members to start tracking performance.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
