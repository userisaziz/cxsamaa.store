"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { Salesperson } from "@samaa/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Users } from "lucide-react";

export default function SalespeoplePage() {
  const { data: salespeople, isLoading } = useQuery({
    queryKey: ["salespeople"],
    queryFn: () => api.get<Salesperson[]>("/salespeople"),
  });

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Salespeople</h1>
        <p className="text-sm text-steel">Manage sales team members</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            All Salespeople
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
                  <TableHead>Role</TableHead>
                  <TableHead>Shift</TableHead>
                  <TableHead>Device #</TableHead>
                  <TableHead>Email</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {salespeople?.map((sp) => (
                  <TableRow key={sp.id}>
                    <TableCell>
                      <Link
                        href={`/salesperson/${sp.id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {sp.name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{sp.role || "—"}</TableCell>
                    <TableCell className="text-muted-foreground">{sp.shift || "—"}</TableCell>
                    <TableCell className="text-muted-foreground">{sp.device_number || "—"}</TableCell>
                    <TableCell className="text-muted-foreground">{sp.email || "—"}</TableCell>
                  </TableRow>
                )) ?? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground py-12">
                      No salespeople found
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
