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
    if (!user) return;

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
      default:
        router.replace("/recordings");
    }
  }, [user, router]);

  return (
    <div className="flex h-screen items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  );
}
