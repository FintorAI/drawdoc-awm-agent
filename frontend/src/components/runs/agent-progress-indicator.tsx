"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { AgentStatusValue } from "@/lib/api";

// =============================================================================
// TYPES
// =============================================================================

interface AgentProgressIndicatorProps {
  agents: {
    preparation: AgentStatusValue;
    drawcore?: AgentStatusValue;
    verification: AgentStatusValue;
    orderdocs: AgentStatusValue;
  };
  /** Show agent labels on hover */
  showTooltips?: boolean;
  /** Size variant */
  size?: "sm" | "md";
  className?: string;
}

// =============================================================================
// STATUS DOT COMPONENT
// =============================================================================

interface StatusDotProps {
  status: AgentStatusValue;
  label: string;
  size: "sm" | "md";
}

function StatusDot({ status, label, size }: StatusDotProps) {
  const sizeClasses = {
    sm: "h-2.5 w-2.5",
    md: "h-3 w-3",
  };

  const statusConfig: Record<string, { icon: string; className: string; title: string }> = {
    success: {
      icon: "✓",
      className: "bg-emerald-500 text-white",
      title: `${label}: Completed`,
    },
    running: {
      icon: "●",
      className: "bg-blue-500 text-white animate-pulse",
      title: `${label}: Running`,
    },
    failed: {
      icon: "✗",
      className: "bg-red-500 text-white",
      title: `${label}: Failed`,
    },
    pending: {
      icon: "○",
      className: "bg-slate-200 text-slate-400 border border-slate-300",
      title: `${label}: Pending`,
    },
    pending_review: {
      icon: "⏸",
      className: "bg-amber-500 text-white animate-pulse",
      title: `${label}: Pending Review`,
    },
    blocked: {
      icon: "⚠",
      className: "bg-orange-500 text-white",
      title: `${label}: Blocked`,
    },
  };

  // Fallback to pending if status not found
  const config = statusConfig[status] || statusConfig.pending;

  return (
    <div
      className={cn(
        "rounded-full flex items-center justify-center text-[8px] font-bold leading-none",
        sizeClasses[size],
        config.className
      )}
      title={config.title}
      aria-label={config.title}
    >
      {status === "success" && (
        <svg className="h-1.5 w-1.5" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M2 6l3 3 5-6" />
        </svg>
      )}
      {status === "failed" && (
        <svg className="h-1.5 w-1.5" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 3l6 6M9 3l-6 6" />
        </svg>
      )}
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

/**
 * Agent Progress Indicator
 * 
 * Shows 3 mini indicators representing the status of each agent:
 * - Preparation
 * - Verification  
 * - OrderDocs
 * 
 * Status icons:
 * - ✓ (checkmark) = success
 * - ● (filled, pulsing) = running
 * - ✗ (x) = failed
 * - ○ (empty circle) = pending
 */
export function AgentProgressIndicator({
  agents,
  size = "sm",
  className,
}: AgentProgressIndicatorProps) {
  return (
    <div className={cn("flex items-center gap-1", className)}>
      <StatusDot status={agents.preparation || "pending"} label="Preparation" size={size} />
      <StatusDot status={agents.drawcore || "pending"} label="Drawcore" size={size} />
      <StatusDot status={agents.verification || "pending"} label="Verification" size={size} />
      <StatusDot status={agents.orderdocs || "pending"} label="OrderDocs" size={size} />
    </div>
  );
}

// =============================================================================
// EXPANDED VARIANT (with labels)
// =============================================================================

interface AgentProgressExpandedProps {
  agents: {
    preparation: AgentStatusValue;
    drawcore?: AgentStatusValue;
    verification: AgentStatusValue;
    orderdocs: AgentStatusValue;
  };
  className?: string;
}

/**
 * Expanded agent progress indicator with labels
 * Good for detail views where more space is available
 */
export function AgentProgressExpanded({ agents, className }: AgentProgressExpandedProps) {
  const agentList = [
    { key: 'preparation', label: 'Prep', status: agents.preparation || "pending" },
    { key: 'drawcore', label: 'Draw', status: agents.drawcore || "pending" },
    { key: 'verification', label: 'Verify', status: agents.verification || "pending" },
    { key: 'orderdocs', label: 'Order', status: agents.orderdocs || "pending" },
  ] as const;

  return (
    <div className={cn("flex items-center gap-3", className)}>
      {agentList.map((agent, idx) => (
        <React.Fragment key={agent.key}>
          <div className="flex items-center gap-1.5">
            <StatusDot status={agent.status} label={agent.label} size="md" />
            <span className="text-xs text-muted-foreground">{agent.label}</span>
          </div>
          {idx < agentList.length - 1 && (
            <div className="h-0.5 w-4 bg-slate-200 rounded-full" />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

