"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { StoreComparisonItem } from "@samaa/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Inbox } from "lucide-react";
import { useRouter } from "next/navigation";

interface StoreScatterProps {
  data: StoreComparisonItem[];
  title?: string;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: StoreComparisonItem & { z: number } }> }) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-md">
      <p className="text-xs font-medium text-ink">{item.store_name}</p>
      <div className="mt-1 space-y-0.5">
        <p className="text-xs text-steel">
          Avg Score: <span className="font-mono text-ink">{item.avg_score?.toFixed(1) ?? "–"}</span>
        </p>
        <p className="text-xs text-steel">
          Conversion: <span className="font-mono text-ink">{item.conversion_rate != null ? `${item.conversion_rate.toFixed(1)}%` : "–"}</span>
        </p>
        <p className="text-xs text-steel">
          Conversations: <span className="font-mono text-ink">{item.total_conversations}</span>
        </p>
      </div>
    </div>
  );
}

export function StoreScatter({ data, title = "Store Comparison" }: StoreScatterProps) {
  const router = useRouter();
  const hasData = data.length > 0 && data.some((d) => d.total_conversations > 0);

  const scatterData = data
    .filter((d) => d.total_conversations > 0)
    .map((d) => ({
      ...d,
      x: d.avg_score ?? 0,
      y: (d.conversion_rate ?? 0),
      z: d.total_conversations,
    }));

  return (
    <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
      <CardHeader>
        <CardTitle className="text-sm font-medium text-steel">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {hasData ? (
          <div className="h-[240px] sm:h-[260px] lg:h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  type="number"
                  dataKey="x"
                  name="Avg Score"
                  domain={[0, 100]}
                  tickLine={false}
                  tick={{ fontSize: 11, fill: "var(--steel)" }}
                  label={{ value: "Avg Score", position: "bottom", offset: 0, style: { fontSize: 11, fill: "var(--steel)" } }}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name="Conversion %"
                  domain={[0, 100]}
                  tickLine={false}
                  tick={{ fontSize: 11, fill: "var(--steel)" }}
                  label={{ value: "Conversion %", angle: -90, position: "insideLeft", offset: 10, style: { fontSize: 11, fill: "var(--steel)" } }}
                />
                <ZAxis type="number" dataKey="z" range={[80, 400]} />
                <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: "3 3" }} />
                <Scatter
                  data={scatterData}
                  fill="var(--brand-green, #22c55e)"
                  fillOpacity={0.7}
                  className="cursor-pointer"
                  onClick={(_entry, _index, e) => {
                    // Use the payload from the click event
                    const payload = (e as { payload?: { store_id?: string } })?.payload ?? (_entry as unknown as { store_id?: string });
                    if (payload?.store_id) router.push(`/store/${payload.store_id}`);
                  }}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-[240px] sm:h-[260px] lg:h-[280px] flex-col items-center justify-center text-center">
            <Inbox className="h-8 w-8 text-stone/40 mb-2" />
            <p className="text-sm text-steel">No store comparison data yet</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
