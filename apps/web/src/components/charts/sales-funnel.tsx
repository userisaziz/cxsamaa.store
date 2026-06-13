"use client";

import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Inbox } from "lucide-react";
import type { FunnelStage } from "@samaa/shared";

interface SalesFunnelProps {
  data: FunnelStage[];
  title?: string;
  onStageClick?: (stage: string) => void;
}

function fmt(n: number): string {
  return n.toLocaleString();
}

function pct(a: number, b: number): string {
  return b > 0 ? ((a / b) * 100).toFixed(1) : "0";
}

function getBarColor(index: number, isFinal: boolean): string {
  if (isFinal) return "oklch(0.65 0.2 165)"; // brand-green-deep
  
  // Neutral progression: ink → charcoal → slate → steel
  const colors = [
    "oklch(0.15 0 0)",      // ink (darkest)
    "oklch(0.25 0 0)",      // charcoal
    "oklch(0.45 0 0)",      // slate
    "oklch(0.55 0 0)",      // steel
    "oklch(0.65 0 0)",      // stone
  ];
  
  return colors[Math.min(index, colors.length - 1)];
}

function getPillVariant(dropRate: number): "ok" | "warn" | "bad" {
  if (dropRate > 50) return "bad";
  if (dropRate > 30) return "warn";
  return "ok";
}

const PILL_STYLES: Record<"ok" | "warn" | "bad", React.CSSProperties> = {
  ok: {
    background: "oklch(0.96 0.04 165)", // brand-green-soft
    color: "oklch(0.45 0.15 165)",      // brand-green-deep
  },
  warn: {
    background: "oklch(0.97 0.06 95)",  // warm amber tint
    color: "oklch(0.45 0.12 70)",       // amber-700
  },
  bad: {
    background: "oklch(0.97 0.04 25)",  // red tint
    color: "oklch(0.50 0.18 25)",       // red-600
  },
};

