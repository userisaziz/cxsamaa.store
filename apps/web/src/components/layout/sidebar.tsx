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
  MessageSquare,
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
    label: "Conversations",
    href: "/conversations",
    icon: MessageSquare,
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

function getInitials(name?: string): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return parts[0].slice(0, 2).toUpperCase();
}

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
      <div className="flex items-center gap-3 px-6 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary">
          <Headphones className="h-4.5 w-4.5 text-primary-foreground" />
        </div>
        <div>
          <span className="text-lg font-semibold tracking-tight text-ink">SAMAA</span>
          <p className="text-[11px] font-medium text-steel -mt-0.5">Audio Intelligence</p>
        </div>
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
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
                  isActive
                    ? "bg-brand-green-soft text-ink font-medium"
                    : "text-steel font-normal hover:bg-secondary/70 hover:text-charcoal",
                )}
              >
                <item.icon className={cn("h-4 w-4", isActive ? "text-brand-green-deep" : "")} />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>

      <Separator />

      {/* User section */}
      <div className="p-4">
        <div className="mb-3 flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-secondary text-sm font-semibold text-ink">
            {getInitials(user?.full_name)}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-ink truncate">{user?.full_name}</p>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-steel truncate">
              {user?.role}
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="w-full rounded-lg"
          onClick={handleLogout}
        >
          <LogOut className="mr-2 h-4 w-4" />
          Sign Out
        </Button>
      </div>
    </aside>
  );
}
