"use client";

import { useState } from "react";
import { CalendarIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export interface DateRange {
  from: Date;
  to: Date;
}

export interface DateRangeFilterProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
  className?: string;
}

const PRESETS = [
  { label: "Last 7 days", days: 7 },
  { label: "Last 30 days", days: 30 },
  { label: "Last 90 days", days: 90 },
  { label: "This year", days: -1 },
] as const;

function getDateRange(days: number): DateRange {
  const now = new Date();
  const to = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
  
  let from: Date;
  if (days === -1) {
    // This year
    from = new Date(now.getFullYear(), 0, 1, 0, 0, 0);
  } else {
    from = new Date(now);
    from.setDate(from.getDate() - days);
    from.setHours(0, 0, 0, 0);
  }
  
  return { from, to };
}

function formatDateRange(range: DateRange): string {
  const fromStr = range.from.toLocaleDateString("en-US", { 
    month: "short", 
    day: "numeric",
    year: "numeric"
  });
  const toStr = range.to.toLocaleDateString("en-US", { 
    month: "short", 
    day: "numeric",
    year: "numeric"
  });
  return `${fromStr} - ${toStr}`;
}

export function DateRangeFilter({ value, onChange, className }: DateRangeFilterProps) {
  const [activePreset, setActivePreset] = useState("30");

  const handlePresetChange = (presetValue: string | null) => {
    if (!presetValue) return;
    setActivePreset(presetValue);
    const days = parseInt(presetValue);
    onChange(getDateRange(days));
  };

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {/* Preset selector */}
      <Select value={activePreset} onValueChange={handlePresetChange}>
        <SelectTrigger className="w-[180px] h-9">
          <CalendarIcon className="h-4 w-4 mr-2" />
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {PRESETS.map((preset) => (
            <SelectItem key={preset.label} value={String(preset.days)}>
              {preset.label}
            </SelectItem>
          ))}
          <SelectItem value="custom">Custom range</SelectItem>
        </SelectContent>
      </Select>

      {/* Date range display */}
      <div className="px-3 py-1.5 bg-surface-soft rounded-md border border-hairline-soft">
        <span className="text-xs font-mono text-steel">
          {formatDateRange(value)}
        </span>
      </div>
    </div>
  );
}
