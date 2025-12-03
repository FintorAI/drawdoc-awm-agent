"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { CheckCircle2, Clock, Loader2, AlertCircle, ShieldAlert, ArrowRight } from "lucide-react";
import { type AgentType, getSubAgents, type SubAgentConfig } from "@/types/agents";
import type { AgentStatusValue } from "@/lib/api";

// =============================================================================
// TYPES
// =============================================================================

interface SubAgentPipelineProps {
  /** Agent pipeline type */
  agentType: AgentType;
  /** Agent statuses keyed by agent ID */
  agentStatuses?: Record<string, AgentStatusValue>;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Show agent names below icons */
  showLabels?: boolean;
  /** Additional className */
  className?: string;
}

// =============================================================================
// STATUS DOT
// =============================================================================

interface StatusDotProps {
  status: AgentStatusValue;
  size: "sm" | "md" | "lg";
}

function StatusDot({ status, size }: StatusDotProps) {
  const sizeClasses = {
    sm: "h-2 w-2",
    md: "h-3 w-3",
    lg: "h-4 w-4",
  };

  const baseClasses = cn("rounded-full", sizeClasses[size]);

  switch (status) {
    case "success":
      return <span className={cn(baseClasses, "bg-emerald-500")} />;
    case "running":
      return <span className={cn(baseClasses, "bg-blue-500 animate-pulse")} />;
    case "failed":
      return <span className={cn(baseClasses, "bg-red-500")} />;
    case "blocked":
      return <span className={cn(baseClasses, "bg-amber-500")} />;
    case "pending":
    default:
      return <span className={cn(baseClasses, "bg-slate-300")} />;
  }
}

// =============================================================================
// STATUS ICON
// =============================================================================

interface StatusIconProps {
  status: AgentStatusValue;
  size: "sm" | "md" | "lg";
  className?: string;
}

function StatusIcon({ status, size, className }: StatusIconProps) {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-5 w-5",
    lg: "h-6 w-6",
  };

  const iconClass = cn(sizeClasses[size], className);

  switch (status) {
    case "success":
      return <CheckCircle2 className={cn(iconClass, "text-emerald-500")} />;
    case "running":
      return <Loader2 className={cn(iconClass, "text-blue-500 animate-spin")} />;
    case "failed":
      return <AlertCircle className={cn(iconClass, "text-red-500")} />;
    case "blocked":
      return <ShieldAlert className={cn(iconClass, "text-amber-500")} />;
    case "pending":
    default:
      return <Clock className={cn(iconClass, "text-slate-400")} />;
  }
}

// =============================================================================
// PIPELINE STEP
// =============================================================================

interface PipelineStepProps {
  agent: SubAgentConfig;
  status: AgentStatusValue;
  size: "sm" | "md" | "lg";
  showLabels: boolean;
  isLast: boolean;
}

function PipelineStep({ agent, status, size, showLabels, isLast }: PipelineStepProps) {
  const Icon = agent.icon;
  
  const iconContainerSize = {
    sm: "h-8 w-8",
    md: "h-10 w-10",
    lg: "h-12 w-12",
  };

  const iconSize = {
    sm: "h-4 w-4",
    md: "h-5 w-5",
    lg: "h-6 w-6",
  };

  const arrowSize = {
    sm: "h-3 w-3",
    md: "h-4 w-4",
    lg: "h-5 w-5",
  };

  return (
    <>
      <div className="flex flex-col items-center">
        <div className={cn(
          "rounded-xl flex items-center justify-center relative",
          iconContainerSize[size],
          status === "success" && "bg-emerald-100",
          status === "running" && "bg-blue-100",
          status === "failed" && "bg-red-100",
          status === "blocked" && "bg-amber-100",
          status === "pending" && "bg-slate-100",
        )}>
          <Icon className={cn(
            iconSize[size],
            status === "success" && "text-emerald-600",
            status === "running" && "text-blue-600",
            status === "failed" && "text-red-600",
            status === "blocked" && "text-amber-600",
            status === "pending" && "text-slate-400",
          )} />
          
          {/* Status indicator */}
          <div className="absolute -bottom-1 -right-1">
            <StatusDot status={status} size="sm" />
          </div>
        </div>
        
        {showLabels && (
          <span className={cn(
            "text-xs mt-1.5 font-medium",
            status === "pending" ? "text-slate-400" : "text-foreground"
          )}>
            {agent.name}
          </span>
        )}
      </div>
      
      {!isLast && (
        <ArrowRight className={cn(
          arrowSize[size],
          "text-slate-300 shrink-0",
          showLabels && "mt-0 self-start mt-3"
        )} />
      )}
    </>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function SubAgentPipeline({
  agentType,
  agentStatuses = {},
  size = "md",
  showLabels = false,
  className,
}: SubAgentPipelineProps) {
  const subAgents = getSubAgents(agentType);

  return (
    <div className={cn(
      "flex items-center gap-2",
      showLabels && "gap-3",
      className
    )}>
      {subAgents.map((agent, index) => (
        <PipelineStep
          key={agent.id}
          agent={agent}
          status={agentStatuses[agent.id] || "pending"}
          size={size}
          showLabels={showLabels}
          isLast={index === subAgents.length - 1}
        />
      ))}
    </div>
  );
}

// =============================================================================
// COMPACT DOT VARIANT
// =============================================================================

interface SubAgentDotsProps {
  agentType: AgentType;
  agentStatuses?: Record<string, AgentStatusValue>;
  className?: string;
}

/**
 * Compact dot representation of pipeline status.
 * Shows just colored dots for each sub-agent.
 */
export function SubAgentDots({
  agentType,
  agentStatuses = {},
  className,
}: SubAgentDotsProps) {
  const subAgents = getSubAgents(agentType);

  return (
    <div className={cn("flex items-center gap-1", className)}>
      {subAgents.map((agent) => (
        <StatusDot
          key={agent.id}
          status={agentStatuses[agent.id] || "pending"}
          size="sm"
        />
      ))}
    </div>
  );
}

