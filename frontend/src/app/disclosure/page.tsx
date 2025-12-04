"use client";

import * as React from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { RunTriggerForm } from "@/components/runs/run-trigger-form";
import { Plus, CheckCircle2, Clock, ArrowRight, Shield, AlertTriangle, Calendar } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useAgentRuns } from "@/hooks/use-runs";
import { DISCLOSURE_CONFIG } from "@/types/agents";
import type { RunSummary } from "@/lib/api";

// =============================================================================
// DISCLOSURE-SPECIFIC STATS CARDS
// =============================================================================

interface StatsCardsProps {
  runs: RunSummary[];
  isLoading: boolean;
}

function StatsCards({ runs, isLoading }: StatsCardsProps) {
  const stats = React.useMemo(() => {
    if (!runs.length) {
      return {
        lesSentToday: 0,
        inProgress: 0,
        successRate: 0,
        avgProcessingTime: 0,
      };
    }

    // Calculate date for "today" (last 24 hours)
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);

    // Filter today's runs
    const todayRuns = runs.filter(r => {
      const createdAt = new Date(r.created_at);
      return createdAt >= yesterday;
    });
    
    const lesSentToday = todayRuns.filter(r => r.status === "success").length;
    const inProgress = runs.filter(r => r.status === "running").length;
    
    // Success rate (exclude running)
    const completedRuns = runs.filter(r => r.status !== "running");
    const successfulRuns = completedRuns.filter(r => r.status === "success");
    const successRate = completedRuns.length > 0 
      ? (successfulRuns.length / completedRuns.length) * 100 
      : 0;
    
    // Average processing time (for completed runs)
    const avgProcessingTime = completedRuns.length > 0
      ? completedRuns.reduce((sum, r) => sum + (r.duration_seconds || 0), 0) / completedRuns.length
      : 0;

    return { lesSentToday, inProgress, successRate, avgProcessingTime };
  }, [runs]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <Skeleton className="h-10 w-10 rounded-lg" />
                <div className="space-y-2">
                  <Skeleton className="h-6 w-12" />
                  <Skeleton className="h-4 w-24" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {/* LEs Sent Today */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-emerald-100 flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-2xl font-semibold">{stats.lesSentToday}</p>
              <p className="text-sm text-muted-foreground">LEs Sent Today</p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* In Progress */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <Clock className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-semibold">{stats.inProgress}</p>
              <p className="text-sm text-muted-foreground">In Progress</p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Success Rate */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <Shield className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-semibold">{stats.successRate.toFixed(1)}%</p>
              <p className="text-sm text-muted-foreground">Success Rate</p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Avg Processing Time */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-purple-100 flex items-center justify-center">
              <Clock className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-semibold">
                {stats.avgProcessingTime >= 60 
                  ? `${(stats.avgProcessingTime / 60).toFixed(1)}m`
                  : `${Math.round(stats.avgProcessingTime)}s`}
              </p>
              <p className="text-sm text-muted-foreground">Avg Time</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// =============================================================================
// TRID INFO CARD
// =============================================================================

function TridInfoCard() {
  return (
    <Card className="border-blue-200 bg-blue-50/50">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-blue-600" />
          <CardTitle className="text-blue-900">TRID Compliance</CardTitle>
        </div>
        <CardDescription className="text-blue-700">
          Loan Estimate must be sent within 3 business days of application
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="text-sm text-blue-800 space-y-2">
          <p>• <strong>3-Day Rule:</strong> LE due within 3 business days of app date</p>
          <p>• <strong>Hard Stops:</strong> Missing phone/email blocks disclosure</p>
          <p>• <strong>15-Day Rule:</strong> Closing date ≥ 15 days from app/lock</p>
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// RECENT RUNS
// =============================================================================

interface RecentRunsProps {
  runs: RunSummary[];
  isLoading: boolean;
}

function RecentRuns({ runs, isLoading }: RecentRunsProps) {
  const recentRuns = runs.slice(0, 5);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex items-center justify-between py-2">
            <div className="flex items-center gap-4">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-5 w-16 rounded-full" />
            </div>
            <Skeleton className="h-4 w-20" />
          </div>
        ))}
      </div>
    );
  }

  if (recentRuns.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p>No disclosure runs yet. Start your first LE disclosure run!</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {recentRuns.map((run) => (
        <Link
          key={run.run_id}
          href={`/disclosure/runs/${run.run_id}`}
          className="flex items-center justify-between py-3 px-4 hover:bg-muted/50 rounded-lg transition-colors group"
        >
          <div className="flex items-center gap-4">
            <span className="text-sm font-mono text-muted-foreground">
              {run.loan_id.slice(0, 8)}...
            </span>
            <StatusBadge
              variant={run.status === "success" ? "success" : 
                       run.status === "running" ? "processing" :
                       run.status === "blocked" ? "warning" : "error"}
              size="sm"
            >
              {run.status}
            </StatusBadge>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
            </span>
            <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
          </div>
        </Link>
      ))}
    </div>
  );
}

// =============================================================================
// MAIN PAGE
// =============================================================================

export default function DisclosurePage() {
  const [isNewRunOpen, setIsNewRunOpen] = React.useState(false);
  const { data: runs, isLoading } = useAgentRuns("disclosure");

  const handleRunSuccess = () => {
    setIsNewRunOpen(false);
  };

  return (
    <div className="flex flex-col">
      <Header 
        title={DISCLOSURE_CONFIG.name}
        subtitle={DISCLOSURE_CONFIG.description}
        actions={
          <Sheet open={isNewRunOpen} onOpenChange={setIsNewRunOpen}>
            <Button onClick={() => setIsNewRunOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Run
            </Button>
            <SheetContent side="right" className="w-full sm:max-w-xl overflow-y-auto">
              <SheetHeader className="mb-6">
                <SheetTitle>Start New Disclosure Run</SheetTitle>
                <SheetDescription>
                  Process Loan Estimate disclosure for a loan
                </SheetDescription>
              </SheetHeader>
              <RunTriggerForm 
                onSuccess={handleRunSuccess}
                agentType="disclosure"
                className="border-0 shadow-none"
              />
            </SheetContent>
          </Sheet>
        }
      />
      
      <div className="px-8 pb-8 space-y-6">
        {/* Stats */}
        <StatsCards runs={runs || []} isLoading={isLoading} />

        {/* Sub-agents Pipeline Overview */}
        <Card>
          <CardHeader>
            <CardTitle>Pipeline</CardTitle>
            <CardDescription>Disclosure 3-stage LE processing pipeline</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between gap-4">
              {DISCLOSURE_CONFIG.subAgents.map((agent, index) => {
                const Icon = agent.icon;
                return (
                  <React.Fragment key={agent.id}>
                    <div className="flex flex-col items-center text-center">
                      <div className={`h-12 w-12 rounded-xl flex items-center justify-center bg-${agent.color}-100`}>
                        <Icon className={`h-6 w-6 text-${agent.color}-600`} />
                      </div>
                      <span className="text-sm font-medium mt-2">{agent.name}</span>
                      <span className="text-xs text-muted-foreground">{agent.description}</span>
                    </div>
                    {index < DISCLOSURE_CONFIG.subAgents.length - 1 && (
                      <ArrowRight className="h-5 w-5 text-muted-foreground shrink-0" />
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* TRID Info */}
        <TridInfoCard />

        {/* Recent Runs */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Runs</CardTitle>
              <CardDescription>Latest Disclosure processing runs</CardDescription>
            </div>
            <Link href="/disclosure/runs">
              <Button variant="outline" size="sm">
                View All
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            <RecentRuns runs={runs || []} isLoading={isLoading} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

