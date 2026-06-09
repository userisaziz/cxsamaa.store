"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import {
  LayoutDashboard,
  Store,
  Users,
  Mic,
  LogOut,
  Headphones,
  GraduationCap,
  Search,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  roles?: string[];
}

const navItems: NavItem[] = [
  {
    label: "Brand Dashboard",
    href: "/brand",
    icon: LayoutDashboard,
    roles: ["SUPER_ADMIN", "BRAND_ADMIN"],
  },
  {
    label: "Stores",
    href: "/stores",
    icon: Store,
    roles: ["SUPER_ADMIN", "BRAND_ADMIN"],
  },
  {
    label: "Store Dashboard",
    href: "/store",
    icon: Store,
    roles: ["STORE_MANAGER"],
  },
  {
    label: "Salespeople",
    href: "/salespeople",
    icon: Users,
  },
  {
    label: "My Dashboard",
    href: "/salesperson",
    icon: LayoutDashboard,
    roles: ["SALESPERSON"],
  },
  {
    label: "Recordings",
    href: "/recordings",
    icon: Mic,
  },
  {
    label: "Search",
    href: "/search",
    icon: Search,
  },
  {
    label: "Coaching",
    href: "/coaching",
    icon: GraduationCap,
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const filteredNav = navItems.filter(
    (item) => !item.roles || (user && item.roles.includes(user.role)),
  );

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <aside className="flex h-full w-64 flex-col border-r border-border bg-card">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-6 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary">
          <Headphones className="h-4.5 w-4.5 text-primary-foreground" />
        </div>
        <span className="text-lg font-semibold tracking-tight text-ink">SAMAA</span>
      </div>

      <Separator />

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4">
        <p className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-widest text-steel">
          Navigation
        </p>
        <div className="space-y-0.5">
          {filteredNav.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-brand-green-soft text-ink border-l-2 border-brand-green"
                    : "text-steel hover:bg-secondary/70 hover:text-charcoal border-l-2 border-transparent",
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>

      <Separator />

      {/* User section */}
      <div className="p-4">
        <div className="mb-3 space-y-0.5">
          <p className="text-sm font-medium text-ink">{user?.full_name}</p>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-steel">{user?.role}</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="w-full rounded-md"
          onClick={handleLogout}
        >
          <LogOut className="mr-2 h-4 w-4" />
          Sign Out
        </Button>
      </div>
    </aside>
  );
}
