"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { Store, Salesperson, SalespersonPerformance } from "@samaa/shared";
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
import { Breadcrumbs } from "@/components/breadcrumbs";
import { Users, Mic, TrendingUp, AlertTriangle } from "lucide-react";

export default function StoreDashboardPage() {
  const params = useParams();
  const storeId = params.id as string;

  const { data: store } = useQuery({
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

  // Compute store-level aggregates
  const perfValues = Array.from(performances.values());
  const avgStoreScore =
    perfValues.length > 0
      ? perfValues.reduce((sum, p) => sum + (p.avg_overall_score ?? 0), 0) / perfValues.length
      : null;
  const totalConversations = perfValues.reduce((sum, p) => sum + p.total_conversations, 0);

  // Find top objection from all salespeople (placeholder until aggregated endpoint exists)
  const topObjection = "—";

  return (
    <div className="space-y-8 p-8">
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          { label: store?.name || "Store" },
        ]}
      />

      {/* Store Header */}
      <div>
        <h1 className="text-[28px] font-semibold tracking-tight text-ink leading-tight">{store?.name || "Store"}</h1>
        <p className="mt-1 text-sm text-steel">{store?.location || ""}</p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Performance Score"
          value={avgStoreScore != null ? avgStoreScore.toFixed(1) : "—"}
          icon={TrendingUp}
          description="Average across salespeople"
        />
        <KPICard
          title="Conversations"
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
          title="Top Objection"
          value={topObjection}
          icon={AlertTriangle}
          description="Most common"
        />
      </div>

      {/* Salesperson Performance Table */}
      <Card>
        <CardHeader>
          <CardTitle>Salesperson Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Shift</TableHead>
                <TableHead className="text-right">Avg Score</TableHead>
                <TableHead className="text-right">Conversations</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {salespeople?.map((sp) => {
                const perf = performances.get(sp.id);
                return (
                  <TableRow key={sp.id}>
                    <TableCell>
                      <Link
                        href={`/salesperson/${sp.id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {sp.name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-steel">{sp.role || "—"}</TableCell>
                    <TableCell className="text-steel">{sp.shift || "—"}</TableCell>
                    <TableCell className="text-right">
                      {perf?.avg_overall_score != null ? (
                        <Badge
                          variant="outline"
                          className={
                            perf.avg_overall_score >= 80
                              ? "border-brand-green/30 text-brand-green-deep bg-brand-green-soft"
                              : perf.avg_overall_score >= 60
                              ? "border-brand-warn/30 text-amber-700 bg-amber-50"
                              : "border-brand-error/20 text-destructive bg-destructive/10"
                          }
                        >
                          {perf.avg_overall_score.toFixed(0)}
                        </Badge>
                      ) : (
                        <span className="text-steel">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {perf?.total_conversations ?? 0}
                    </TableCell>
                  </TableRow>
                );
              }) ?? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-steel py-12">
                    No salespeople found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
