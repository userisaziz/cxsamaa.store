"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type {
  Salesperson,
  SalespersonPerformance,
  Recording,
  Store,
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
  Mic,
  TrendingUp,
  Award,
  Target,
  BarChart3,
  Eye,
} from "lucide-react";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from "recharts";

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

export default function SalespersonDetailPage() {
  const params = useParams();
  const salespersonId = params.id as string;

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
    <div className="space-y-8 p-8">
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          { label: store?.name || "Store", href: store ? `/store/${store.id}` : undefined },
          { label: salesperson?.name || "Salesperson" },
        ]}
      />

      {/* Back button + Header */}
      <div className="flex items-center gap-4">
        <Link href={store ? `/store/${store.id}` : "/salespeople"}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-[28px] font-semibold tracking-tight text-ink leading-tight">
            {salesperson?.name || "Salesperson"}
          </h1>
          <p className="mt-1 text-sm text-steel">
            {[salesperson?.role, salesperson?.shift, salesperson?.email]
              .filter(Boolean)
              .join(" · ") || "Sales team member"}
          </p>
        </div>
        {overallScore != null && (
          <Badge
            variant="outline"
            className={`text-lg px-4 py-2 font-bold ${
              overallScore >= 80
                ? "border-brand-green/30 text-brand-green-deep bg-brand-green-soft"
                : overallScore >= 60
                ? "border-brand-warn/30 text-amber-700 bg-amber-50"
                : "border-brand-error/20 text-destructive bg-destructive/10"
            }`}
          >
            {overallScore.toFixed(0)} / 100
          </Badge>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Total Conversations"
          value={performance?.total_conversations ?? 0}
          icon={Mic}
          description="Analyzed interactions"
        />
        <KPICard
          title="Avg Overall Score"
          value={overallScore != null ? overallScore.toFixed(1) : "—"}
          icon={Award}
          description="Across all skills"
        />
        <KPICard
          title="Conversion Rate"
          value={conversionRate != null ? `${conversionRate.toFixed(0)}%` : "—"}
          icon={Target}
          description="Sales conversion"
        />
        <KPICard
          title="Recordings"
          value={recordingsData?.total ?? 0}
          icon={BarChart3}
          description="Total uploads"
        />
      </div>

      {/* Skill Scores + Radar Chart */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Skill Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Award className="h-4 w-4" />
              Skill Scores
            </CardTitle>
          </CardHeader>
          <CardContent>
            {performance ? (
              <div className="space-y-3">
                {Object.entries(SKILL_LABELS).map(([key, label]) => {
                  const score = performance[
                    key as keyof SalespersonPerformance
                  ] as number | null;
                  return (
                    <div key={key} className="flex items-center justify-between">
                      <span className="text-sm">{label}</span>
                      <div className="flex items-center gap-3">
                        <div className="w-32 h-2 rounded-full bg-muted overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              score != null && score >= 80
                                ? "bg-brand-green"
                                : score != null && score >= 60
                                ? "bg-brand-warn"
                                : score != null
                                ? "bg-brand-error"
                                : "bg-muted"
                            }`}
                            style={{ width: `${score ?? 0}%` }}
                          />
                        </div>
                        <span className="text-sm font-semibold w-8 text-right">
                          {score != null ? score.toFixed(0) : "—"}
                        </span>
                      </div>
                    </div>
                  );
                })}
                <Separator />
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Overall</span>
                  <span className="text-sm font-bold">
                    {overallScore != null ? overallScore.toFixed(1) : "—"}
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-4">
                Performance data will appear once conversations are analyzed.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Radar Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
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
              <div className="h-[280px] flex items-center justify-center text-muted-foreground text-sm">
                Skill radar will render when analysis data is available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Recordings */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Mic className="h-4 w-4" />
              Recent Recordings
            </CardTitle>
            <Link href={`/recordings?salesperson_id=${salespersonId}`}>
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
                  <TableHead>Date</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Format</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recordings.map((rec) => (
                  <TableRow key={rec.id}>
                    <TableCell className="text-muted-foreground">
                      {formatDate(rec.uploaded_at)}
                    </TableCell>
                    <TableCell>{formatDuration(rec.duration_seconds)}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {rec.format}
                    </TableCell>
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
            <p className="text-sm text-muted-foreground py-8 text-center">
              No recordings found yet.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
