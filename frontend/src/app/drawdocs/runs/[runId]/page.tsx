"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { RunDetailHeader } from "@/components/runs/run-detail-header";
import { AgentStatusCards } from "@/components/runs/agent-status-card";
import { OverviewTab } from "@/components/runs/overview-tab";
import { TimelineTab } from "@/components/runs/timeline-tab";
import { FinalReportTab } from "@/components/runs/final-report-tab";
import { FieldReviewTab } from "@/components/runs/field-review-tab";
import { useRunDetail } from "@/hooks/use-runs";
import { AlertTriangle, RefreshCw, ChevronLeft, AlertCircle } from "lucide-react";

// =============================================================================
// LOADING STATE
// =============================================================================

function LoadingState() {
  return (
    <div className="flex flex-col">
      {/* Header skeleton */}
      <div className="flex items-center justify-between py-6 px-8">
        <div className="flex items-center gap-4">
          <Skeleton className="h-8 w-20" />
          <div className="h-6 w-px bg-border" />
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-9 w-24" />
        </div>
      </div>

      <div className="px-8 pb-8 space-y-6">
        {/* Agent Cards skeleton */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="p-4 rounded-xl border border-border bg-card">
              <div className="flex items-center gap-3 mb-3">
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
          ))}
        </div>

        {/* Tabs skeleton */}
        <Skeleton className="h-10 w-80" />

        {/* Content skeleton */}
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
      </div>
    </div>
  );
}

// =============================================================================
// ERROR STATE
// =============================================================================

interface ErrorStateProps {
  error: Error;
  onRetry: () => void;
}

function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <div className="h-16 w-16 rounded-full bg-red-100 flex items-center justify-center mb-4">
        <AlertTriangle className="h-8 w-8 text-red-600" />
      </div>
      <h2 className="text-xl font-semibold mb-2">Failed to load run details</h2>
      <p className="text-muted-foreground mb-2 max-w-md">{error.message}</p>
      <p className="text-sm text-muted-foreground mb-6">
        Make sure the backend server is running on port 8000
      </p>
      <div className="flex items-center gap-2">
        <Link href="/drawdocs/runs">
          <Button variant="outline">
            <ChevronLeft className="h-4 w-4 mr-2" />
            Back to Runs
          </Button>
        </Link>
        <Button onClick={onRetry} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    </div>
  );
}

// =============================================================================
// PLACEHOLDER TAB CONTENT
// =============================================================================

function DocumentsTabPlaceholder() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Documents</CardTitle>
        <CardDescription>PDF viewer for processed documents</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-3">
            <span className="text-2xl">📄</span>
          </div>
          <p className="text-muted-foreground">
            Document viewer coming soon
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

// FieldsTab is now FieldReviewTab - imported from components

// =============================================================================
// MAIN PAGE COMPONENT
// =============================================================================

export default function DrawDocsRunDetailPage() {
  const params = useParams();
  const runId = params.runId as string;

  const { data: runDetail, isLoading, error, refetch } = useRunDetail(runId);

  // Handle loading state
  if (isLoading && !runDetail) {
    return <LoadingState />;
  }

  // Handle error state
  if (error && !runDetail) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <RunDetailHeader
        runId={runId}
        runDetail={runDetail}
        isLoading={isLoading}
        backPath="/drawdocs/runs"
      />

      <div className="px-8 pb-8 space-y-6">
        {/* Agent Status Cards */}
        <AgentStatusCards
          agents={runDetail?.agents}
          agentType="drawdocs"
          isLoading={isLoading && !runDetail}
          executionTimestamp={runDetail?.execution_timestamp}
        />

        {/* Pending Review Alert */}
        {(() => {
          const prepStatus = runDetail?.agents?.preparation?.status;
          const isPendingReview = prepStatus === "pending_review" || 
            (prepStatus === "success" && runDetail?.agents?.drawcore?.status === "pending");
          return isPendingReview && (
            <Card className="border-amber-300 bg-amber-50">
              <CardContent className="py-4">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-amber-100 flex items-center justify-center">
                    <AlertCircle className="h-5 w-5 text-amber-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-amber-900">Review Required</h3>
                    <p className="text-sm text-amber-700">
                      Please review the extracted fields before continuing to write them to Encompass
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })()}

        {/* Tabs */}
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="bg-muted/50">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="timeline">Timeline</TabsTrigger>
            <TabsTrigger value="report">Report</TabsTrigger>
            <TabsTrigger value="documents">Documents</TabsTrigger>
            <TabsTrigger value="fields" className="relative">
              Fields
              {runDetail?.agents?.preparation?.status === "pending_review" && (
                <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <OverviewTab
              runDetail={runDetail}
              isLoading={isLoading && !runDetail}
              agentType="drawdocs"
            />
          </TabsContent>

          <TabsContent value="timeline">
            <TimelineTab
              runDetail={runDetail}
              isLoading={isLoading && !runDetail}
              agentType="drawdocs"
            />
          </TabsContent>

          <TabsContent value="report">
            <FinalReportTab
              runDetail={runDetail}
              isLoading={isLoading && !runDetail}
              agentType="drawdocs"
            />
          </TabsContent>

          <TabsContent value="documents">
            <DocumentsTabPlaceholder />
          </TabsContent>

          <TabsContent value="fields">
            <FieldReviewTab
              runDetail={runDetail}
              runId={runId}
              isLoading={isLoading && !runDetail}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

