"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AuthGuard } from "@/components/auth-guard";
import { OperationsSidebar } from "@/components/layout/operations-sidebar";
import { MobileSidebar } from "@/components/layout/mobile-sidebar";
import { useAuthStore } from "@/store/auth";

export default function OperationsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user, hydrate } = useAuthStore();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!user) return;
    // Only OPERATOR and SUPER_ADMIN can access operations
    if (user.role !== "OPERATOR" && user.role !== "SUPER_ADMIN") {
      router.replace("/");
    }
  }, [user, router]);

  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden">
        {/* Desktop sidebar (lg+) */}
        <aside className="hidden lg:flex lg:shrink-0 lg:h-full">
          <OperationsSidebar />
        </aside>

        {/* Mobile: top bar + drawer */}
        <div className="flex flex-1 flex-col lg:hidden">
          <MobileSidebar>
            <OperationsSidebar />
          </MobileSidebar>
          <main className="flex-1 overflow-y-auto bg-surface-soft">
            {children}
          </main>
        </div>

        {/* Desktop main content */}
        <main className="hidden flex-1 overflow-y-auto bg-surface-soft lg:block">
          {children}
        </main>
      </div>
    </AuthGuard>
  );
}
