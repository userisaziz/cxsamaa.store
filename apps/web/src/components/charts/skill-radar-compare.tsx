"use client";

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { SalespersonComparisonItem } from "@samaa/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Inbox } from "lucide-react";

const SKILL_KEYS = [
  { key: "avg_greeting_score", label: "Greeting" },
  { key: "avg_discovery_score", label: "Discovery" },
  { key: "avg_product_knowledge_score", label: "Product Knowledge" },
  { key: "avg_objection_handling_score", label: "Objection Handling" },
  { key: "avg_closing_score", label: "Closing" },
] as const;

const RADAR_COLORS = [
  "#22c55e", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4",
];

interface SkillRadarCompareProps {
  data: SalespersonComparisonItem[];
  title?: string;
}

export function SkillRadarCompare({ data, title = "Skill Comparison" }: SkillRadarCompareProps) {
  const validData = data.filter((d) => d.avg_overall_score != null);
  const hasData = validData.length > 0;

  // Build radar data with each salesperson as a series
  const radarData = SKILL_KEYS.map(({ key, label }) => {
    const point: Record<string, string | number> = { skill: label };
    validData.forEach((sp) => {
      point[sp.name] = (sp[key as keyof SalespersonComparisonItem] as number | null) ?? 0;
    });
    return point;
  });

  return (
    <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
      <CardHeader>
        <CardTitle className="text-sm font-medium text-steel">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {hasData ? (
          <div className="h-[260px] sm:h-[280px] lg:h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid className="stroke-muted" />
                <PolarAngleAxis dataKey="skill" className="text-xs fill-muted-foreground" />
                <PolarRadiusAxis angle={90} domain={[0, 100]} className="text-xs fill-muted-foreground" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                {validData.map((sp, i) => (
                  <Radar
                    key={sp.salesperson_id}
                    name={sp.name}
                    dataKey={sp.name}
                    stroke={RADAR_COLORS[i % RADAR_COLORS.length]}
                    fill={RADAR_COLORS[i % RADAR_COLORS.length]}
                    fillOpacity={0.1}
                    strokeWidth={2}
                  />
                ))}
                <Legend wrapperStyle={{ fontSize: "11px" }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-[260px] sm:h-[280px] lg:h-[300px] flex-col items-center justify-center text-center">
            <Inbox className="h-8 w-8 text-stone/40 mb-2" />
            <p className="text-sm text-steel">No skill data yet</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
