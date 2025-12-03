"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useRunDetail } from "@/hooks/use-runs";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

// Import shared run detail components
import { RunDetailHeader } from "@/components/runs/run-detail-header";
import { AgentStatusCards } from "@/components/runs/agent-status-cards";
import { OverviewTab } from "@/components/runs/tabs/overview-tab";
import { TimelineTab } from "@/components/runs/tabs/timeline-tab";
import { FinalReportTab } from "@/components/runs/tabs/final-report-tab";

/**
 * LOA Run Detail Page
 * 
 * Displays detailed information about a specific LOA (Loan Officer Assistant) run.
 * Shows agent statuses, timeline, report, and other run-specific data.
 */
export default function LoaRunDetailPage() {
  const params = useParams();
  const runId = params?.runId as string;

  const { data: runDetail, isLoading, error } = useRunDetail(runId);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32 w-full" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error || !runDetail) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          {error instanceof Error ? error.message : "Failed to load run details"}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with back button and run info */}
      <RunDetailHeader runDetail={runDetail} backPath="/loa/runs" />

      {/* Agent Status Cards - 3 sub-agents for LOA */}
      <AgentStatusCards runDetail={runDetail} agentType="loa" />

      {/* Tabs for different views */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="report">Report</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewTab runDetail={runDetail} />
        </TabsContent>

        <TabsContent value="timeline">
          <TimelineTab runDetail={runDetail} />
        </TabsContent>

        <TabsContent value="report">
          <FinalReportTab runDetail={runDetail} />
        </TabsContent>

        <TabsContent value="documents">
          <DocumentsTabPlaceholder />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Placeholder for Documents tab
function DocumentsTabPlaceholder() {
  return (
    <div className="flex items-center justify-center h-64 border-2 border-dashed rounded-lg">
      <div className="text-center text-muted-foreground">
        <p className="text-lg font-medium mb-2">Documents View</p>
        <p className="text-sm">LOA document management coming soon</p>
      </div>
    </div>
  );
}

