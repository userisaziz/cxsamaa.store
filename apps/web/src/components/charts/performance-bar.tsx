"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { SalespersonComparisonItem } from "@samaa/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Inbox } from "lucide-react";
import { useRouter } from "next/navigation";

interface PerformanceBarProps {
  data: SalespersonComparisonItem[];
  title?: string;
}

function ScoreTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: SalespersonComparisonItem }> }) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-md">
      <p className="text-xs font-medium text-ink">{item.name}</p>
      <p className="text-sm font-bold font-mono text-ink">
        {item.avg_overall_score?.toFixed(1) ?? "—"} / 100
      </p>
      <p className="text-xs text-steel">{item.total_conversations} conversations</p>
    </div>
  );
}

function getBarColor(score: number | null): string {
  if (score == null) return "#94a3b8";
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#f59e0b";
  return "#ef4444";
}

export function PerformanceBar({ data, title = "Salesperson Rankings" }: PerformanceBarProps) {
  const router = useRouter();
  const sorted = [...data].sort(
    (a, b) => (b.avg_overall_score ?? 0) - (a.avg_overall_score ?? 0)
  );
  const hasData = sorted.length > 0 && sorted.some((d) => d.avg_overall_score != null);

  return (
    <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
      <CardHeader>
        <CardTitle className="text-sm font-medium text-steel">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {hasData ? (
          <div className="h-[260px] sm:h-[280px] lg:h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sorted} layout="vertical" margin={{ left: 20, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} className="text-xs" tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  className="text-xs"
                  tick={{ fill: "var(--charcoal)", fontSize: 12 }}
                  width={100}
                />
                <Tooltip content={<ScoreTooltip />} cursor={{ fill: "var(--muted)", opacity: 0.3 }} />
                <Bar
                  dataKey="avg_overall_score"
                  radius={[0, 6, 6, 0]}
                  onClick={(_data, index) => {
                    const item = sorted[index];
                    if (item) router.push(`/salesperson/${item.salesperson_id}`);
                  }}
                  className="cursor-pointer"
                >
                  {sorted.map((entry, i) => (
                    <Cell key={i} fill={getBarColor(entry.avg_overall_score)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-[260px] sm:h-[280px] lg:h-[300px] flex-col items-center justify-center text-center">
            <Inbox className="h-8 w-8 text-stone/40 mb-2" />
            <p className="text-sm text-steel">No performance data yet</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
