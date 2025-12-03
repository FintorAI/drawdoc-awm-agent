"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  FileStack, 
  ChevronLeft, 
  ChevronRight,
  FileSearch,
  Shield,
  FileText,
  Mail,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { NavSection } from "./nav-section";

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
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-primary">
            <FileSearch className="h-4 w-4 text-white" />
          </div>
          {!isCollapsed && (
            <span className="font-semibold text-foreground text-lg">
              AWM Pilot
            </span>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        <ul className="space-y-1 px-2">
          {/* Dashboard (Agent Hub) */}
          <li>
            <NavSection
              label="Dashboard"
              href="/dashboard"
              icon={LayoutDashboard}
              isCollapsed={isCollapsed}
            />
          </li>

          {/* Disclosure Agent */}
          <li>
            <NavSection
              label="Disclosure"
              href="/disclosure"
              icon={Shield}
              isCollapsed={isCollapsed}
              subItems={[
                { label: "Overview", href: "/disclosure" },
                { label: "Runs", href: "/disclosure/runs" },
              ]}
            />
          </li>

          {/* DrawDocs Agent */}
          <li>
            <NavSection
              label="DrawDocs"
              href="/drawdocs"
              icon={FileText}
              isCollapsed={isCollapsed}
              subItems={[
                { label: "Overview", href: "/drawdocs" },
                { label: "Runs", href: "/drawdocs/runs" },
              ]}
            />
          </li>

          {/* LOA Agent */}
          <li>
            <NavSection
              label="LOA"
              href="/loa"
              icon={Mail}
              isCollapsed={isCollapsed}
              subItems={[
                { label: "Overview", href: "/loa" },
                { label: "Runs", href: "/loa/runs" },
              ]}
            />
          </li>

          {/* Documents */}
          <li>
            <NavSection
              label="Documents"
              href="/documents"
              icon={FileStack}
              isCollapsed={isCollapsed}
            />
          </li>
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
