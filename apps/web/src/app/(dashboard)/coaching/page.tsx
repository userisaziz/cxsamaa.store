"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";
import { api } from "@/lib/api-client";
import type { Salesperson, SalespersonPerformance, AnalyticsOverviewResponse } from "@samaa/shared";
import { KPICard } from "@/components/kpi-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { KPICardsSkeleton } from "@/components/loading-skeleton";
import { ScoreTrend } from "@/components/charts/score-trend";
import { ConversionGauge } from "@/components/charts/conversion-gauge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Award,
  TrendingUp,
  Target,
  AlertTriangle,
  Brain,
  Lightbulb,
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

const SKILL_LABELS: Record<string, string> = {
  avg_greeting_score: "Greeting",
  avg_discovery_score: "Discovery",
  avg_product_knowledge_score: "Product Knowledge",
  avg_objection_handling_score: "Objection Handling",
  avg_closing_score: "Closing",
};

const SKILL_TIPS: Record<string, string> = {
  avg_greeting_score:
    "Focus on warm welcomes, introducing yourself and the brand within the first 30 seconds.",
  avg_discovery_score:
    "Ask open-ended questions to understand customer needs before recommending products.",
  avg_product_knowledge_score:
    "Study product features, benefits, and differentiators. Use specific examples in conversations.",
  avg_objection_handling_score:
    "Practice the LAER method: Listen, Acknowledge, Explore, Respond to objections calmly.",
  avg_closing_score:
    "Always summarize next steps, mention promotions, and ask for the sale before ending.",
};

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

function getScoreBadgeClass(score: number | null): string {
  if (score == null) return "border-border text-steel bg-muted";
  if (score >= 80) return "border-brand-green/30 text-brand-green-deep bg-brand-green-soft";
  if (score >= 60) return "border-brand-warn/30 text-amber-700 bg-amber-50";
  return "border-destructive/20 text-destructive bg-destructive/10";
}

