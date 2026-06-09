"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { api, ApiError } from "@/lib/api-client";
import type { LoginResponse } from "@samaa/shared";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Headphones } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await api.post<LoginResponse>("/auth/login", { email, password });
      login(data);
      router.push("/");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("An unexpected error occurred");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="flex min-h-screen items-center justify-center p-4"
      style={{
        background: "linear-gradient(180deg, var(--color-hero-sky-from) 0%, var(--color-hero-sky-to) 40%, oklch(1 0 0) 100%)",
      }}
    >
      <Card className="w-full max-w-md border border-border shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)] rounded-xl overflow-hidden">
        {/* Brand accent top bar */}
        <div className="h-1 w-full bg-brand-green" />
        <CardHeader className="text-center pb-2 pt-8">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-primary shadow-sm">
            <Headphones className="h-7 w-7 text-primary-foreground" />
          </div>
          <CardTitle className="text-[28px] font-semibold tracking-tight text-ink leading-tight">SAMAA</CardTitle>
          <CardDescription className="text-sm text-steel mt-1">Sales Audio Management & AI Analysis</CardDescription>
        </CardHeader>
        <CardContent className="pt-4 pb-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="rounded-lg bg-destructive/8 p-3 text-sm text-destructive border border-destructive/20">
                {error}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm font-medium text-charcoal">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="admin@samaa.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm font-medium text-charcoal">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full" size="lg" disabled={loading}>
              {loading ? "Signing in..." : "Sign In"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
