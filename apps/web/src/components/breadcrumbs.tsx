import Link from "next/link";
import { ChevronRight, Home } from "lucide-react";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
}

export function Breadcrumbs({ items }: BreadcrumbsProps) {
  return (
    <nav className="flex items-center gap-1 text-sm text-steel">
      <Link
        href="/brand"
        className="flex items-center gap-1 hover:text-ink transition-colors"
      >
        <Home className="h-3.5 w-3.5" />
        <span>Brand</span>
      </Link>
      {items.map((item, index) => (
        <span key={index} className="flex items-center gap-1">
          <ChevronRight className="h-3.5 w-3.5 text-steel/60" />
          {item.href ? (
            <Link
              href={item.href}
              className="hover:text-ink transition-colors"
            >
              {item.label}
            </Link>
          ) : (
            <span className="font-medium text-ink">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