export default function CoachingPage() {
  const { user } = useAuthStore();
  const [selectedSalespersonId, setSelectedSalespersonId] = useState<string>("");

  const isManager = user?.role === "SUPER_ADMIN" || user?.role === "BRAND_ADMIN" || user?.role === "STORE_MANAGER";

  // Fetch all salespeople for the selector dropdown
  const { data: salespeople } = useQuery({
    queryKey: ["salespeople-coaching"],
    queryFn: () => api.get<Salesperson[]>("/salespeople"),
    enabled: isManager,
  });

  // Determine which salesperson to show
  const activeSalespersonId = selectedSalespersonId || (salespeople?.[0]?.id ?? "");

  // Fetch performance for the selected salesperson
  const { data: performance, isLoading: performanceLoading } = useQuery({
    queryKey: ["coaching-performance", activeSalespersonId],
    queryFn: () =>
      api.get<SalespersonPerformance>(
        `/salespeople/${activeSalespersonId}/performance`,
      ),
    enabled: !!activeSalespersonId,
  });

  // Get the active salesperson's store_id for analytics
  const activeSalesperson = salespeople?.find((sp) => sp.id === activeSalespersonId);
  const { data: storeAnalytics } = useQuery({
    queryKey: ["coaching-store-analytics", activeSalesperson?.store_id],
    queryFn: () =>
      api.get<AnalyticsOverviewResponse>(
        `/analytics/overview?store_id=${activeSalesperson?.store_id}`,
      ),
    enabled: !!activeSalesperson?.store_id,
  });

  // Fetch salesperson-specific analytics for trend data
  const { data: salespersonAnalytics } = useQuery({
    queryKey: ["coaching-salesperson-analytics", activeSalespersonId],
    queryFn: () =>
      api.get<AnalyticsOverviewResponse>(
        `/analytics/overview?salesperson_id=${activeSalespersonId}`,
      ),
    enabled: !!activeSalespersonId,
  });

  // Build radar chart data
  const radarData = performance
    ? Object.entries(SKILL_LABELS).map(([key, label]) => ({
        skill: label,
        score: (performance[key as keyof SalespersonPerformance] as number | null) ?? 0,
      }))
    : [];

  // Find weakest skills for improvement areas
  const weakestSkills = performance
    ? Object.entries(SKILL_LABELS)
        .map(([key, label]) => ({
          key,
          label,
          score: (performance[key as keyof SalespersonPerformance] as number | null) ?? 0,
        }))
        .filter((s) => s.score > 0)
        .sort((a, b) => a.score - b.score)
        .slice(0, 3)
    : [];

  // Generate recommendations based on weakest skills
  const recommendations = weakestSkills.map((s) => ({
    skill: s.label,
    score: s.score,
    tip: SKILL_TIPS[s.key] || "",
  }));

  return (
    <div className="space-y-4 sm:space-y-6 lg:space-y-8 px-4 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
      {/* Page Header */}
      {performanceLoading ? (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4 sm:pb-6">
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-48" />
          </div>
          <Skeleton className="h-10 w-full sm:w-[220px]" />
        </div>
      ) : (
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4 sm:pb-6">
        <div>
          <h1 className="text-[22px] sm:text-[28px] font-semibold tracking-tight text-ink leading-tight">Coaching Dashboard</h1>
          <p className="mt-1 text-sm text-steel">
            AI-powered performance insights and recommendations
          </p>
        </div>

        {/* Salesperson Selector (for managers) */}
        {isManager && salespeople && salespeople.length > 0 && (
          <Select
            value={selectedSalespersonId || salespeople[0]?.id || ""}
            onValueChange={(v) => v && setSelectedSalespersonId(v)}
          >
            <SelectTrigger className="w-full sm:w-[220px]">
              <SelectValue placeholder="Select salesperson" />
            </SelectTrigger>
            <SelectContent>
              {salespeople.map((sp) => (
                <SelectItem key={sp.id} value={sp.id}>
                  {sp.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
      )}

      <Tabs defaultValue="overview">
        {performanceLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-64" />
          </div>
        ) : (
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="30d">30 Days</TabsTrigger>
          <TabsTrigger value="60d">60 Days</TabsTrigger>
          <TabsTrigger value="90d">90 Days</TabsTrigger>
        </TabsList>
        )}

        <TabsContent value="overview" className="space-y-6 mt-4">
          {/* KPI Summary */}
          {performanceLoading ? (
            <KPICardsSkeleton count={3} />
          ) : (
          <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            <KPICard
              title="Total Interactions"
              value={performance?.total_conversations ?? 0}
              icon={Target}
              description="Analyzed interactions"
            />
            <KPICard
              title="Overall Score"
              value={
                performance?.avg_overall_score != null
                  ? performance.avg_overall_score.toFixed(1)
                  : "—"
              }
              icon={Award}
              description="Across all skills"
            />
            <KPICard
              title="Deal Closure Rate"
              value={
                performance?.conversion_rate != null
                  ? `${performance.conversion_rate.toFixed(0)}%`
                  : "—"
              }
              icon={TrendingUp}
              description="Sales success rate"
            />
          </div>
          )}

          {/* Skill Scores + Radar Chart */}
          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Award className="h-4 w-4 text-steel" />
                  Skill Scores
                </CardTitle>
              </CardHeader>
              <CardContent>
                {performanceLoading ? (
                  <div className="space-y-4">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div key={i} className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <Skeleton className="h-4 w-24" />
                          <Skeleton className="h-4 w-8" />
                        </div>
                        <Skeleton className="h-2 w-full rounded-full" />
                      </div>
                    ))}
                  </div>
                ) : performance ? (
                  <div className="space-y-4">
                    {Object.entries(SKILL_LABELS).map(([key, label]) => {
                      const score = performance[
                        key as keyof SalespersonPerformance
                      ] as number | null;
                      return (
                        <div key={key} className="space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-charcoal">{label}</span>
                            <span
                              className={`text-sm font-semibold font-mono w-8 text-right ${getScoreColor(score)}`}
                            >
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
                      <Badge variant="outline" className={`font-mono font-semibold ${getScoreBadgeClass(performance.avg_overall_score)}`}>
                        {performance.avg_overall_score != null
                          ? performance.avg_overall_score.toFixed(1)
                          : "—"}
                      </Badge>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <Inbox className="h-10 w-10 text-stone/40 mb-3" />
                    <p className="text-sm text-steel">
                      Select a salesperson to view their performance data.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Radar Chart */}
            <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-4 w-4 text-steel" />
                  Skill Radar
                </CardTitle>
              </CardHeader>
              <CardContent>
                {performanceLoading ? (
                  <div className="h-[280px] flex items-center justify-center">
                    <Skeleton className="h-[240px] w-[240px] rounded-full" />
                  </div>
                ) : radarData.some((d) => d.score > 0) ? (
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

          {/* Improvement Areas */}
          {performanceLoading ? (
            <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
              <CardHeader>
                <Skeleton className="h-5 w-40" />
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-start gap-3 rounded-lg border border-border p-4">
                      <Skeleton className="h-7 w-7 rounded-full" />
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center justify-between">
                          <Skeleton className="h-4 w-32" />
                          <Skeleton className="h-5 w-12 rounded-full" />
                        </div>
                        <Skeleton className="h-3 w-full" />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : weakestSkills.length > 0 && (
            <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-brand-warn" />
                  Improvement Areas
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {weakestSkills.map((s, i) => (
                    <div
                      key={s.key}
                      className="flex items-start gap-3 rounded-lg border border-border p-4"
                    >
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-secondary text-[11px] font-semibold text-ink">
                        {i + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-sm font-medium text-ink">{s.label}</p>
                          <Badge variant="outline" className={`shrink-0 font-mono ${getScoreBadgeClass(s.score)}`}>
                            {s.score.toFixed(0)}
                          </Badge>
                        </div>
                        <p className="text-xs text-steel mt-1 leading-relaxed">
                          {SKILL_TIPS[s.key]}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Recommendations */}
          {performanceLoading ? (
            <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
              <CardHeader>
                <Skeleton className="h-5 w-36" />
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-start gap-3 rounded-lg border border-brand-tag/15 bg-brand-tag/[0.03] p-4">
                      <Skeleton className="h-7 w-7 rounded-lg" />
                      <div className="flex-1 space-y-2">
                        <Skeleton className="h-4 w-48" />
                        <Skeleton className="h-3 w-full" />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : recommendations.length > 0 && (
            <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="h-4 w-4 text-brand-tag" />
                  Recommendations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {recommendations.map((rec, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 rounded-lg border border-brand-tag/15 bg-brand-tag/[0.03] p-4"
                    >
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-tag/10">
                        <Lightbulb className="h-3.5 w-3.5 text-brand-tag" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-ink">
                          Improve {rec.skill} <span className="font-mono text-steel font-normal">(currently {rec.score.toFixed(0)})</span>
                        </p>
                        <p className="text-xs text-steel mt-1 leading-relaxed">{rec.tip}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Historical Trend + Deal Closure Gauge */}
          {performanceLoading ? (
            <div className="grid gap-6 lg:grid-cols-2">
              <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
                <CardHeader>
                  <Skeleton className="h-5 w-32" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-[280px] w-full" />
                </CardContent>
              </Card>
              <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
                <CardHeader>
                  <Skeleton className="h-5 w-40" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-[280px] w-full" />
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="grid gap-6 lg:grid-cols-2">
              <ScoreTrend
                data={salespersonAnalytics?.score_trend ?? storeAnalytics?.score_trend ?? []}
                title="Score Trend"
              />
              <ConversionGauge
                value={performance?.conversion_rate != null ? performance.conversion_rate / 100 : null}
                title="Deal Closure Rate"
                label={performance?.total_conversations ? `${performance.total_conversations} conversations` : undefined}
              />
            </div>
          )}
        </TabsContent>

        <TabsContent value="30d" className="mt-4">
          <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
            <CardContent className="py-12 text-center">
              <Inbox className="h-10 w-10 text-stone/40 mx-auto mb-3" />
              <p className="text-sm font-medium text-steel">30-day detailed view</p>
              <p className="text-xs text-stone mt-1">Conversation-level breakdown coming soon.</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="60d" className="mt-4">
          <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
            <CardContent className="py-12 text-center">
              <Inbox className="h-10 w-10 text-stone/40 mx-auto mb-3" />
              <p className="text-sm font-medium text-steel">60-day trend analysis</p>
              <p className="text-xs text-stone mt-1">Week-over-week comparisons coming soon.</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="90d" className="mt-4">
          <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
            <CardContent className="py-12 text-center">
              <Inbox className="h-10 w-10 text-stone/40 mx-auto mb-3" />
              <p className="text-sm font-medium text-steel">90-day quarterly review</p>
              <p className="text-xs text-stone mt-1">Comprehensive performance summary coming soon.</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
