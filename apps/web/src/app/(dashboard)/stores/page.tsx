"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { Store } from "@samaa/shared";
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
import { Store as StoreIcon, Inbox } from "lucide-react";

export default function StoresPage() {
  const { data: stores, isLoading } = useQuery({
    queryKey: ["stores"],
    queryFn: () => api.get<Store[]>("/stores"),
  });

  return (
    <div className="space-y-6 lg:space-y-8 p-4 sm:p-6 lg:p-8">
      {/* Page Header */}
      <div className="border-b border-border pb-4 sm:pb-6">
        <h1 className="text-[22px] sm:text-[28px] font-semibold tracking-tight text-ink leading-tight">Stores</h1>
        <p className="mt-1 text-sm text-steel">Manage retail locations</p>
      </div>

      <Card className="shadow-[0_1px_3px_rgba(0,0,0,0.04),0_1px_2px_rgba(0,0,0,0.06)]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <StoreIcon className="h-4 w-4 text-steel" />
            All Stores
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3 py-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4 px-2">
                  <Skeleton className="h-4 w-36" />
                  <Skeleton className="h-4 w-48" />
                  <Skeleton className="h-4 w-24" />
                </div>
              ))}
            </div>
          ) : stores && stores.length > 0 ? (
            <div className="overflow-x-auto -mx-6 sm:mx-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Name</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Location</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-steel">Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stores.map((store) => (
                  <TableRow 
                    key={store.id} 
                    className="group cursor-pointer hover:bg-accent/50 transition-colors"
                    onClick={() => window.location.href = `/store/${store.id}`}
                  >
                    <TableCell>
                      <Link
                        href={`/store/${store.id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {store.name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-steel">
                      {store.location || "—"}
                    </TableCell>
                    <TableCell className="text-steel font-mono text-[13px]">
                      {new Date(store.created_at).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Inbox className="h-10 w-10 text-stone/40 mb-3" />
              <p className="text-sm font-medium text-steel">No stores configured</p>
              <p className="text-xs text-stone mt-1">Add retail locations to start tracking store performance.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
