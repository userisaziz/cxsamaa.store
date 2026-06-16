"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { api, ApiError } from "@/lib/api-client";
import type { LoginResponse } from "@samaa/shared";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Headphones, Eye, EyeOff, Loader2 } from "lucide-react";
import { toast } from "sonner";

/* ── Animated waveform bars for the brand panel ── */
function WaveformVisual() {
  const bars = [
    { delay: "0s", height: "35%" },
    { delay: "0.15s", height: "55%" },
    { delay: "0.3s", height: "75%" },
    { delay: "0.1s", height: "45%" },
    { delay: "0.4s", height: "85%" },
    { delay: "0.25s", height: "60%" },
    { delay: "0.05s", height: "40%" },
    { delay: "0.35s", height: "70%" },
    { delay: "0.2s", height: "50%" },
    { delay: "0.45s", height: "65%" },
    { delay: "0.15s", height: "80%" },
    { delay: "0.3s", height: "45%" },
    { delay: "0.5s", height: "55%" },
    { delay: "0.1s", height: "70%" },
    { delay: "0.4s", height: "40%" },
    { delay: "0.2s", height: "60%" },
    { delay: "0.35s", height: "75%" },
    { delay: "0.05s", height: "50%" },
    { delay: "0.25s", height: "65%" },
    { delay: "0.45s", height: "45%" },
  ];

  return (
    <div className="flex items-center justify-center gap-[3px] h-16" aria-hidden="true">
      {bars.map((bar, i) => (
        <div
          key={i}
          className="w-[3px] rounded-full bg-brand-green/60 animate-waveform"
          style={{
            height: bar.height,
            animationDelay: bar.delay,
          }}
        />
      ))}
    </div>
  );
}

/* ── Feature pill for the brand panel ── */
function FeaturePill({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2.5 rounded-lg bg-white/[0.06] border border-white/[0.08] px-3.5 py-2.5">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-brand-green/15 text-brand-green">
        {icon}
      </span>
      <span className="text-[13px] leading-snug text-on-dark/80">{children}</span>
    </div>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    e.stopPropagation();
    setError("");
    setLoading(true);

    try {
      const data = await api.post<LoginResponse>("/auth/login", { email, password });
      login(data);
      toast.success("Welcome back!", {
        description: "You have successfully signed in.",
      });
      router.push("/");
    } catch (err) {
      console.error("Login error:", err);
      if (err instanceof ApiError) {
        const message = err.detail || "Invalid email or password";
        setError(message);
        toast.error("Sign in failed", {
          description: message,
        });
      } else if (err instanceof Error) {
        const message = err.message || "An unexpected error occurred";
        setError(message);
        toast.error("Sign in failed", {
          description: message,
        });
      } else {
        const message = "An unexpected error occurred";
        setError(message);
        toast.error("Sign in failed", {
          description: message,
        });
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* ── Left brand panel (hidden on mobile) ── */}
      <div
        className="hidden lg:flex lg:w-[480px] xl:w-[540px] flex-col justify-between relative overflow-hidden"
        style={{
          background: "linear-gradient(160deg, oklch(0.22 0.04 180) 0%, oklch(0.15 0 0) 60%, oklch(0.18 0.03 165) 100%)",
        }}
      >
        {/* Subtle grid pattern overlay */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />

        {/* Glow accent */}
        <div
          className="absolute top-1/3 -left-20 w-60 h-60 rounded-full opacity-20 blur-[100px]"
          style={{ background: "oklch(0.75 0.18 165)" }}
        />

        <div className="relative z-10 flex flex-col h-full justify-between p-10 xl:p-12">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-green/15 border border-brand-green/20">
              <Headphones className="h-5 w-5 text-brand-green" />
            </div>
            <span className="text-lg font-semibold tracking-tight text-on-dark">CXSAMAA</span>
          </div>

          {/* Center content */}
          <div className="space-y-8">
            <div className="space-y-3">
              <h1 className="text-[32px] xl:text-[36px] font-semibold tracking-tight text-on-dark leading-[1.15]">
                Retail Audio
                <br />
                Intelligence
              </h1>
              <p className="text-[15px] leading-relaxed text-on-dark-muted max-w-[360px]">
                Transform every sales conversation into actionable coaching insights with AI-powered audio analysis.
              </p>
            </div>

            {/* Waveform visualization */}
            <WaveformVisual />

            {/* Feature pills */}
            <div className="space-y-2.5">
              <FeaturePill icon={<svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M12 2v20M2 12h20" /></svg>}>
                Real-time speech-to-text transcription
              </FeaturePill>
              <FeaturePill icon={<svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>}>
                Multi-speaker diarization &amp; scoring
              </FeaturePill>
              <FeaturePill icon={<svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M3 3v18h18" /><path d="m19 9-5 5-4-4-3 3" /></svg>}>
                Performance dashboards at every level
              </FeaturePill>
            </div>
          </div>

          {/* Footer */}
          <p className="text-[12px] text-on-dark-muted/50">
            &copy; {new Date().getFullYear()} CXSAMAA. All rights reserved.
          </p>
        </div>
      </div>

      {/* ── Right form panel ── */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 sm:px-12 lg:px-16 bg-background">
        <div className="w-full max-w-[400px] space-y-8">
          {/* Mobile logo (visible below lg) */}
          <div className="lg:hidden flex flex-col items-center gap-3 mb-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
              <Headphones className="h-6 w-6 text-primary-foreground" />
            </div>
            <div className="text-center">
              <h2 className="text-xl font-semibold tracking-tight text-ink">CXSAMAA</h2>
              <p className="text-[13px] text-steel mt-0.5">Sales Audio Management &amp; AI Analysis</p>
            </div>
          </div>

          {/* Form header */}
          <div className="space-y-1.5">
            <h2 className="text-[22px] font-semibold tracking-tight text-ink">Welcome back</h2>
            <p className="text-sm text-steel">Sign in to your account to continue</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Error message */}
            {error && (
              <div className="flex items-start gap-2.5 rounded-lg bg-destructive/[0.06] border border-destructive/15 px-4 py-3 text-[13px] leading-snug text-destructive">
                <svg className="h-4 w-4 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <span>{error}</span>
              </div>
            )}

            {/* Email field */}
            <div className="space-y-2">
              <Label htmlFor="email" className="text-[13px] font-medium text-charcoal">
                Email address
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
                autoComplete="email"
                className="h-11"
              />
            </div>

            {/* Password field */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-[13px] font-medium text-charcoal">
                  Password
                </Label>
              </div>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="h-11 pr-11"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-1 top-1/2 -translate-y-1/2 flex h-8 w-8 items-center justify-center rounded-md text-steel hover:text-charcoal hover:bg-secondary transition-colors"
                  tabIndex={-1}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Submit */}
            <Button
              type="submit"
              className="w-full h-11 text-[14px] font-medium mt-2"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign in"
              )}
            </Button>
          </form>

          {/* Help text */}
          <p className="text-center text-[13px] text-stone">
            Contact your administrator if you need access
          </p>
        </div>
      </div>
    </div>
  );
}
