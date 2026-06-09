"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { Store } from "@samaa/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Store as StoreIcon } from "lucide-react";

export default function StoresPage() {
  const { data: stores, isLoading } = useQuery({
    queryKey: ["stores"],
    queryFn: () => api.get<Store[]>("/stores"),
  });

  return (
    <div className="space-y-8 p-8">
      <div>
        <h1 className="text-[28px] font-semibold tracking-tight text-ink leading-tight">Stores</h1>
        <p className="mt-1 text-sm text-steel">Manage retail locations</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <StoreIcon className="h-4 w-4" />
            All Stores
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stores?.map((store) => (
                  <TableRow key={store.id}>
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
                    <TableCell className="text-steel">
                      {new Date(store.created_at).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                )) ?? (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center text-steel py-12">
                      No stores found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
