"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { AgentIcon } from "@/components/ui/agent-icon";
import { 
  FileText, 
  Clock, 
  CheckCircle2, 
  Database,
  Settings,
  AlertTriangle,
  BarChart3,
  Gauge,
  Terminal,
  CheckCircle,
  XCircle,
  Info,
  AlertCircle,
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { RunDetail, AgentResultDetail, LogEntry } from "@/lib/api";

// =============================================================================
// TYPES
// =============================================================================

interface OverviewTabProps {
  runDetail: RunDetail | undefined;
  isLoading: boolean;
  className?: string;
}

// =============================================================================
// HELPERS
// =============================================================================

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function getTotalDuration(agents: RunDetail["agents"]): number {
  let total = 0;
  if (agents.preparation?.elapsed_seconds) total += agents.preparation.elapsed_seconds;
  if (agents.verification?.elapsed_seconds) total += agents.verification.elapsed_seconds;
  if (agents.orderdocs?.elapsed_seconds) total += agents.orderdocs.elapsed_seconds;
  return total;
}

function getFieldsInEncompass(orderdocsOutput: unknown): number {
  if (!orderdocsOutput || typeof orderdocsOutput !== "object") return 0;
  
  const output = orderdocsOutput as Record<string, { has_value?: boolean }>;
  return Object.values(output).filter(field => field?.has_value === true).length;
}

function getPreparationOutput(prepResult: AgentResultDetail | undefined): {
  documentsFound: number;
  documentsProcessed: number;
  fieldsExtracted: number;
} {
  if (!prepResult?.output) {
    return { documentsFound: 0, documentsProcessed: 0, fieldsExtracted: 0 };
  }
  
  const output = prepResult.output as {
    total_documents_found?: number;
    documents_processed?: number;
    results?: {
      field_mappings?: Record<string, unknown>;
    };
  };
  
  return {
    documentsFound: output.total_documents_found || 0,
    documentsProcessed: output.documents_processed || 0,
    fieldsExtracted: output.results?.field_mappings 
      ? Object.keys(output.results.field_mappings).length 
      : 0,
  };
}

// =============================================================================
// CONFIG CARD
// =============================================================================

interface ConfigCardProps {
  runDetail: RunDetail;
}

function ConfigCard({ runDetail }: ConfigCardProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Settings className="h-4 w-4 text-muted-foreground" />
          Run Configuration
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Loan ID</span>
            <p className="font-mono text-xs mt-0.5 truncate" title={runDetail.loan_id}>
              {runDetail.loan_id}
            </p>
          </div>
          <div>
            <span className="text-muted-foreground">Executed</span>
            <p className="mt-0.5">{formatDate(runDetail.execution_timestamp)}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Mode</span>
            <p className="mt-0.5">
              {runDetail.demo_mode ? (
                <span className="inline-flex items-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-blue-500" />
                  Demo Mode
                </span>
              ) : (
                <span className="inline-flex items-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-amber-500" />
                  Production
                </span>
              )}
            </p>
          </div>
          <div>
            <span className="text-muted-foreground">Document Types</span>
            <p className="mt-0.5">All Types</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// TIMING BREAKDOWN CARD (Progress Bars)
// =============================================================================

interface TimingBreakdownProps {
  agents: RunDetail["agents"];
}

function getProgressPercentage(status: string | undefined): number {
  switch (status) {
    case "success":
      return 100;
    case "failed":
      return 100;
    case "running":
      return 50; // Indeterminate - show partial progress
    case "pending":
    default:
      return 0;
  }
}

function TimingBreakdown({ agents }: TimingBreakdownProps) {
  const totalDuration = getTotalDuration(agents);
  
  const agentTimings = [
    { 
      key: "preparation", 
      name: "Preparation", 
      seconds: agents.preparation?.elapsed_seconds || 0,
      status: agents.preparation?.status,
    },
    { 
      key: "verification", 
      name: "Verification", 
      seconds: agents.verification?.elapsed_seconds || 0,
      status: agents.verification?.status,
    },
    { 
      key: "orderdocs", 
      name: "OrderDocs", 
      seconds: agents.orderdocs?.elapsed_seconds || 0,
      status: agents.orderdocs?.status,
    },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Clock className="h-4 w-4 text-muted-foreground" />
          Timing Breakdown
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mb-4">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-semibold tabular-nums">
              {formatDuration(totalDuration)}
            </span>
            <span className="text-sm text-muted-foreground">total</span>
          </div>
        </div>

        <div className="space-y-3">
          {agentTimings.map((agent) => {
            const progress = getProgressPercentage(agent.status);
            const isRunning = agent.status === "running";
            const isFailed = agent.status === "failed";
            
            return (
              <div key={agent.key} className="space-y-1.5">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <AgentIcon type={agent.key as "preparation" | "verification" | "orderdocs"} size="sm" />
                    <span>{agent.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground tabular-nums">
                      {agent.status === "success" || agent.status === "failed" 
                        ? formatDuration(agent.seconds)
                        : agent.status === "running" 
                          ? "Running..."
                          : "—"
                      }
                    </span>
                    {agent.status === "success" && (
                      <CheckCircle className="h-4 w-4 text-emerald-500" />
                    )}
                    {agent.status === "failed" && (
                      <XCircle className="h-4 w-4 text-red-500" />
                    )}
                  </div>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-500",
                      isFailed 
                        ? "bg-red-500"
                        : agent.key === "preparation" && "bg-blue-500",
                      !isFailed && agent.key === "verification" && "bg-emerald-500",
                      !isFailed && agent.key === "orderdocs" && "bg-purple-500",
                      isRunning && "animate-pulse bg-gradient-to-r from-blue-400 to-blue-600"
                    )}
                    style={{ 
                      width: isRunning ? "100%" : `${progress}%`,
                      opacity: isRunning ? 0.6 : 1,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// METRICS CARD
// =============================================================================

interface MetricsCardProps {
  runDetail: RunDetail;
}

function MetricsCard({ runDetail }: MetricsCardProps) {
  const prepOutput = getPreparationOutput(runDetail.agents.preparation);
  const fieldsInEncompass = getFieldsInEncompass(runDetail.agents.orderdocs?.output);
  const progress = runDetail.progress;
  const isPrepRunning = runDetail.agents.preparation?.status === "running";

  // Use live progress when preparation is running, otherwise use final output
  const documentsFound = isPrepRunning && progress?.documents_found 
    ? progress.documents_found 
    : prepOutput.documentsFound;
  const documentsProcessed = isPrepRunning && progress?.documents_processed !== undefined
    ? progress.documents_processed 
    : prepOutput.documentsProcessed;
  const fieldsExtracted = isPrepRunning && progress?.fields_extracted !== undefined
    ? progress.fields_extracted 
    : prepOutput.fieldsExtracted;

  const metrics = [
    {
      icon: FileText,
      label: "Documents Found",
      value: documentsFound,
      color: "text-blue-600",
      bgColor: "bg-blue-100",
      isLive: isPrepRunning && progress?.documents_found !== undefined,
    },
    {
      icon: Gauge,
      label: "Documents Processed",
      value: documentsProcessed,
      color: "text-emerald-600",
      bgColor: "bg-emerald-100",
      isLive: isPrepRunning,
    },
    {
      icon: BarChart3,
      label: "Fields Extracted",
      value: fieldsExtracted,
      color: "text-amber-600",
      bgColor: "bg-amber-100",
      subtext: isPrepRunning && progress?.current_document 
        ? `from ${progress.current_document.slice(0, 20)}...` 
        : "from prep",
      isLive: isPrepRunning,
    },
    {
      icon: Database,
      label: "Fields in Encompass",
      value: fieldsInEncompass,
      color: "text-purple-600",
      bgColor: "bg-purple-100",
      subtext: "with values",
      isLive: false,
    },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
          Key Metrics
          {isPrepRunning && (
            <span className="ml-auto text-[10px] font-normal text-blue-500 animate-pulse">
              ● Live
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          {metrics.map((metric) => (
            <div
              key={metric.label}
              className={cn(
                "flex items-start gap-3 p-3 rounded-lg bg-muted/50",
                metric.isLive && "ring-1 ring-blue-200 dark:ring-blue-800"
              )}
            >
              <div className={cn("p-2 rounded-lg", metric.bgColor)}>
                <metric.icon className={cn("h-4 w-4", metric.color)} />
              </div>
              <div>
                <p className={cn(
                  "text-2xl font-semibold tabular-nums",
                  metric.isLive && "text-blue-600"
                )}>
                  {metric.value}
                </p>
                <p className="text-xs text-muted-foreground">{metric.label}</p>
                {metric.subtext && (
                  <p className="text-[10px] text-muted-foreground/70 truncate max-w-[120px]">
                    {metric.subtext}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// LIVE LOGS CARD
// =============================================================================

interface LiveLogsCardProps {
  logs: LogEntry[] | undefined;
}

function getLogIcon(level: string) {
  switch (level) {
    case "success":
      return <CheckCircle className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0" />;
    case "error":
      return <XCircle className="h-3.5 w-3.5 text-red-500 flex-shrink-0" />;
    case "warning":
      return <AlertCircle className="h-3.5 w-3.5 text-amber-500 flex-shrink-0" />;
    default:
      return <Info className="h-3.5 w-3.5 text-blue-500 flex-shrink-0" />;
  }
}

function formatLogTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function LiveLogsCard({ logs }: LiveLogsCardProps) {
  const displayLogs = logs?.slice().reverse() || [];
  
  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Terminal className="h-4 w-4 text-muted-foreground" />
          Activity Log
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[200px] px-4 pb-4">
          {displayLogs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
              No activity yet...
            </div>
          ) : (
            <div className="space-y-2">
              {displayLogs.map((log, idx) => (
                <div
                  key={idx}
                  className={cn(
                    "flex items-start gap-2 text-xs p-2 rounded-md",
                    log.level === "error" && "bg-red-50 dark:bg-red-950/20",
                    log.level === "success" && "bg-emerald-50 dark:bg-emerald-950/20",
                    log.level === "warning" && "bg-amber-50 dark:bg-amber-950/20",
                    log.level === "info" && "bg-muted/50",
                  )}
                >
                  {getLogIcon(log.level)}
                  <div className="flex-1 min-w-0">
                    <p className="text-foreground leading-tight">{log.message}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-muted-foreground font-mono text-[10px]">
                        {formatLogTime(log.timestamp)}
                      </span>
                      {log.agent && log.agent !== "orchestrator" && (
                        <span className="text-muted-foreground text-[10px] capitalize">
                          • {log.agent}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// ERROR DETAILS CARD
// =============================================================================

interface ErrorDetailsCardProps {
  agents: RunDetail["agents"];
}

function ErrorDetailsCard({ agents }: ErrorDetailsCardProps) {
  const errors: { agent: string; error: string }[] = [];

  if (agents.preparation?.status === "failed" && agents.preparation.error) {
    errors.push({ agent: "Preparation", error: agents.preparation.error });
  }
  if (agents.verification?.status === "failed" && agents.verification.error) {
    errors.push({ agent: "Verification", error: agents.verification.error });
  }
  if (agents.orderdocs?.status === "failed" && agents.orderdocs.error) {
    errors.push({ agent: "OrderDocs", error: agents.orderdocs.error });
  }

  if (errors.length === 0) return null;

  return (
    <Card className="border-red-200 bg-red-50/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2 text-red-700">
          <AlertTriangle className="h-4 w-4" />
          Error Details
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {errors.map((err, idx) => (
          <div key={idx} className="p-3 rounded-lg bg-red-100/50 border border-red-200">
            <p className="text-sm font-medium text-red-800 mb-1">
              {err.agent} Agent Failed
            </p>
            <pre className="text-xs text-red-700 whitespace-pre-wrap font-mono overflow-x-auto">
              {err.error}
            </pre>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// LOADING SKELETON
// =============================================================================

function OverviewSkeleton() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {[...Array(4)].map((_, i) => (
        <Card key={i}>
          <CardHeader className="pb-3">
            <Skeleton className="h-4 w-32" />
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function OverviewTab({ runDetail, isLoading, className }: OverviewTabProps) {
  if (isLoading || !runDetail) {
    return <OverviewSkeleton />;
  }

  // Check if any agent failed
  const hasFailed = 
    runDetail.agents.preparation?.status === "failed" ||
    runDetail.agents.verification?.status === "failed" ||
    runDetail.agents.orderdocs?.status === "failed";

  return (
    <div className={cn("space-y-4", className)}>
      {/* Error Details (if failed) */}
      {hasFailed && <ErrorDetailsCard agents={runDetail.agents} />}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ConfigCard runDetail={runDetail} />
        <TimingBreakdown agents={runDetail.agents} />
        <MetricsCard runDetail={runDetail} />
        <LiveLogsCard logs={runDetail.logs} />

        {/* Corrected Fields Summary (if available) */}
        {runDetail.corrected_fields_summary && runDetail.corrected_fields_summary.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Database className="h-4 w-4 text-muted-foreground" />
                Corrected Fields
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {runDetail.corrected_fields_summary.slice(0, 5).map((field, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between text-sm p-2 rounded bg-muted/50"
                  >
                    <div>
                      <p className="font-medium">{field.field_name}</p>
                      <p className="text-xs text-muted-foreground font-mono">
                        {field.field_id}
                      </p>
                    </div>
                    <p className="text-sm font-mono text-emerald-600">
                      {field.corrected_value}
                    </p>
                  </div>
                ))}
                {runDetail.corrected_fields_summary.length > 5 && (
                  <p className="text-xs text-muted-foreground text-center pt-2">
                    +{runDetail.corrected_fields_summary.length - 5} more fields
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

