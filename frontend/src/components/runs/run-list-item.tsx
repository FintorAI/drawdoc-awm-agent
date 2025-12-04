"use client";

import * as React from "react";
import Link from "next/link";
import { Copy, Check, ChevronRight, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/status-badge";
import { AgentProgressIndicator } from "./agent-progress-indicator";
import type { RunSummary, RunStatusValue } from "@/lib/api";

// =============================================================================
// TYPES
// =============================================================================

interface RunListItemProps {
  run: RunSummary;
  className?: string;
  /** Base path for run detail links (default: "/runs") */
  basePath?: string;
}

// =============================================================================
// HELPERS
// =============================================================================

/**
 * Format duration in seconds to human-readable string.
 * e.g., 72.47 -> "1m 12s"
 */
function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

/**
 * Format ISO timestamp to relative time.
 * e.g., "2 minutes ago"
 */
function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  
  if (diffSecs < 60) {
    return "just now";
  }
  
  const diffMins = Math.floor(diffSecs / 60);
  if (diffMins < 60) {
    return `${diffMins} minute${diffMins !== 1 ? "s" : ""} ago`;
  }
  
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) {
    return `${diffHours} hour${diffHours !== 1 ? "s" : ""} ago`;
  }
  
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) {
    return `${diffDays} day${diffDays !== 1 ? "s" : ""} ago`;
  }
  
  return date.toLocaleDateString();
}

/**
 * Map run status to StatusBadge variant.
 */
function getStatusVariant(status: RunStatusValue): "success" | "processing" | "error" | "warning" {
  switch (status) {
    case "success":
      return "success";
    case "running":
      return "processing";
    case "failed":
      return "error";
    case "blocked":
      return "warning";
    default:
      return "processing";
  }
}

/**
 * Truncate UUID for display.
 */
function truncateUuid(uuid: string): string {
  return uuid.substring(0, 8) + "...";
}

// =============================================================================
// COPY BUTTON COMPONENT
// =============================================================================

interface CopyButtonProps {
  text: string;
  className?: string;
}

function CopyButton({ text, className }: CopyButtonProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error("Failed to copy:", error);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className={cn(
        "p-1 rounded hover:bg-muted transition-colors",
        className
      )}
      title={copied ? "Copied!" : "Copy Loan ID"}
    >
      {copied ? (
        <Check className="h-3.5 w-3.5 text-emerald-500" />
      ) : (
        <Copy className="h-3.5 w-3.5 text-muted-foreground" />
      )}
    </button>
  );
}

// =============================================================================
// LIVE DURATION COUNTER
// =============================================================================

interface LiveDurationProps {
  startTime: string;
}

function LiveDuration({ startTime }: LiveDurationProps) {
  const [elapsed, setElapsed] = React.useState(0);

  React.useEffect(() => {
    const start = new Date(startTime).getTime();
    
    const updateElapsed = () => {
      const now = Date.now();
      setElapsed((now - start) / 1000);
    };

    updateElapsed();
    const interval = setInterval(updateElapsed, 1000);
    
    return () => clearInterval(interval);
  }, [startTime]);

  return (
    <span className="text-blue-600 font-medium">
      {formatDuration(elapsed)}
      <span className="animate-pulse ml-0.5">...</span>
    </span>
  );
}

// =============================================================================
// MAIN COMPONENT - TABLE ROW VARIANT
// =============================================================================

/**
 * Run list item component for table/list view.
 * 
 * Displays:
 * - Loan ID (truncated with copy button)
 * - Status Badge
 * - Agent Progress (3 mini indicators)
 * - Documents Processed
 * - Duration (live counter if running)
 * - Started (relative time)
 */
export function RunListItem({ run, className, basePath = "/runs" }: RunListItemProps) {
  return (
    <Link
      href={`${basePath}/${run.run_id}`}
      className={cn(
        "flex items-center gap-4 p-4 rounded-lg border border-border",
        "hover:bg-muted/50 hover:border-muted-foreground/20 transition-all",
        "group cursor-pointer",
        run.status === "running" && "border-blue-200 bg-blue-50/30",
        className
      )}
    >
      {/* Loan ID */}
      <div className="flex items-center gap-2 min-w-[140px]">
        <code className="text-sm font-mono text-foreground">
          {truncateUuid(run.loan_id)}
        </code>
        <CopyButton text={run.loan_id} />
        {run.demo_mode && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-medium uppercase tracking-wide">
            Demo
          </span>
        )}
      </div>

      {/* Status Badge */}
      <StatusBadge variant={getStatusVariant(run.status)} size="md">
        {run.status === "success" && "Success"}
        {run.status === "running" && "Running"}
        {run.status === "failed" && "Failed"}
        {run.status === "blocked" && "Blocked"}
      </StatusBadge>

      {/* Agent Progress */}
      <div className="hidden sm:flex items-center gap-2">
        <AgentProgressIndicator agents={run.agents} agentType={run.agent_type} size="sm" />
      </div>

      {/* Documents */}
      <div className="hidden md:flex items-center gap-1.5 text-sm text-muted-foreground min-w-[80px]">
        <FileText className="h-4 w-4" />
        <span>
          {run.documents_processed}
          <span className="text-muted-foreground/60"> / {run.documents_found}</span>
        </span>
      </div>

      {/* Duration */}
      <div className="text-sm min-w-[70px] text-right">
        {run.status === "running" ? (
          <LiveDuration startTime={run.created_at} />
        ) : (
          <span className="text-muted-foreground">
            {formatDuration(run.duration_seconds)}
          </span>
        )}
      </div>

      {/* Started time */}
      <div className="hidden lg:block text-sm text-muted-foreground min-w-[100px]">
        {formatRelativeTime(run.created_at)}
      </div>

      {/* Arrow */}
      <ChevronRight className="h-5 w-5 text-muted-foreground/50 group-hover:text-muted-foreground transition-colors ml-auto" />
    </Link>
  );
}

// =============================================================================
// CARD VARIANT (for mobile)
// =============================================================================

export function RunListItemCard({ run, className, basePath = "/runs" }: RunListItemProps) {
  return (
    <Link
      href={`${basePath}/${run.run_id}`}
      className={cn(
        "block p-4 rounded-lg border border-border",
        "hover:bg-muted/50 hover:border-muted-foreground/20 transition-all",
        "space-y-3",
        run.status === "running" && "border-blue-200 bg-blue-50/30",
        className
      )}
    >
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <code className="text-sm font-mono text-foreground">
            {truncateUuid(run.loan_id)}
          </code>
          <CopyButton text={run.loan_id} />
        </div>
        <StatusBadge variant={getStatusVariant(run.status)} size="sm">
          {run.status === "success" && "Success"}
          {run.status === "running" && "Running"}
          {run.status === "failed" && "Failed"}
          {run.status === "blocked" && "Blocked"}
        </StatusBadge>
      </div>

      {/* Agent Progress */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Agents:</span>
        <AgentProgressIndicator agents={run.agents} agentType={run.agent_type} size="sm" />
      </div>

      {/* Stats row */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <div className="flex items-center gap-4">
          <span>{run.documents_processed} / {run.documents_found} docs</span>
          {run.demo_mode && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-medium uppercase">
              Demo
            </span>
          )}
        </div>
        <div>
          {run.status === "running" ? (
            <LiveDuration startTime={run.created_at} />
          ) : (
            formatDuration(run.duration_seconds)
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-muted-foreground pt-1 border-t border-border">
        <span>{formatRelativeTime(run.created_at)}</span>
        <ChevronRight className="h-4 w-4" />
      </div>
    </Link>
  );
}

