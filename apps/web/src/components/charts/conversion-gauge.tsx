"use client";

import {
  RadialBarChart,
  RadialBar,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Inbox } from "lucide-react";

interface ConversionGaugeProps {
  value: number | null; // 0-1 ratio
  title?: string;
  label?: string;
}

function gaugeColor(value: number): string {
  if (value >= 60) return "#22c55e";
  if (value >= 30) return "#f59e0b";
  return "#ef4444";
}

export function ConversionGauge({
  value,
  title = "Conversion Rate",
  label,
}: ConversionGaugeProps) {
  // Auto-detect format: if value > 1, assume it's a percentage (0-100), otherwise it's a ratio (0-1)
  const pct = value != null ? (value > 1 ? Math.round(value) : Math.round(value * 100)) : null;
  const hasData = pct != null;

  const gaugeData = hasData
    ? [{ name: "conversion", value: pct, fill: gaugeColor(pct) }]
    : [];

  return (
    <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
      <CardHeader>
        <CardTitle className="text-sm font-medium text-steel">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {hasData ? (
          <div className="relative h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadialBarChart
                cx="50%"
                cy="55%"
                innerRadius="70%"
                outerRadius="100%"
                barSize={14}
                data={gaugeData}
                startAngle={180}
                endAngle={0}
              >
                <RadialBar
                  dataKey="value"
                  cornerRadius={8}
                  background={{ fill: "var(--muted, #f1f5f9)" }}
                />
              </RadialBarChart>
            </ResponsiveContainer>
            {/* Center label */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pt-4">
              <span
                className="text-3xl font-bold font-mono"
                style={{ color: gaugeColor(pct) }}
              >
                {pct}%
              </span>
              {label && (
                <span className="text-xs text-steel mt-1">{label}</span>
              )}
            </div>
          </div>
        ) : (
          <div className="flex h-[200px] flex-col items-center justify-center text-center">
            <Inbox className="h-8 w-8 text-stone/40 mb-2" />
            <p className="text-sm text-steel">No conversion data yet</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