export function SalesFunnel({
  data,
  title = "Sales Pipeline",
  onStageClick,
}: SalesFunnelProps) {
  const hasData = data.length > 0 && data.some((d) => d.count > 0);

  const topCount = data[0]?.count ?? 1;
  const botCount = data[data.length - 1]?.count ?? 0;

  const stages = useMemo(
    () =>
      data.map((s, i) => {
        const prev = i > 0 ? data[i - 1].count : s.count;
        const dropped = i > 0 ? prev - s.count : 0;
        const dropRate = i > 0 && prev > 0 ? (dropped / prev) * 100 : 0;
        const convRate = i > 0 && prev > 0 ? (s.count / prev) * 100 : 100;
        const barWidth = Math.max((s.count / topCount) * 100, 18);
        return { ...s, dropped, dropRate, convRate, barWidth };
      }),
    [data, topCount],
  );

  const leakIdx = useMemo(() => {
    let maxDrop = 0;
    let idx = -1;
    stages.forEach((s, i) => {
      if (i > 0 && s.dropped > maxDrop) {
        maxDrop = s.dropped;
        idx = i;
      }
    });
    return idx;
  }, [stages]);

  const leakStage = leakIdx > 0 ? stages[leakIdx] : null;
  const leakPrev = leakIdx > 0 ? stages[leakIdx - 1] : null;

  return (
    <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)] overflow-hidden">
      {/* Header */}
      <CardHeader className="py-4 px-5 border-b border-border/40">
        <div className="flex items-center justify-between">
          <CardTitle className="text-[13px] font-medium text-steel">
            {title}
          </CardTitle>
          {hasData && (
            <span className="text-[11px] font-mono text-steel/50 bg-stone/10 px-2 py-0.5 rounded-full">
              {data.length} stages
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {hasData ? (
          <>
            {/* Stage rows */}
            <div className="px-5 py-6 flex flex-col gap-0">
              {stages.map((stage, i) => {
                const isFinal = i === stages.length - 1;
                const isLeak = i === leakIdx;
                const fill = getBarColor(i, isFinal);
                const nextStage = !isFinal ? stages[i + 1] : null;

                return (
                  <div key={stage.stage}>
                    {/* Bar row */}
                    <div
                      className="grid items-center gap-3 py-[5px]"
                      style={{ gridTemplateColumns: "96px 1fr 52px" }}
                    >
                      {/* Label */}
                      <div className="flex items-center justify-end gap-1.5 min-w-0">
                        <span
                          className="text-[12px] text-steel/80 truncate text-right"
                          title={stage.stage}
                        >
                          {stage.stage}
                        </span>
                        {isLeak && (
                          <span className="shrink-0 text-[10px] font-mono px-1.5 py-px rounded-[3px]" style={PILL_STYLES.bad}>
                            drop
                          </span>
                        )}
                      </div>

                      {/* Bar */}
                      <div className="relative h-9 bg-stone/10 rounded-[5px] overflow-hidden">
                        <button
                          type="button"
                          className="absolute inset-y-0 left-0 flex items-center pl-3 rounded-[5px] transition-[filter] duration-100 hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1"
                          style={{
                            width: `${stage.barWidth}%`,
                            backgroundColor: fill,
                            cursor: onStageClick ? "pointer" : "default",
                          }}
                          onClick={() => onStageClick?.(stage.stage)}
                          aria-label={`${stage.stage}: ${fmt(stage.count)} (${pct(stage.count, topCount)}% of total)`}
                        >
                          <span className="text-[13px] font-medium font-mono text-white whitespace-nowrap">
                            {fmt(stage.count)}
                          </span>
                        </button>
                      </div>

                      {/* % of total */}
                      <span className="text-[11px] font-mono text-steel/50 text-right tabular-nums">
                        {pct(stage.count, topCount)}%
                      </span>
                    </div>

                    {/* Connector pill between stages */}
                    {nextStage && (
                      <div
                        className="grid items-center gap-3 py-[3px]"
                        style={{ gridTemplateColumns: "96px 1fr 52px" }}
                      >
                        <span />
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-px bg-border/40" />
                          <span
                            className="text-[11px] font-mono px-2 py-0.5 rounded-full whitespace-nowrap"
                            style={PILL_STYLES[getPillVariant(stage.dropRate)]}
                          >
                            {nextStage.convRate.toFixed(0)}% continue · {fmt(stage.dropped)} lost
                          </span>
                          <div className="flex-1 h-px bg-border/40" />
                        </div>
                        <span />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Footer stats */}
            <div className="grid grid-cols-3 border-t border-border/40">
              <div className="px-5 py-4 border-r border-border/40">
                <p className="text-[11px] uppercase tracking-wider text-steel/50 mb-1">
                  Conversion rate
                </p>
                <p className="text-xl font-medium font-mono tabular-nums" style={{ color: "oklch(0.65 0.2 165)" }}>
                  {pct(botCount, topCount)}%
                </p>
                <p className="text-[11px] text-steel/40 mt-0.5">
                  {fmt(botCount)} sales from {fmt(topCount)}
                </p>
              </div>

              <div className="px-5 py-4 border-r border-border/40">
                <p className="text-[11px] uppercase tracking-wider text-steel/50 mb-1">
                  Total conversations
                </p>
                <p className="text-xl font-medium font-mono text-steel tabular-nums">
                  {fmt(topCount)}
                </p>
                <p className="text-[11px] text-steel/40 mt-0.5">
                  entered pipeline
                </p>
              </div>

              <div className="px-5 py-4">
                <p className="text-[11px] uppercase tracking-wider text-steel/50 mb-1">
                  Biggest drop-off
                </p>
                {leakStage && leakPrev ? (
                  <>
                    <p className="text-[13px] font-medium leading-snug" style={{ color: "oklch(0.50 0.18 25)" }}>
                      {leakPrev.stage} → {leakStage.stage}
                    </p>
                    <p className="text-[11px] text-steel/40 mt-0.5">
                      −{fmt(leakStage.dropped)} conversations ({leakStage.dropRate.toFixed(0)}% lost)
                    </p>
                  </>
                ) : (
                  <p className="text-[13px] text-steel/30">—</p>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="flex h-[200px] flex-col items-center justify-center text-center px-5">
            <Inbox className="h-8 w-8 text-stone/30 mb-2" />
            <p className="text-sm text-steel">No sales data yet</p>
            <p className="text-xs text-steel/40 mt-1">
              Upload audio recordings to track your sales pipeline
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}