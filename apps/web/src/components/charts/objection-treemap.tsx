"use client";

import {
  Treemap,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { ObjectionCount } from "@samaa/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Inbox } from "lucide-react";

interface ObjectionTreemapProps {
  data: ObjectionCount[];
  title?: string;
  onObjectionClick?: (objection: string) => void;
}

const COLORS = [
  "#3b82f6", "#ef4444", "#f59e0b", "#22c55e", "#8b5cf6",
  "#ec4899", "#06b6d4", "#f97316", "#6366f1", "#14b8a6",
];

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: { name: string; value: number } }> }) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-md">
      <p className="text-xs font-medium text-ink max-w-[200px] truncate">{item.name}</p>
      <p className="text-sm font-bold font-mono text-ink">{item.value}</p>
    </div>
  );
}

function CustomContent(props: {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  value?: number;
  index?: number;
  root?: { children?: Array<{ value: number }> };
}) {
  const { x = 0, y = 0, width = 0, height = 0, name, value, index = 0 } = props;
  const total = props.root?.children?.reduce((s, c) => s + (c.value ?? 0), 0) ?? value ?? 1;
  const pct = total > 0 && value ? ((value / total) * 100).toFixed(0) : "";

  if (width < 40 || height < 30) return null;

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={COLORS[index % COLORS.length]}
        rx={4}
        className="cursor-pointer transition-opacity hover:opacity-80"
        stroke="#fff"
        strokeWidth={2}
      />
      {width > 60 && height > 40 && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - 8}
            textAnchor="middle"
            fill="#fff"
            fontSize={width > 100 ? 12 : 10}
            fontWeight={500}
          >
            {name && name.length > width / 7 ? `${name.slice(0, Math.floor(width / 7))}…` : name}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + 10}
            textAnchor="middle"
            fill="rgba(255,255,255,0.85)"
            fontSize={11}
            fontFamily="monospace"
          >
            {value} ({pct}%)
          </text>
        </>
      )}
    </g>
  );
}

export function ObjectionTreemap({ data, title = "Top Objections", onObjectionClick }: ObjectionTreemapProps) {
  const hasData = data.length > 0 && data.some((d) => d.count > 0);

  const treemapData = data
    .filter((d) => d.count > 0)
    .map((d) => ({ name: d.objection, value: d.count }));

  return (
    <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
      <CardHeader>
        <CardTitle className="text-sm font-medium text-steel">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {hasData ? (
          <div className="h-[220px] sm:h-[240px] lg:h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
              <Treemap
                data={treemapData}
                dataKey="value"
                content={
                  <CustomContent
                    root={{ children: treemapData.map((d) => ({ value: d.value })) }}
                  />
                }
                onClick={(entry) => {
                  if (entry?.name) onObjectionClick?.(entry.name as string);
                }}
              >
                <Tooltip content={<CustomTooltip />} />
              </Treemap>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-[220px] sm:h-[240px] lg:h-[260px] flex-col items-center justify-center text-center">
            <Inbox className="h-8 w-8 text-stone/40 mb-2" />
            <p className="text-sm text-steel">No objection data yet</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
