"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { Salesperson, SalespersonComparisonItem, ObjectionCount } from "@samaa/shared";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Users,
  Inbox,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  X,
  Trophy,
  TrendingUp,
  AlertTriangle,
  Target,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from "recharts";

type SortField = "name" | "role" | "shift";
type SortDirection = "asc" | "desc";

interface SortConfig {
  field: SortField;
  direction: SortDirection;
}

/**
 * Get sort icon based on field and direction
 */
function SortIcon({ field, config }: { field: SortField; config: SortConfig }) {
  if (config.field !== field) {
    return <ArrowUpDown className="h-3.5 w-3.5" />;
  }
  return config.direction === "asc" ? (
    <ArrowUp className="h-3.5 w-3.5" />
  ) : (
    <ArrowDown className="h-3.5 w-3.5" />
  );
}

export default function SalespeoplePage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Initialize state from URL params
  const [searchQuery, setSearchQuery] = useState(searchParams.get("search") || "");
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    field: (searchParams.get("sort") as SortField) || "name",
    direction: (searchParams.get("dir") as SortDirection) || "asc",
  });

  const { data: salespeople, isLoading: isLoadingSalespeople } = useQuery({
    queryKey: ["salespeople"],
    queryFn: () => api.get<Salesperson[]>("/salespeople"),
  });

  // Fetch analytics for ranking and skills
  const { data: analytics, isLoading: isLoadingAnalytics } = useQuery({
    queryKey: ["analytics-salespeople"],
    queryFn: () =>
      api.get<{ salespeople: SalespersonComparisonItem[]; top_objections: ObjectionCount[] }>(
        "/analytics/salespeople-comparison",
      ),
  });

  // Merge salespeople with analytics
  const salespeopleWithAnalytics = useMemo(() => {
    if (!salespeople || !analytics?.salespeople) return [];

    const analyticsMap = new Map(
      analytics.salespeople.map((a) => [a.salesperson_id, a])
    );

    return salespeople.map((sp) => ({
      ...sp,
      analytics: analyticsMap.get(sp.id) || null,
    }));
  }, [salespeople, analytics]);

  // Filter and sort salespeople
  const filteredAndSorted = useMemo(() => {
    if (!salespeople) return [];

    let result = [...salespeople];

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (sp) =>
          sp.name.toLowerCase().includes(query) ||
          sp.email?.toLowerCase().includes(query) ||
          sp.role?.toLowerCase().includes(query) ||
          sp.shift?.toLowerCase().includes(query),
      );
    }

    // Apply sorting
    result.sort((a, b) => {
      const field = sortConfig.field;
      const aVal = (a[field] || "").toLowerCase();
      const bVal = (b[field] || "").toLowerCase();

      if (aVal < bVal) return sortConfig.direction === "asc" ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === "asc" ? 1 : -1;
      return 0;
    });

    return result;
  }, [salespeople, searchQuery, sortConfig]);

  /**
   * Update URL params when filters change
   */
  const updateUrlParams = (search: string, sort: SortConfig) => {
    const params = new URLSearchParams(searchParams.toString());

    if (search) {
      params.set("search", search);
    } else {
      params.delete("search");
    }

    if (sort.field !== "name" || sort.direction !== "asc") {
      params.set("sort", sort.field);
      params.set("dir", sort.direction);
    } else {
      params.delete("sort");
      params.delete("dir");
    }

    const newUrl = params.toString() ? `?${params.toString()}` : window.location.pathname;
    router.replace(newUrl, { scroll: false });
  };

  /**
   * Handle sort column click
   */
  const handleSort = (field: SortField) => {
    const newDirection: SortDirection =
      sortConfig.field === field && sortConfig.direction === "asc" ? "desc" : "asc";
    const newConfig = { field, direction: newDirection };
    setSortConfig(newConfig);
    updateUrlParams(searchQuery, newConfig);
  };

  /**
   * Handle search input change with debounce
   */
  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    // Debounce URL updates for better UX
    const timeoutId = setTimeout(() => {
      updateUrlParams(value, sortConfig);
    }, 300);
    return () => clearTimeout(timeoutId);
  };

  /**
   * Clear all filters
   */
  const clearFilters = () => {
    setSearchQuery("");
    setSortConfig({ field: "name", direction: "asc" });
    router.replace(window.location.pathname, { scroll: false });
  };

  const hasActiveFilters = searchQuery || sortConfig.field !== "name" || sortConfig.direction !== "asc";
  const isLoading = isLoadingSalespeople || isLoadingAnalytics;

  // Calculate rankings
  const rankedSalespeople = useMemo(() => {
    if (!salespeopleWithAnalytics.length) return [];

    return salespeopleWithAnalytics
      .filter((sp) => sp.analytics)
      .sort((a, b) => {
        const aScore = a.analytics?.avg_overall_score || 0;
        const bScore = b.analytics?.avg_overall_score || 0;
        return bScore - aScore; // Highest score first
      })
      .map((sp, index) => ({
        ...sp,
        rank: index + 1,
      }));
  }, [salespeopleWithAnalytics]);

  return (
    <div className="space-y-6 lg:space-y-8 p-4 sm:p-6 lg:p-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4 sm:pb-6">
        <div>
          <h1 className="text-[22px] sm:text-[28px] font-semibold tracking-tight text-ink leading-tight">Salespeople</h1>
          <p className="mt-1 text-sm text-steel">
            {salespeople ? (
              <span className="font-mono">{salespeople.length}</span> + " team members"
            ) : (
              "Manage sales team members"
            )}
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <Card className="shadow-none border-border">
        <CardContent className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 py-4">
          {/* Search Input */}
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-steel" />
            <Input
              placeholder="Search by name, email, role..."
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-9 h-9"
            />
            {searchQuery && (
              <button
                onClick={() => handleSearchChange("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-accent transition-colors"
                type="button"
              >
                <X className="h-3.5 w-3.5 text-steel" />
              </button>
            )}
          </div>

          {/* Sort Select */}
          <Select
            value={sortConfig.field}
            onValueChange={(value) => {
              if (value) {
                const newConfig = { field: value as SortField, direction: sortConfig.direction };
                setSortConfig(newConfig);
                updateUrlParams(searchQuery, newConfig);
              }
            }}
          >
            <SelectTrigger className="w-full sm:w-[180px] h-9">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="name">Name</SelectItem>
              <SelectItem value="role">Role</SelectItem>
              <SelectItem value="shift">Shift</SelectItem>
            </SelectContent>
          </Select>

          {/* Sort Direction */}
          <Button
            variant="outline"
            size="sm"
            className="h-9"
            onClick={() => {
              const newDirection: SortDirection = sortConfig.direction === "asc" ? "desc" : "asc";
              const newConfig = { ...sortConfig, direction: newDirection };
              setSortConfig(newConfig);
              updateUrlParams(searchQuery, newConfig);
            }}
          >
            {sortConfig.direction === "asc" ? (
              <ArrowUp className="h-4 w-4 mr-2" />
            ) : (
              <ArrowDown className="h-4 w-4 mr-2" />
            )}
            {sortConfig.direction === "asc" ? "Ascending" : "Descending"}
          </Button>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters} className="h-9">
              Clear filters
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Salespeople Rankings - Top Performers */}
      {rankedSalespeople.length > 0 && (
        <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)] border-brand-green/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Trophy className="h-4 w-4 text-brand-green-deep" />
              Performance Rankings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {rankedSalespeople.slice(0, 6).map((sp) => {
                const rank = sp.rank;
                const score = sp.analytics?.avg_overall_score || 0;
                const conversion = sp.analytics?.conversion_rate || 0;
                const conversations = sp.analytics?.total_conversations || 0;

                return (
                  <Link
                    key={sp.id}
                    href={`/salesperson/${sp.id}`}
                    className="group flex items-start gap-3 rounded-lg border border-border p-3 hover:bg-accent/50 transition-colors"
                  >
                    <div
                      className={cn(
                        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold",
                        rank === 1 && "bg-brand-green text-white",
                        rank === 2 && "bg-slate-400 text-white",
                        rank === 3 && "bg-amber-600 text-white",
                        rank > 3 && "bg-muted text-steel",
                      )}
                    >
                      {rank}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-medium text-ink truncate group-hover:text-primary">
                          {sp.name}
                        </p>
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-xs font-mono",
                            score >= 80
                              ? "border-brand-green/30 text-brand-green-deep bg-brand-green-soft"
                              : score >= 60
                                ? "border-amber-200 text-amber-700 bg-amber-50"
                                : "border-destructive/20 text-destructive bg-destructive/10",
                          )}
                        >
                          {score.toFixed(0)}
                        </Badge>
                      </div>
                      <div className="mt-1 flex items-center gap-3 text-xs text-steel">
                        <span className="flex items-center gap-1">
                          <Target className="h-3 w-3" />
                          {conversion.toFixed(0)}%
                        </span>
                        <span>{conversations} convs</span>
                      </div>
                    </div>
                    <ChevronRight className="h-4 w-4 text-steel shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </Link>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Skill Comparison Chart */}
      {rankedSalespeople.length >= 2 && (
        <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-steel" />
              Skill Comparison
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={rankedSalespeople.slice(0, 5).map((sp) => ({
                    name: sp.name.split(" ")[0], // First name only
                    greeting: sp.analytics?.avg_greeting_score || 0,
                    discovery: sp.analytics?.avg_discovery_score || 0,
                    product: sp.analytics?.avg_product_knowledge_score || 0,
                    objection: sp.analytics?.avg_objection_handling_score || 0,
                    closing: sp.analytics?.avg_closing_score || 0,
                  }))}
                  margin={{ top: 10, right: 30, left: 20, bottom: 5 }}
                >
                  <XAxis dataKey="name" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "oklch(1 0 0)",
                      border: "1px solid oklch(0.92 0 0)",
                      borderRadius: "6px",
                    }}
                  />
                  <Bar dataKey="greeting" stackId="a" fill="oklch(0.75 0.18 165)" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="discovery" stackId="a" fill="oklch(0.65 0.15 260)" />
                  <Bar dataKey="product" stackId="a" fill="oklch(0.7 0.12 55)" />
                  <Bar dataKey="objection" stackId="a" fill="oklch(0.6 0.18 25)" />
                  <Bar dataKey="closing" stackId="a" fill="oklch(0.65 0.16 310)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 flex flex-wrap gap-4 text-xs">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-sm" style={{ backgroundColor: "oklch(0.75 0.18 165)" }} />
                <span className="text-steel">Greeting</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-sm" style={{ backgroundColor: "oklch(0.65 0.15 260)" }} />
                <span className="text-steel">Discovery</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-sm" style={{ backgroundColor: "oklch(0.7 0.12 55)" }} />
                <span className="text-steel">Product Knowledge</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-sm" style={{ backgroundColor: "oklch(0.6 0.18 25)" }} />
                <span className="text-steel">Objection Handling</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-sm" style={{ backgroundColor: "oklch(0.65 0.16 310)" }} />
                <span className="text-steel">Closing</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Top Objections */}
      {analytics?.top_objections && analytics.top_objections.length > 0 && (
        <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Top Customer Objections
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {analytics.top_objections.slice(0, 5).map((obj, idx) => {
                const maxCount = analytics.top_objections[0]?.count || 1;
                const percentage = (obj.count / maxCount) * 100;

                return (
                  <div key={idx} className="group">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-ink">{obj.objection}</span>
                      <span className="text-xs font-mono text-steel">{obj.count} times</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-amber-500 to-amber-600 transition-all"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Salespeople Table */}
      <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-4 w-4 text-steel" />
            All Salespeople
            {hasActiveFilters && filteredAndSorted.length > 0 && (
              <span className="text-xs font-normal text-steel ml-2">
                ({filteredAndSorted.length} of {salespeople?.length})
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3 py-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4 px-2">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-4 w-12" />
                  <Skeleton className="h-4 w-40" />
                </div>
              ))}
            </div>
          ) : filteredAndSorted.length > 0 ? (
            <div className="overflow-x-auto -mx-6 sm:mx-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead
                      className="text-[11px] font-semibold uppercase tracking-wider text-steel cursor-pointer hover:text-ink transition-colors select-none"
                      onClick={() => handleSort("name")}
                    >
                      <div className="flex items-center gap-1.5">
                        Name
                        <SortIcon field="name" config={sortConfig} />
                      </div>
                    </TableHead>
                    <TableHead
                      className="text-[11px] font-semibold uppercase tracking-wider text-steel cursor-pointer hover:text-ink transition-colors select-none"
                      onClick={() => handleSort("role")}
                    >
                      <div className="flex items-center gap-1.5">
                        Role
                        <SortIcon field="role" config={sortConfig} />
                      </div>
                    </TableHead>
                    <TableHead
                      className="text-[11px] font-semibold uppercase tracking-wider text-steel cursor-pointer hover:text-ink transition-colors select-none"
                      onClick={() => handleSort("shift")}
                    >
                      <div className="flex items-center gap-1.5">
                        Shift
                        <SortIcon field="shift" config={sortConfig} />
                      </div>
                    </TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Device #</TableHead>
                    <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Email</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredAndSorted.map((sp) => (
                    <TableRow 
                      key={sp.id} 
                      className="group cursor-pointer hover:bg-accent/50 transition-colors"
                      onClick={() => window.location.href = `/salesperson/${sp.id}`}
                    >
                      <TableCell>
                        <Link
                          href={`/salesperson/${sp.id}`}
                          className="font-medium text-primary hover:underline"
                        >
                          {sp.name}
                        </Link>
                      </TableCell>
                      <TableCell className="text-steel">{sp.role || "—"}</TableCell>
                      <TableCell className="text-steel">{sp.shift || "—"}</TableCell>
                      <TableCell className="text-steel font-mono text-sm">{sp.device_number || "—"}</TableCell>
                      <TableCell className="text-steel">{sp.email || "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Inbox className="h-10 w-10 text-stone/40 mb-3" />
              <p className="text-sm font-medium text-steel">
                {searchQuery ? "No matching salespeople found" : "No salespeople found"}
              </p>
              <p className="text-xs text-stone mt-1">
                {searchQuery ? "Try adjusting your search" : "Add team members to start tracking performance."}
              </p>
              {hasActiveFilters && (
                <Button variant="outline" size="sm" onClick={clearFilters} className="mt-4">
                  Clear all filters
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
