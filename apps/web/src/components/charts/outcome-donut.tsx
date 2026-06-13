"use client";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";
import type { OutcomeCount } from "@samaa/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Inbox } from "lucide-react";

const OUTCOME_COLORS: Record<string, string> = {
  SALE_MADE: "#22c55e",
  LOST: "#ef4444",
  FOLLOW_UP_NEEDED: "#f59e0b",
};

const OUTCOME_LABELS: Record<string, string> = {
  SALE_MADE: "Sale Made",
  LOST: "Lost",
  FOLLOW_UP_NEEDED: "Follow Up",
};

interface OutcomeDonutProps {
  data: OutcomeCount[];
  title?: string;
  onOutcomeClick?: (outcome: string) => void;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number; payload: { percent: number } }> }) {
  if (!active || !payload?.length) return null;
  const item = payload[0];
  const total = item.payload.percent ? Math.round((item.value / item.payload.percent) * 100) : item.value;
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-md">
      <p className="text-xs font-medium text-ink">{OUTCOME_LABELS[item.name] ?? item.name}</p>
      <p className="text-sm font-bold font-mono text-ink">{item.value}</p>
      <p className="text-xs text-steel">{total > 0 ? `${((item.value / total) * 100).toFixed(1)}%` : ""}</p>
    </div>
  );
}

export function OutcomeDonut({ data, title = "Conversation Outcomes", onOutcomeClick }: OutcomeDonutProps) {
  const hasData = data.length > 0 && data.some((d) => d.count > 0);

  return (
    <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
      <CardHeader>
        <CardTitle className="text-sm font-medium text-steel">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {hasData ? (
          <div className="h-[200px] sm:h-[220px] lg:h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="count"
                  nameKey="outcome"
                  onClick={(entry) => onOutcomeClick?.((entry as unknown as OutcomeCount).outcome)}
                  className="cursor-pointer"
                >
                  {data.map((entry) => (
                    <Cell
                      key={entry.outcome}
                      fill={OUTCOME_COLORS[entry.outcome] ?? "#94a3b8"}
                    />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  formatter={(value: string) => (
                    <span className="text-xs text-charcoal">
                      {OUTCOME_LABELS[value] ?? value}
                    </span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-[200px] sm:h-[220px] lg:h-[240px] flex-col items-center justify-center text-center">
            <Inbox className="h-8 w-8 text-stone/40 mb-2" />
            <p className="text-sm text-steel">No outcome data yet</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
