"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";
import { api } from "@/lib/api-client";
import type { Salesperson, SalespersonPerformance } from "@samaa/shared";
import { KPICard } from "@/components/kpi-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
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
} from "lucide-react";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
} from "recharts";

// Mock trend data (will be replaced with real API data in Sprint 6)
const mockTrendData = [
  { week: "W1", score: 62 },
  { week: "W2", score: 65 },
  { week: "W3", score: 61 },
  { week: "W4", score: 68 },
  { week: "W5", score: 72 },
  { week: "W6", score: 70 },
  { week: "W7", score: 74 },
  { week: "W8", score: 76 },
];

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
  if (score == null) return "text-muted-foreground";
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-amber-600";
  return "text-red-600";
}

function getScoreBg(score: number | null): string {
  if (score == null) return "bg-muted";
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-amber-500";
  return "bg-red-400";
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
  const { data: performance } = useQuery({
    queryKey: ["coaching-performance", activeSalespersonId],
    queryFn: () =>
      api.get<SalespersonPerformance>(
        `/salespeople/${activeSalespersonId}/performance`,
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
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Coaching Dashboard</h1>
          <p className="text-sm text-steel">
            AI-powered performance insights and recommendations
          </p>
        </div>

        {/* Salesperson Selector (for managers) */}
        {isManager && salespeople && salespeople.length > 0 && (
          <Select
            value={selectedSalespersonId || salespeople[0]?.id || ""}
            onValueChange={(v) => v && setSelectedSalespersonId(v)}
          >
            <SelectTrigger className="w-[220px]">
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

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="30d">30 Days</TabsTrigger>
          <TabsTrigger value="60d">60 Days</TabsTrigger>
          <TabsTrigger value="90d">90 Days</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6 mt-4">
          {/* KPI Summary */}
          <div className="grid gap-4 md:grid-cols-3">
            <KPICard
              title="Total Conversations"
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
              title="Conversion Rate"
              value={
                performance?.conversion_rate != null
                  ? `${performance.conversion_rate.toFixed(0)}%`
                  : "—"
              }
              icon={TrendingUp}
              description="Sales conversion"
            />
          </div>

          {/* Skill Scores + Radar Chart */}
          <div className="grid gap-6 lg:grid-cols-2">
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
                                className={`h-full rounded-full transition-all ${getScoreBg(score)}`}
                                style={{ width: `${score ?? 0}%` }}
                              />
                            </div>
                            <span
                              className={`text-sm font-semibold w-8 text-right ${getScoreColor(score)}`}
                            >
                              {score != null ? score.toFixed(0) : "—"}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                    <Separator />
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Overall</span>
                      <span
                        className={`text-sm font-bold ${getScoreColor(performance.avg_overall_score)}`}
                      >
                        {performance.avg_overall_score != null
                          ? performance.avg_overall_score.toFixed(1)
                          : "—"}
                      </span>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground py-4">
                    Select a salesperson to view their performance data.
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Radar Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Skill Radar</CardTitle>
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

          {/* Improvement Areas */}
          {weakestSkills.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  Improvement Areas
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {weakestSkills.map((s) => (
                    <div
                      key={s.key}
                      className="flex items-start gap-3 rounded-md border border-amber-100 bg-amber-50/50 p-3"
                    >
                      <Badge
                        variant="outline"
                        className={`shrink-0 mt-0.5 ${getScoreColor(s.score)}`}
                      >
                        {s.score.toFixed(0)}
                      </Badge>
                      <div>
                        <p className="text-sm font-medium">{s.label}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
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
          {recommendations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="h-4 w-4 text-blue-500" />
                  Recommendations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {recommendations.map((rec, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 rounded-md border border-blue-100 bg-blue-50/50 p-3"
                    >
                      <Lightbulb className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium">
                          Improve {rec.skill} (currently {rec.score.toFixed(0)})
                        </p>
                        <p className="text-xs text-muted-foreground mt-0.5">{rec.tip}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Historical Trend */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                Score Trend
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={mockTrendData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="week" className="text-xs" />
                    <YAxis domain={[0, 100]} className="text-xs" />
                    <RechartsTooltip />
                    <Line
                      type="monotone"
                      dataKey="score"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-2 text-xs text-muted-foreground text-center">
                Weekly overall score trend (sample data)
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="30d" className="mt-4">
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground text-sm">
              30-day detailed view with conversation-level breakdown
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="60d" className="mt-4">
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground text-sm">
              60-day trend analysis with week-over-week comparisons
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="90d" className="mt-4">
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground text-sm">
              90-day quarterly review with comprehensive performance summary
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
