"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Inbox } from "lucide-react";
import type { SalespersonComparisonItem } from "@samaa/shared";
import { useRouter } from "next/navigation";

interface SkillHeatmapProps {
  data: SalespersonComparisonItem[];
  title?: string;
}

const DIMENSIONS: { key: keyof SalespersonComparisonItem; label: string }[] = [
  { key: "avg_greeting_score", label: "Greeting" },
  { key: "avg_discovery_score", label: "Discovery" },
  { key: "avg_product_knowledge_score", label: "Product" },
  { key: "avg_objection_handling_score", label: "Objections" },
  { key: "avg_closing_score", label: "Closing" },
];

function scoreToColor(score: number | null): string {
  if (score == null) return "var(--stone)";
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#f59e0b";
  return "#ef4444";
}

function scoreToOpacity(score: number | null): number {
  if (score == null) return 0.15;
  return 0.3 + (score / 100) * 0.7;
}

export function SkillHeatmap({ data, title = "Team Skill Heatmap" }: SkillHeatmapProps) {
  const router = useRouter();
  const hasData = data.length > 0 && data.some(
    (d) =>
      d.avg_greeting_score != null ||
      d.avg_discovery_score != null ||
      d.avg_product_knowledge_score != null ||
      d.avg_objection_handling_score != null ||
      d.avg_closing_score != null,
  );

  return (
    <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
      <CardHeader>
        <CardTitle className="text-sm font-medium text-steel">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {hasData ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="text-left text-xs font-medium text-steel pb-2 pr-4 min-w-[120px]">
                    Salesperson
                  </th>
                  {DIMENSIONS.map((dim) => (
                    <th
                      key={dim.key}
                      className="text-center text-xs font-medium text-steel pb-2 px-2 min-w-[80px]"
                    >
                      {dim.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.map((person) => (
                  <tr
                    key={person.salesperson_id}
                    className="cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => router.push(`/salesperson/${person.salesperson_id}`)}
                  >
                    <td className="py-1.5 pr-4 text-xs font-medium text-ink truncate max-w-[140px]">
                      {person.name}
                    </td>
                    {DIMENSIONS.map((dim) => {
                      const score = person[dim.key] as number | null;
                      return (
                        <td key={dim.key} className="py-1.5 px-2">
                          <div
                            className="group relative flex items-center justify-center rounded-md py-2.5 text-xs font-mono font-medium text-white transition-transform hover:scale-105"
                            style={{
                              backgroundColor: scoreToColor(score),
                              opacity: scoreToOpacity(score),
                            }}
                          >
                            {score != null ? score.toFixed(0) : "–"}
                            <div className="absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-popover border border-border px-2 py-1 text-xs text-ink shadow-md opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10">
                              {dim.label}: {score?.toFixed(1) ?? "N/A"}
                            </div>
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex h-[180px] sm:h-[200px] lg:h-[220px] flex-col items-center justify-center text-center">
            <Inbox className="h-8 w-8 text-stone/40 mb-2" />
            <p className="text-sm text-steel">No skill data available</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
