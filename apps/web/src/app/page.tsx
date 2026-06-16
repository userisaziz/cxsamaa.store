"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";

export default function HomePage() {
  const router = useRouter();
  const { user, hydrate } = useAuthStore();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!user) {
      router.replace("/login");
      return;
    }

    // Role-based redirect
    switch (user.role) {
      case "SUPER_ADMIN":
      case "BRAND_ADMIN":
        router.replace("/brand");
        break;
      case "STORE_MANAGER":
        router.replace(`/store/${user.store_id}`);
        break;
      case "SALESPERSON":
        router.replace("/recordings");
        break;
      case "OPERATOR":
        router.replace("/operations");
        break;
      default:
        router.replace("/recordings");
    }
  }, [user, router]);

  return (
    <div className="flex h-screen items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-green border-t-transparent" />
        <p className="text-sm font-medium tracking-wide text-steel">CXSAMAA</p>
      </div>
    </div>
  );
}
