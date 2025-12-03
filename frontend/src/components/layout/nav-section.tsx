"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface NavSubItem {
  label: string;
  href: string;
}

interface NavSectionProps {
  label: string;
  href: string;
  icon: React.ElementType;
  subItems?: NavSubItem[];
  isCollapsed?: boolean;
  disabled?: boolean;
  badge?: string;
}

export function NavSection({ 
  label, 
  href, 
  icon: Icon, 
  subItems, 
  isCollapsed,
  disabled,
  badge,
}: NavSectionProps) {
  const pathname = usePathname();
  const [isExpanded, setIsExpanded] = React.useState(false);
  
  // Check if current path matches this section or any sub-items
  const isActive = pathname === href || pathname.startsWith(`${href}/`);
  const hasSubItems = subItems && subItems.length > 0;
  
  // Auto-expand if a sub-item is active
  React.useEffect(() => {
    if (isActive && hasSubItems && !isCollapsed) {
      setIsExpanded(true);
    }
  }, [isActive, hasSubItems, isCollapsed]);

  if (disabled) {
    return (
      <div
        className={cn(
          "relative flex items-center gap-3 px-3 py-2.5 rounded-lg opacity-50 cursor-not-allowed",
          isCollapsed && "justify-center px-0"
        )}
      >
        <Icon className="h-5 w-5 shrink-0 text-muted-foreground" />
        {!isCollapsed && (
          <>
            <span className="text-sm text-muted-foreground">{label}</span>
            {badge && (
              <span className="ml-auto text-xs bg-muted text-muted-foreground px-1.5 py-0.5 rounded">
                {badge}
              </span>
            )}
          </>
        )}
      </div>
    );
  }

  // Simple link without sub-items
  if (!hasSubItems) {
    return (
      <Link
        href={href}
        className={cn(
          "relative flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors",
          isCollapsed && "justify-center px-0",
          isActive
            ? "bg-primary-light text-primary-dark font-medium"
            : "text-muted-foreground hover:bg-muted hover:text-foreground"
        )}
      >
        {isActive && <span className="nav-indicator" />}
        <Icon className={cn(
          "h-5 w-5 shrink-0",
          isActive ? "text-primary" : "text-muted-foreground"
        )} />
        {!isCollapsed && <span className="text-sm">{label}</span>}
      </Link>
    );
  }

  // Section with sub-items
  return (
    <div>
      {/* Main section link/button */}
      <button
        onClick={() => !isCollapsed && setIsExpanded(!isExpanded)}
        className={cn(
          "w-full relative flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors",
          isCollapsed && "justify-center px-0",
          isActive
            ? "bg-primary-light text-primary-dark font-medium"
            : "text-muted-foreground hover:bg-muted hover:text-foreground"
        )}
      >
        {isActive && <span className="nav-indicator" />}
        <Icon className={cn(
          "h-5 w-5 shrink-0",
          isActive ? "text-primary" : "text-muted-foreground"
        )} />
        {!isCollapsed && (
          <>
            <span className="text-sm flex-1 text-left">{label}</span>
            <ChevronDown 
              className={cn(
                "h-4 w-4 transition-transform",
                isExpanded && "rotate-180"
              )} 
            />
          </>
        )}
      </button>

      {/* Sub-items */}
      {!isCollapsed && isExpanded && (
        <div className="mt-1 ml-4 pl-4 border-l border-border space-y-1">
          {subItems.map((item) => {
            const subIsActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "block px-3 py-2 rounded-lg text-sm transition-colors",
                  subIsActive
                    ? "bg-primary-light text-primary-dark font-medium"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

