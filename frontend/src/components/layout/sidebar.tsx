"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  Play, 
  FileStack, 
  ChevronLeft, 
  ChevronRight,
  FileSearch
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Runs", href: "/runs", icon: Play },
  { label: "Documents", href: "/documents", icon: FileStack },
];

interface SidebarProps {
  defaultCollapsed?: boolean;
}

export function Sidebar({ defaultCollapsed = false }: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = React.useState(defaultCollapsed);
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        "relative flex flex-col h-screen bg-white border-r border-border sidebar-transition",
        isCollapsed ? "w-16" : "w-60"
      )}
    >
      {/* Logo Area */}
      <div className={cn(
        "flex items-center h-16 px-4 border-b border-border",
        isCollapsed ? "justify-center" : "justify-start"
      )}>
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-primary">
            <FileSearch className="h-4 w-4 text-white" />
          </div>
          {!isCollapsed && (
            <span className="font-semibold text-foreground text-lg">
              DrawDoc
            </span>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4">
        <ul className="space-y-1 px-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "relative flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors",
                    isCollapsed && "justify-center px-0",
                    isActive
                      ? "bg-primary-light text-primary-dark font-medium"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )}
                >
                  {/* Active indicator */}
                  {isActive && (
                    <span className="nav-indicator" />
                  )}
                  
                  <Icon className={cn(
                    "h-5 w-5 shrink-0",
                    isActive ? "text-primary" : "text-muted-foreground"
                  )} />
                  
                  {!isCollapsed && (
                    <span className="text-sm">{item.label}</span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Collapse Toggle */}
      <div className="p-4 border-t border-border">
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            "h-8 w-8",
            isCollapsed ? "mx-auto" : "ml-auto"
          )}
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>
    </aside>
  );
}

