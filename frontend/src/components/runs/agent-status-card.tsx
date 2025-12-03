"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { AgentIcon } from "@/components/ui/agent-icon";
import { StatusBadge } from "@/components/ui/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, CheckCircle2, Clock, Loader2 } from "lucide-react";
import type { AgentResultDetail } from "@/lib/api";

// =============================================================================
// TYPES
// =============================================================================

type AgentType = "preparation" | "drawcore" | "verification" | "orderdocs";

interface AgentStatusCardProps {
  agent: AgentType;
  result: AgentResultDetail | undefined;
  isLoading?: boolean;
  isActive?: boolean;
  onClick?: () => void;
  className?: string;
  /** Run execution timestamp for live duration calculation */
  executionTimestamp?: string;
}

// =============================================================================
// HELPERS
// =============================================================================

const agentNames: Record<AgentType, string> = {
  preparation: "Preparation",
  drawcore: "Drawcore",
  verification: "Verification",
  orderdocs: "OrderDocs",
};

const agentDescriptions: Record<AgentType, string> = {
  preparation: "Extract data from documents",
  drawcore: "Update Encompass fields in bulk",
  verification: "Verify against SOP rules",
  orderdocs: "Mavent check & order docs",
};

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const mins = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(0);
  return `${mins}m ${secs}s`;
}

// =============================================================================
// LIVE DURATION COUNTER
// =============================================================================

interface LiveDurationProps {
  startTime?: string;
}

function LiveDuration({ startTime }: LiveDurationProps) {
  const [elapsed, setElapsed] = React.useState(0);

  React.useEffect(() => {
    if (!startTime) {
      // If no start time, just count from now
      const now = Date.now();
      const interval = setInterval(() => {
        setElapsed((Date.now() - now) / 1000);
      }, 100);
      return () => clearInterval(interval);
    }

    const start = new Date(startTime).getTime();
    
    const updateElapsed = () => {
      const now = Date.now();
      setElapsed((now - start) / 1000);
    };

    updateElapsed();
    const interval = setInterval(updateElapsed, 100);
    
    return () => clearInterval(interval);
  }, [startTime]);

  return (
    <span className="tabular-nums">
      {elapsed.toFixed(1)}s
      <span className="animate-pulse">...</span>
    </span>
  );
}

// =============================================================================
// STATUS ICON
// =============================================================================

interface StatusIconProps {
  status: AgentResultDetail["status"] | undefined;
  className?: string;
}

function StatusIcon({ status, className }: StatusIconProps) {
  switch (status) {
    case "success":
      return <CheckCircle2 className={cn("h-5 w-5 text-emerald-500", className)} />;
    case "running":
      return <Loader2 className={cn("h-5 w-5 text-blue-500 animate-spin", className)} />;
    case "failed":
      return <AlertCircle className={cn("h-5 w-5 text-red-500", className)} />;
    case "pending":
    default:
      return <Clock className={cn("h-5 w-5 text-slate-400", className)} />;
  }
}

// =============================================================================
// LOADING SKELETON
// =============================================================================

