"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { 
  ArrowLeft, 
  RefreshCw, 
  ChevronDown, 
  Download, 
  FileJson,
  Copy,
  Check,
  Loader2
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useToast } from "@/components/ui/toast";
import { useCreateRun } from "@/hooks/use-runs";
import type { RunDetail, RunStatusValue } from "@/lib/api";

// =============================================================================
// TYPES
// =============================================================================

interface RunDetailHeaderProps {
  runId: string;
  runDetail: RunDetail | undefined;
  isLoading: boolean;
  className?: string;
}

// =============================================================================
// HELPERS
// =============================================================================

function truncateUuid(uuid: string): string {
  return uuid.substring(0, 8) + "...";
}

function getOverallStatus(runDetail: RunDetail | undefined): RunStatusValue | "pending" {
  if (!runDetail) return "pending";
  
  const agents = runDetail.agents;
  
  // If any agent failed, the run failed
  if (agents.preparation?.status === "failed" || 
      agents.verification?.status === "failed" || 
      agents.orderdocs?.status === "failed") {
    return "failed";
  }
  
  // If any agent is running, the run is running
  if (agents.preparation?.status === "running" || 
      agents.verification?.status === "running" || 
      agents.orderdocs?.status === "running") {
    return "running";
  }
  
  // If all agents are pending, the run is pending
  if ((!agents.preparation || agents.preparation.status === "pending") &&
      (!agents.verification || agents.verification.status === "pending") &&
      (!agents.orderdocs || agents.orderdocs.status === "pending")) {
    return "pending";
  }
  
  // If all agents are successful
  if (agents.preparation?.status === "success" && 
      agents.verification?.status === "success" && 
      agents.orderdocs?.status === "success") {
    return "success";
  }
  
  // Mixed state - some complete, some pending
  return "running";
}

function getStatusBadgeVariant(status: RunStatusValue | "pending"): "success" | "processing" | "error" | "pending" {
  switch (status) {
    case "success":
      return "success";
    case "running":
      return "processing";
    case "failed":
      return "error";
    case "pending":
    default:
      return "pending";
  }
}

function getStatusLabel(status: RunStatusValue | "pending"): string {
  switch (status) {
    case "success":
      return "Completed";
    case "running":
      return "Running";
    case "failed":
      return "Failed";
    case "pending":
    default:
      return "Pending";
  }
}

// =============================================================================
// COPY BUTTON COMPONENT
// =============================================================================

interface CopyButtonProps {
  text: string;
}

function CopyButton({ text }: CopyButtonProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
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
      className="p-1.5 rounded hover:bg-muted transition-colors"
      title={copied ? "Copied!" : "Copy Loan ID"}
    >
      {copied ? (
        <Check className="h-4 w-4 text-emerald-500" />
      ) : (
        <Copy className="h-4 w-4 text-muted-foreground" />
      )}
    </button>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function RunDetailHeader({ 
  runId, 
  runDetail, 
  isLoading,
  className 
}: RunDetailHeaderProps) {
  const router = useRouter();
  const { addToast } = useToast();
  
  const overallStatus = getOverallStatus(runDetail);
  const loanId = runDetail?.loan_id || "";

  // Re-run mutation
  const createRunMutation = useCreateRun({
    onSuccess: (data) => {
      addToast({
        title: "Run Started",
        description: "New run has been queued",
        variant: "success",
      });
      router.push(`/runs/${data.run_id}`);
    },
    onError: (error) => {
      addToast({
        title: "Failed to Start Run",
        description: error.message,
        variant: "error",
      });
    },
  });

  const handleRerun = () => {
    if (!runDetail) return;
    
    createRunMutation.mutate({
      loan_id: runDetail.loan_id,
      demo_mode: runDetail.demo_mode,
    });
  };

  const handleExportJson = () => {
    if (!runDetail) return;
    
    const blob = new Blob([JSON.stringify(runDetail, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `run-${runId}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    addToast({
      title: "Export Complete",
      description: "Run data exported as JSON",
      variant: "success",
    });
  };

  return (
    <header className={cn("flex items-center justify-between py-6 px-8", className)}>
      <div className="flex items-center gap-4">
        {/* Back Button */}
        <Button variant="ghost" size="sm" asChild className="-ml-2">
          <Link href="/runs" className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" />
            <span>Runs</span>
          </Link>
        </Button>

        <div className="h-6 w-px bg-border" />

        {/* Loan ID */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Loan:</span>
          {isLoading ? (
            <div className="h-5 w-24 bg-muted animate-pulse rounded" />
          ) : (
            <>
              <code className="text-sm font-mono font-medium">
                {truncateUuid(loanId)}
              </code>
              <CopyButton text={loanId} />
            </>
          )}
        </div>

        {/* Demo Mode Badge */}
        {runDetail?.demo_mode && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-medium uppercase tracking-wide">
            Demo
          </span>
        )}

        {/* Status Badge */}
        {!isLoading && (
          <StatusBadge variant={getStatusBadgeVariant(overallStatus)} size="md">
            {getStatusLabel(overallStatus)}
          </StatusBadge>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleRerun}
          disabled={isLoading || createRunMutation.isPending}
        >
          {createRunMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Starting...
            </>
          ) : (
            <>
              <RefreshCw className="h-4 w-4 mr-2" />
              Re-run
            </>
          )}
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" disabled={isLoading}>
              Actions
              <ChevronDown className="h-4 w-4 ml-2" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onClick={handleExportJson}>
              <FileJson className="h-4 w-4 mr-2" />
              Export JSON
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem 
              onClick={() => {
                if (loanId) {
                  navigator.clipboard.writeText(loanId);
                  addToast({
                    title: "Copied",
                    description: "Loan ID copied to clipboard",
                    variant: "success",
                  });
                }
              }}
            >
              <Copy className="h-4 w-4 mr-2" />
              Copy Loan ID
            </DropdownMenuItem>
            <DropdownMenuItem 
              onClick={() => {
                navigator.clipboard.writeText(runId);
                addToast({
                  title: "Copied",
                  description: "Run ID copied to clipboard",
                  variant: "success",
                });
              }}
            >
              <Copy className="h-4 w-4 mr-2" />
              Copy Run ID
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}

