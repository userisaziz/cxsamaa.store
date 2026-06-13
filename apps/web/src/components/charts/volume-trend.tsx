"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { TrendPoint } from "@samaa/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Inbox } from "lucide-react";

interface VolumeTrendProps {
  data: TrendPoint[];
  title?: string;
}

function VolumeTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-md">
      <p className="text-xs text-steel">{label}</p>
      <p className="text-sm font-bold font-mono text-ink">{payload[0]?.value ?? 0}</p>
      <p className="text-xs text-steel">conversations</p>
    </div>
  );
}

export function VolumeTrend({ data, title = "Conversation Volume" }: VolumeTrendProps) {
  const hasData = data.length > 0 && data.some((d) => d.conversation_count > 0);

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
                  <linearGradient id="volumeGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--chart-2)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="var(--chart-2)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  dataKey="date"
                  className="text-xs"
                  tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                  tickFormatter={(v: string) => new Date(v).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                />
                <YAxis className="text-xs" tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} allowDecimals={false} />
                <Tooltip content={<VolumeTooltip />} />
                <Area
                  type="monotone"
                  dataKey="conversation_count"
                  stroke="var(--chart-2)"
                  strokeWidth={2}
                  fill="url(#volumeGradient)"
                  dot={{ r: 3, fill: "var(--chart-2)" }}
                  activeDot={{ r: 5 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-[200px] sm:h-[220px] lg:h-[240px] flex-col items-center justify-center text-center">
            <Inbox className="h-8 w-8 text-stone/40 mb-2" />
            <p className="text-sm text-steel">No volume data yet</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