function AgentStatusCardSkeleton({ className }: { className?: string }) {
    return (
      <div className={cn(
        "flex flex-col gap-3 p-4 rounded-xl border border-border bg-card",
        className
      )}>
        <div className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <div className="space-y-1.5 flex-1">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-3 w-32" />
          </div>
        </div>
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-4 w-12" />
        </div>
      </div>
    );
  }
  
  // =============================================================================
  // MAIN COMPONENT
  // =============================================================================
  
  export function AgentStatusCard({
    agent,
    result,
    isLoading = false,
    isActive = false,
    onClick,
    className,
    executionTimestamp,
  }: AgentStatusCardProps) {
    if (isLoading) {
      return <AgentStatusCardSkeleton className={className} />;
    }
  
    const status = result?.status || "pending";
    const isPending = status === "pending";
    const isRunning = status === "running";
    const isSuccess = status === "success";
    const isFailed = status === "failed";
  
    return (
      <button
        onClick={onClick}
        disabled={isPending}
        className={cn(
          "flex flex-col gap-3 p-4 rounded-xl border transition-all text-left w-full",
          "hover:shadow-md focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
          // Base styles
          "bg-card",
          // Status-specific styles
          isPending && "border-slate-200 bg-slate-50/50 cursor-default opacity-70",
          isRunning && "border-blue-200 bg-blue-50/30 shadow-sm",
          isSuccess && "border-emerald-200 bg-emerald-50/30",
          isFailed && "border-red-200 bg-red-50/30",
          // Active state
          isActive && "ring-2 ring-primary ring-offset-2",
          className
        )}
      >
        {/* Top Row: Icon + Name */}
        <div className="flex items-center gap-3">
          <AgentIcon type={agent} showBackground size="lg" />
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-sm text-foreground">
              {agentNames[agent]}
            </h3>
            <p className="text-xs text-muted-foreground truncate">
              {agentDescriptions[agent]}
            </p>
          </div>
          <StatusIcon status={status} />
        </div>
  
        {/* Bottom Row: Status Badge + Timing */}
        <div className="flex items-center justify-between gap-2">
          <StatusBadge
            variant={
              isSuccess ? "success" :
              isRunning ? "processing" :
              isFailed ? "error" :
              "pending"
            }
            size="sm"
          >
            {isSuccess && "Complete"}
            {isRunning && "Running"}
            {isFailed && "Failed"}
            {isPending && "Pending"}
          </StatusBadge>
  
          <div className="text-sm font-medium">
            {isRunning ? (
              <span className="text-blue-600">
                <LiveDuration startTime={executionTimestamp} />
              </span>
            ) : result?.elapsed_seconds !== undefined ? (
              <span className={cn(
                isFailed ? "text-red-600" : "text-muted-foreground"
              )}>
                {formatDuration(result.elapsed_seconds)}
              </span>
            ) : (
              <span className="text-slate-400">—</span>
            )}
          </div>
        </div>
  
        {/* Attempts indicator (if more than 1) */}
        {result && result.attempts > 1 && (
          <div className="text-xs text-muted-foreground">
            Attempt {result.attempts}
          </div>
        )}
  
        {/* Error preview (if failed) */}
        {isFailed && result?.error && (
          <div className="mt-1 p-2 rounded bg-red-100 border border-red-200">
            <p className="text-xs text-red-700 line-clamp-2">
              {result.error}
            </p>
          </div>
        )}
      </button>
    );
  }
  
  // =============================================================================
  // AGENT STATUS CARDS ROW
  // =============================================================================
  
  interface AgentStatusCardsProps {
    agents: {
      preparation?: AgentResultDetail;
      drawcore?: AgentResultDetail;
      verification?: AgentResultDetail;
      orderdocs?: AgentResultDetail;
    } | undefined;
    isLoading?: boolean;
    activeAgent?: AgentType | null;
    onAgentClick?: (agent: AgentType) => void;
    className?: string;
    /** Run execution timestamp for live duration calculation */
    executionTimestamp?: string;
  }
  
  export function AgentStatusCards({
    agents,
    isLoading = false,
    activeAgent,
    onAgentClick,
    className,
    executionTimestamp,
  }: AgentStatusCardsProps) {
    const agentTypes: AgentType[] = ["preparation", "drawcore", "verification", "orderdocs"];
  
    return (
      <div className={cn("grid grid-cols-1 sm:grid-cols-4 gap-4", className)}>
        {agentTypes.map((agentType) => (
          <AgentStatusCard
            key={agentType}
            agent={agentType}
            result={agents?.[agentType]}
            isLoading={isLoading}
            isActive={activeAgent === agentType}
            onClick={() => onAgentClick?.(agentType)}
            executionTimestamp={executionTimestamp}
          />
        ))}
      </div>
    );
  }