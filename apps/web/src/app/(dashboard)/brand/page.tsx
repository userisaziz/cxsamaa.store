"use client";

import { useQuery } from "@tanstack/react-query";
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
import { Store as StoreIcon, Users, Mic, TrendingUp, AlertTriangle } from "lucide-react";
import Link from "next/link";

export default function BrandDashboardPage() {
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

  return (
    <div className="space-y-8 p-8">
      <div>
        <h1 className="text-[28px] font-semibold tracking-tight text-ink leading-tight">Brand Dashboard</h1>
        <p className="mt-1 text-sm text-steel">Overview of your brand performance across all locations</p>
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

      {/* Store Ranking Table */}
      <Card>
        <CardHeader>
          <CardTitle>Store Performance Ranking</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Store</TableHead>
                <TableHead>Location</TableHead>
                <TableHead className="text-right">Salespeople</TableHead>
                <TableHead className="text-right">Avg Score</TableHead>
                <TableHead className="text-right">Conversations</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stores
                ?.map((store: StoreType) => ({
                  store,
                  agg: getStoreAggregates(store.id),
                }))
                .sort((a, b) => (b.agg.avgScore ?? 0) - (a.agg.avgScore ?? 0))
                .map(({ store, agg }) => (
                  <TableRow key={store.id}>
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
                    <TableCell className="text-right">{agg.count}</TableCell>
                    <TableCell className="text-right">
                      {agg.avgScore != null ? (
                        <Badge
                          variant="outline"
                          className={
                            agg.avgScore >= 80
                              ? "border-brand-green/30 text-brand-green-deep bg-brand-green-soft"
                              : agg.avgScore >= 60
                              ? "border-brand-warn/30 text-amber-700 bg-amber-50"
                              : "border-brand-error/20 text-destructive bg-destructive/10"
                          }
                        >
                          {agg.avgScore.toFixed(0)}
                        </Badge>
                      ) : (
                        <span className="text-steel">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">{agg.conversations}</TableCell>
                  </TableRow>
                )) ?? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-steel py-12">
                    No stores found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Coaching Alerts */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-brand-warn" />
            Coaching Alerts
          </CardTitle>
        </CardHeader>
        <CardContent>
          {perfValues.length > 0 ? (
            <div className="space-y-2">
              {perfValues
                .filter((p) => p.avg_overall_score != null && p.avg_overall_score < 60)
                .sort((a, b) => (a.avg_overall_score ?? 100) - (b.avg_overall_score ?? 100))
                .map((p) => (
                  <div
                    key={p.salesperson_id}
                    className="flex items-center justify-between rounded-md border border-brand-error/20 bg-destructive/5 px-4 py-3"
                  >
                    <div>
                      <p className="text-sm font-medium text-ink">{p.name}</p>
                      <p className="text-xs text-steel">
                        Score: {p.avg_overall_score?.toFixed(0)} · {p.total_conversations} conversations
                      </p>
                    </div>
                    <Badge variant="outline" className="border-brand-error/20 text-destructive bg-destructive/10">
                      Needs Attention
                    </Badge>
                  </div>
                ))}
              {perfValues.filter((p) => p.avg_overall_score != null && p.avg_overall_score < 60)
                .length === 0 && (
                <p className="text-sm text-steel">
                  No salespeople currently need urgent coaching. Great job!
                </p>
              )}
            </div>
          ) : (
            <p className="text-sm text-steel">
              Coaching alerts will appear here when AI analysis identifies salespeople who need improvement.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
