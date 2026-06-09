import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";

interface KPICardProps {
  title: string;
  value: string | number;
  description?: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
}

export function KPICard({ title, value, description, icon: Icon, trend }: KPICardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-steel">{title}</CardTitle>
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-green-soft">
          <Icon className="h-4 w-4 text-brand-green-deep" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold tracking-tight text-ink">{value}</div>
        {description && (
          <p className="mt-1 text-xs text-steel">{description}</p>
        )}
        {trend && (
          <p
            className={`mt-1 text-xs font-medium ${
              trend.isPositive ? "text-brand-green-deep" : "text-destructive"
            }`}
          >
            {trend.isPositive ? "+" : ""}
            {trend.value}% from last period
          </p>
        )}
      </CardContent>
    </Card>
  );
}
