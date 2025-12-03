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
import { useRunDetail } from "@/hooks/use-runs";
import { AlertTriangle, RefreshCw, ChevronLeft, Shield, Calendar, AlertCircle } from "lucide-react";

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
        {/* Agent Cards skeleton - 3 for disclosure */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
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
        <Link href="/disclosure/runs">
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
// DISCLOSURE-SPECIFIC COMPLIANCE TAB
// =============================================================================

interface ComplianceTabProps {
  runDetail: any;
  isLoading: boolean;
}

function ComplianceTab({ runDetail, isLoading }: ComplianceTabProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {[...Array(3)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-3">
              <Skeleton className="h-4 w-32" />
            </CardHeader>
            <CardContent className="space-y-3">
              <Skeleton className="h-8 w-24" />
              <Skeleton className="h-4 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  // Extract disclosure-specific data
  const verificationOutput = runDetail?.agents?.verification?.output || {};
  const sendOutput = runDetail?.agents?.send?.output || {};
  const blockingIssues = runDetail?.blocking_issues || [];
  const tridCompliance = verificationOutput?.trid_compliance || {};
  const hardStopCheck = verificationOutput?.hard_stop_check || {};
  const maventResult = sendOutput?.mavent_result || {};
  const atrQmResult = sendOutput?.atr_qm_result || {};

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* TRID Compliance */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-blue-600" />
            <CardTitle className="text-base">TRID Compliance</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Status</span>
            <span className={`text-sm font-medium ${tridCompliance.compliant ? 'text-emerald-600' : 'text-amber-600'}`}>
              {tridCompliance.compliant ? 'Compliant' : 'Attention Required'}
            </span>
          </div>
          {tridCompliance.application_date && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">App Date</span>
              <span className="text-sm">{tridCompliance.application_date}</span>
            </div>
          )}
          {tridCompliance.le_due_date && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">LE Due Date</span>
              <span className="text-sm">{tridCompliance.le_due_date}</span>
            </div>
          )}
          {tridCompliance.days_remaining !== undefined && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Days Remaining</span>
              <span className={`text-sm font-medium ${tridCompliance.days_remaining <= 1 ? 'text-amber-600' : 'text-emerald-600'}`}>
                {tridCompliance.days_remaining} days
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Hard Stops */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-blue-600" />
            <CardTitle className="text-base">Hard Stop Checks</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Status</span>
            <span className={`text-sm font-medium ${!hardStopCheck.has_hard_stops ? 'text-emerald-600' : 'text-red-600'}`}>
              {!hardStopCheck.has_hard_stops ? 'All Clear' : 'BLOCKED'}
            </span>
          </div>
          <div className="text-sm text-muted-foreground">
            <p>• Phone: {hardStopCheck.phone_present !== false ? '✓ Present' : '✗ Missing'}</p>
            <p>• Email: {hardStopCheck.email_present !== false ? '✓ Present' : '✗ Missing'}</p>
          </div>
        </CardContent>
      </Card>

      {/* Mavent Check */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-purple-600" />
            <CardTitle className="text-base">Mavent Compliance</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Status</span>
            <span className={`text-sm font-medium ${maventResult.passed ? 'text-emerald-600' : 'text-amber-600'}`}>
              {maventResult.passed ? 'PASSED' : `${maventResult.total_issues || 0} Issues`}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* ATR/QM Check */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <CardTitle className="text-base">ATR/QM Flags</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Status</span>
            <span className={`text-sm font-medium ${atrQmResult.passed ? 'text-emerald-600' : 'text-red-600'}`}>
              {atrQmResult.passed ? 'No Red Flags' : 'Red Flags Detected'}
            </span>
          </div>
          {atrQmResult.red_flags?.length > 0 && (
            <div className="text-sm text-red-600">
              {atrQmResult.red_flags.map((flag: string, i: number) => (
                <p key={i}>• {flag}</p>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Blocking Issues */}
      {blockingIssues.length > 0 && (
        <Card className="lg:col-span-2 border-red-200 bg-red-50/50">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-600" />
              <CardTitle className="text-base text-red-900">Blocking Issues</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1">
              {blockingIssues.map((issue: string, i: number) => (
                <li key={i} className="text-sm text-red-800">• {issue}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// =============================================================================
// MAIN PAGE COMPONENT
// =============================================================================

export default function DisclosureRunDetailPage() {
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
        backPath="/disclosure/runs"
      />

      <div className="px-8 pb-8 space-y-6">
        {/* Agent Status Cards */}
        <AgentStatusCards
          agents={runDetail?.agents}
          agentType="disclosure"
          isLoading={isLoading && !runDetail}
          executionTimestamp={runDetail?.execution_timestamp}
        />

        {/* Tabs */}
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="bg-muted/50">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="timeline">Timeline</TabsTrigger>
            <TabsTrigger value="compliance">Compliance</TabsTrigger>
            <TabsTrigger value="report">Report</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <OverviewTab
              runDetail={runDetail}
              isLoading={isLoading && !runDetail}
            />
          </TabsContent>

          <TabsContent value="timeline">
            <TimelineTab
              runDetail={runDetail}
              isLoading={isLoading && !runDetail}
            />
          </TabsContent>

          <TabsContent value="compliance">
            <ComplianceTab
              runDetail={runDetail}
              isLoading={isLoading && !runDetail}
            />
          </TabsContent>

          <TabsContent value="report">
            <FinalReportTab
              runDetail={runDetail}
              isLoading={isLoading && !runDetail}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

