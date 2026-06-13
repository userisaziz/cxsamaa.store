"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api-client";
import type { Brand, Store as StoreType, Salesperson, SalespersonPerformance } from "@samaa/shared";
import { KPICard } from "@/components/kpi-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Store as StoreIcon, Users, Mic, TrendingUp, AlertTriangle, Inbox } from "lucide-react";
import Link from "next/link";
import type { AnalyticsOverviewResponse, AnalyticsSalespeopleResponse } from "@samaa/shared";
import { DateRangeFilter } from "@/components/date-range-filter";
import type { DateRange } from "@/components/date-range-filter";
import { OutcomeDonut } from "@/components/charts/outcome-donut";
import { ConversionGauge } from "@/components/charts/conversion-gauge";
import { ScoreTrend } from "@/components/charts/score-trend";
import { VolumeTrend } from "@/components/charts/volume-trend";
import { PerformanceBar } from "@/components/charts/performance-bar";
import { StoreScatter } from "@/components/charts/store-scatter";
import { ObjectionTreemap } from "@/components/charts/objection-treemap";
import { SkillHeatmap } from "@/components/charts/skill-heatmap";

export default function BrandDashboardPage() {
  const [dateRange, setDateRange] = useState<DateRange>(() => {
    const now = new Date();
    const to = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
    const from = new Date(now);
    from.setDate(from.getDate() - 30);
    from.setHours(0, 0, 0, 0);
    return { from, to };
  });
  const { data: stores } = useQuery({
    queryKey: ["stores"],
    queryFn: () => api.get<StoreType[]>("/stores"),
  });

  const { data: salespeople } = useQuery({
    queryKey: ["salespeople-all"],
    queryFn: () => api.get<Salesperson[]>("/salespeople"),
  });

  // Fetch performance for each salesperson to compute aggregates
  const performanceQueries = useQuery({
    queryKey: ["brand-performances", salespeople?.map((s) => s.id)],
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

  // Fetch analytics overview + salespeople comparison
  const brandId = stores?.[0]?.brand_id;
  const { data: analytics } = useQuery({
    queryKey: ["analytics-overview", "brand", brandId, dateRange.from.toISOString(), dateRange.to.toISOString()],
    queryFn: () =>
      api.get<AnalyticsOverviewResponse>(
        `/analytics/overview${brandId ? `?brand_id=${brandId}` +
        `&date_from=${dateRange.from.toISOString().split("T")[0]}` +
        `&date_to=${dateRange.to.toISOString().split("T")[0]}` : ""}`,
      ),
    enabled: !!brandId,
  });
  const { data: salespeopleComparison } = useQuery({
    queryKey: ["analytics-salespeople", "brand", brandId, dateRange.from.toISOString(), dateRange.to.toISOString()],
    queryFn: () =>
      api.get<AnalyticsSalespeopleResponse>(
        `/analytics/salespeople-comparison${brandId ? `?brand_id=${brandId}` +
        `&date_from=${dateRange.from.toISOString().split("T")[0]}` +
        `&date_to=${dateRange.to.toISOString().split("T")[0]}` : ""}`,
      ),
    enabled: !!brandId,
  });

  // Compute brand-level aggregates
  const perfValues = Array.from(performances.values());
  const totalConversations = perfValues.reduce((sum, p) => sum + p.total_conversations, 0);
  const avgBrandScore =
    perfValues.length > 0
      ? perfValues.reduce((sum, p) => sum + (p.avg_overall_score ?? 0), 0) / perfValues.length
      : null;

  // Group salespeople by store for the ranking table
  function getStoreAggregates(storeId: string) {
    const storeSalespeople = salespeople?.filter((sp) => sp.store_id === storeId) ?? [];
    const storePerfs = storeSalespeople
      .map((sp) => performances.get(sp.id))
      .filter((p): p is SalespersonPerformance => p != null);

    const count = storeSalespeople.length;
    const conversations = storePerfs.reduce((sum, p) => sum + p.total_conversations, 0);
    const avgScore =
      storePerfs.length > 0
        ? storePerfs.reduce((sum, p) => sum + (p.avg_overall_score ?? 0), 0) / storePerfs.length
        : null;

    return { count, conversations, avgScore };
  }

  const coachingAlerts = perfValues
    .filter((p) => p.avg_overall_score != null && p.avg_overall_score < 60)
    .sort((a, b) => (a.avg_overall_score ?? 100) - (b.avg_overall_score ?? 100));

  return (
    <div className="space-y-6 lg:space-y-8 p-4 sm:p-6 lg:p-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 border-b border-border pb-4 sm:pb-6">
        <div>
          <h1 className="text-[22px] sm:text-[28px] font-semibold tracking-tight text-ink leading-tight">Brand Dashboard</h1>
          <p className="mt-1 text-sm text-steel">Overview of your brand performance across all locations</p>
        </div>
        <DateRangeFilter value={dateRange} onChange={setDateRange} />
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Total Stores"
          value={stores?.length ?? 0}
          icon={StoreIcon}
          description="Active retail locations"
        />
        <KPICard
          title="Salespeople"
          value={salespeople?.length ?? 0}
          icon={Users}
          description="Across all stores"
        />
        <KPICard
          title="Conversations"
          value={totalConversations}
          icon={Mic}
          description="Total analyzed"
        />
        <KPICard
          title="Avg Score"
          value={avgBrandScore != null ? avgBrandScore.toFixed(1) : "—"}
          icon={TrendingUp}
          description="Brand-wide average"
        />
      </div>

      {/* Analytics Charts */}
      <div className="space-y-4">
        {/* Row 1: Outcome Donut + Conversion Gauge */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <OutcomeDonut data={analytics?.outcome_distribution ?? []} />
          <ConversionGauge
            value={analytics?.conversion_rate ?? null}
            label={`${analytics?.total_conversations ?? 0} conversations`}
          />
        </div>

        {/* Row 2: Score Trend + Volume Trend */}
        <div className="grid gap-4 lg:grid-cols-2">
          <ScoreTrend data={analytics?.score_trend ?? []} />
          <VolumeTrend data={analytics?.volume_trend ?? []} />
        </div>

        {/* Row 3: Sales Performance Bar */}
        <PerformanceBar data={salespeopleComparison?.salespeople ?? []} />

        {/* Row 4: Store Scatter + Objection Treemap */}
        <div className="grid gap-4 lg:grid-cols-2">
          <StoreScatter data={analytics?.store_comparison ?? []} />
          <ObjectionTreemap data={analytics?.top_objections ?? []} />
        </div>

        {/* Row 5: Team Skill Heatmap */}
        <SkillHeatmap data={salespeopleComparison?.salespeople ?? []} />
      </div>

      {/* Store Ranking Table */}
      <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <StoreIcon className="h-4 w-4 text-steel" />
            Store Performance Ranking
          </CardTitle>
        </CardHeader>
        <CardContent>
          {stores && stores.length > 0 ? (
            <div className="overflow-x-auto -mx-6 sm:mx-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Store</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Location</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel text-right">Salespeople</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel text-right">Avg Score</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel text-right">Conversations</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stores
                  .map((store: StoreType) => ({
                    store,
                    agg: getStoreAggregates(store.id),
                  }))
                  .sort((a, b) => (b.agg.avgScore ?? 0) - (a.agg.avgScore ?? 0))
                  .map(({ store, agg }) => (
                    <TableRow 
                      key={store.id} 
                      className="group cursor-pointer hover:bg-accent/50 transition-colors"
                      onClick={() => window.location.href = `/store/${store.id}`}
                    >
                      <TableCell>
                        <Link
                          href={`/store/${store.id}`}
                          className="font-medium text-primary hover:underline"
                        >
                          {store.name}
                        </Link>
                      </TableCell>
                      <TableCell className="text-steel">
                        {store.location || "—"}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">{agg.count}</TableCell>
                      <TableCell className="text-right">
                        {agg.avgScore != null ? (
                          <Badge
                            variant="outline"
                            className={
                              agg.avgScore >= 80
                                ? "border-brand-green/30 text-brand-green-deep bg-brand-green-soft font-mono"
                                : agg.avgScore >= 60
                                ? "border-brand-warn/30 text-amber-700 bg-amber-50 font-mono"
                                : "border-brand-error/20 text-destructive bg-destructive/10 font-mono"
                            }
                          >
                            {agg.avgScore.toFixed(0)}
                          </Badge>
                        ) : (
                          <span className="text-steel font-mono text-sm">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">{agg.conversations}</TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Inbox className="h-10 w-10 text-stone/40 mb-3" />
              <p className="text-sm font-medium text-steel">No stores configured yet</p>
              <p className="text-xs text-stone mt-1">Stores will appear here once they are added to the system.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Coaching Alerts */}
      <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-brand-warn" />
            Coaching Alerts
            {coachingAlerts.length > 0 && (
              <Badge variant="outline" className="ml-1 bg-destructive/10 text-destructive border-destructive/20 text-[11px] font-mono">
                {coachingAlerts.length}
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {perfValues.length > 0 ? (
            <div className="space-y-2">
              {coachingAlerts.length > 0 ? (
                coachingAlerts.map((p) => (
                  <div
                    key={p.salesperson_id}
                    className="flex items-center justify-between rounded-lg border border-destructive/15 bg-destructive/[0.03] px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-destructive/10">
                        <AlertTriangle className="h-3.5 w-3.5 text-destructive" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-ink">{p.name}</p>
                        <p className="text-xs text-steel font-mono">
                          Score: {p.avg_overall_score?.toFixed(0)} &middot; {p.total_conversations} conversations
                        </p>
                      </div>
                    </div>
                    <Badge variant="outline" className="border-destructive/20 text-destructive bg-destructive/5 text-[11px]">
                      Needs Attention
                    </Badge>
                  </div>
                ))
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-green-soft mb-3">
                    <TrendingUp className="h-5 w-5 text-brand-green-deep" />
                  </div>
                  <p className="text-sm font-medium text-ink">All clear</p>
                  <p className="text-xs text-steel mt-1">No salespeople currently need urgent coaching.</p>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Inbox className="h-10 w-10 text-stone/40 mb-3" />
              <p className="text-sm text-steel">
                Coaching alerts will appear here when AI analysis identifies salespeople who need improvement.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
