"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { AgentStatusValue } from "@/lib/api";
import { AGENT_TYPE_SUB_AGENTS } from "@/types/agents";
import type { AgentType as PipelineType } from "@/types/agents";

// =============================================================================
// TYPES
// =============================================================================

interface AgentProgressIndicatorProps {
  agents: Record<string, AgentStatusValue>;
  agentType?: PipelineType; // Optional: for agent-specific rendering
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
      {status === "blocked" && (
        <span className="text-[10px] font-extrabold">!</span>
      )}
      {status === "pending_review" && (
        <span className="text-[10px] font-extrabold">⏸</span>
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
 * Shows mini indicators representing the status of each sub-agent
 * Dynamically renders based on agent type (drawdocs, disclosure, loa)
 * 
 * Status icons:
 * - ✓ (checkmark) = success
 * - ● (filled, pulsing) = running
 * - ✗ (x) = failed
 * - ! (exclamation) = blocked
 * - ○ (empty circle) = pending
 * - ⏸ (pause) = pending_review
 */
export function AgentProgressIndicator({
  agents,
  agentType = "drawdocs", // default to drawdocs for backwards compatibility
  size = "sm",
  className,
}: AgentProgressIndicatorProps) {
  // Get sub-agents for the specific agent type
  const subAgents = AGENT_TYPE_SUB_AGENTS[agentType] || [];
  
  return (
    <div className={cn("flex items-center gap-1", className)}>
      {subAgents.map((subAgent) => (
        <StatusDot 
          key={subAgent.id}
          status={agents[subAgent.id] || "pending"} 
          label={subAgent.name} 
          size={size} 
        />
      ))}
    </div>
  );
}

// =============================================================================
// EXPANDED VARIANT (with labels)
// =============================================================================

interface AgentProgressExpandedProps {
  agents: Record<string, AgentStatusValue>;
  agentType?: PipelineType;
  className?: string;
}

/**
 * Expanded agent progress indicator with labels
 * Good for detail views where more space is available
 */
export function AgentProgressExpanded({ agents, agentType = "drawdocs", className }: AgentProgressExpandedProps) {
  const subAgents = AGENT_TYPE_SUB_AGENTS[agentType] || [];
  
  return (
    <div className={cn("flex items-center gap-3", className)}>
      {subAgents.map((subAgent, idx) => (
        <React.Fragment key={subAgent.id}>
          <div className="flex items-center gap-1.5">
            <StatusDot status={agents[subAgent.id] || "pending"} label={subAgent.name} size="md" />
            <span className="text-xs text-muted-foreground">{subAgent.name}</span>
          </div>
          {idx < subAgents.length - 1 && (
            <div className="h-0.5 w-4 bg-slate-200 rounded-full" />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}
