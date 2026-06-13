"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Brush,
} from "recharts";
import type { TrendPoint } from "@samaa/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Inbox } from "lucide-react";

interface ScoreTrendProps {
  data: TrendPoint[];
  title?: string;
}

function ScoreTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-md">
      <p className="text-xs text-steel">{label}</p>
      <p className="text-sm font-bold font-mono text-ink">
        {payload[0]?.value?.toFixed(1) ?? "—"}
      </p>
    </div>
  );
}

export function ScoreTrend({ data, title = "Score Trend" }: ScoreTrendProps) {
  const hasData = data.length > 0 && data.some((d) => d.avg_score != null);

  return (
    <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
      <CardHeader>
        <CardTitle className="text-sm font-medium text-steel">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {hasData ? (
          <div className="h-[200px] sm:h-[220px] lg:h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  dataKey="date"
                  className="text-xs"
                  tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                  tickFormatter={(v: string) => new Date(v).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                />
                <YAxis domain={[0, 100]} className="text-xs" tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} />
                <Tooltip content={<ScoreTooltip />} />
                <Area
                  type="monotone"
                  dataKey="avg_score"
                  stroke="#22c55e"
                  strokeWidth={2}
                  fill="url(#scoreGradient)"
                  dot={{ r: 3, fill: "#22c55e" }}
                  activeDot={{ r: 5 }}
                />
                {data.length > 14 && <Brush dataKey="date" height={24} stroke="var(--border)" fill="var(--muted)" />}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-[200px] sm:h-[220px] lg:h-[240px] flex-col items-center justify-center text-center">
            <Inbox className="h-8 w-8 text-stone/40 mb-2" />
            <p className="text-sm text-steel">No trend data yet</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
