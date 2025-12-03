"use client";

import * as React from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { RunTriggerForm } from "@/components/runs/run-trigger-form";
import { RunFilters, type FilterStatus } from "@/components/runs/run-filters";
import { RunListItem, RunListItemCard } from "@/components/runs/run-list-item";
import { Plus, RefreshCw, Inbox, AlertTriangle, ChevronLeft } from "lucide-react";
import { useAgentRuns } from "@/hooks/use-runs";
import { DRAWDOCS_CONFIG } from "@/types/agents";
import type { RunSummary } from "@/lib/api";

// =============================================================================
// EMPTY STATE
// =============================================================================

interface EmptyStateProps {
  onNewRun: () => void;
  hasFilters: boolean;
}

function EmptyState({ onNewRun, hasFilters }: EmptyStateProps) {
  if (hasFilters) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center mb-4">
          <Inbox className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-medium mb-2">No runs match your filters</h3>
        <p className="text-muted-foreground mb-4">
          Try adjusting your filters or search query
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center mb-4">
        <Inbox className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-medium mb-2">No DrawDocs runs yet</h3>
      <p className="text-muted-foreground mb-6">
        Start your first document processing run to see it here
      </p>
      <Button onClick={onNewRun}>
        <Plus className="h-4 w-4 mr-2" />
        Start your first run
      </Button>
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
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="h-16 w-16 rounded-full bg-red-100 flex items-center justify-center mb-4">
        <AlertTriangle className="h-8 w-8 text-red-600" />
      </div>
      <h3 className="text-lg font-medium mb-2">Failed to load runs</h3>
      <p className="text-muted-foreground mb-2">{error.message}</p>
      <p className="text-sm text-muted-foreground mb-6">
        Make sure the backend server is running on port 8000
      </p>
      <Button onClick={onRetry} variant="outline">
        <RefreshCw className="h-4 w-4 mr-2" />
        Retry
      </Button>
    </div>
  );
}

// =============================================================================
// LOADING SKELETON
// =============================================================================

function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex items-center gap-4 p-4 rounded-lg border border-border">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-6 w-20 rounded-full" />
          <Skeleton className="h-3 w-16 hidden sm:block" />
          <Skeleton className="h-4 w-16 hidden md:block" />
          <Skeleton className="h-4 w-14" />
          <Skeleton className="h-4 w-24 hidden lg:block" />
          <Skeleton className="h-5 w-5 ml-auto" />
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// MAIN PAGE COMPONENT
// =============================================================================

export default function DrawDocsRunsPage() {
  const [isNewRunOpen, setIsNewRunOpen] = React.useState(false);
  const [statusFilter, setStatusFilter] = React.useState<FilterStatus>("all");
  const [searchQuery, setSearchQuery] = React.useState("");

  const { data: runs, isLoading, error, refetch } = useAgentRuns("drawdocs");

  // Filter runs based on status and search query
  const filteredRuns = React.useMemo(() => {
    if (!runs) return [];

    return runs.filter((run) => {
      // Status filter
      if (statusFilter !== "all" && run.status !== statusFilter) {
        return false;
      }

      // Search filter (by loan ID)
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        if (!run.loan_id.toLowerCase().includes(query) &&
            !run.run_id.toLowerCase().includes(query)) {
          return false;
        }
      }

      return true;
    });
  }, [runs, statusFilter, searchQuery]);

  const handleRunSuccess = () => {
    setIsNewRunOpen(false);
  };

  const hasActiveFilters = statusFilter !== "all" || searchQuery.length > 0;

  return (
    <div className="flex flex-col">
      <Header 
        title="DrawDocs Runs"
        subtitle="Document processing run history"
        actions={
          <div className="flex items-center gap-2">
            <Link href="/drawdocs">
              <Button variant="outline" size="sm">
                <ChevronLeft className="h-4 w-4 mr-1" />
                Overview
              </Button>
            </Link>
            <Sheet open={isNewRunOpen} onOpenChange={setIsNewRunOpen}>
              <Button onClick={() => setIsNewRunOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                New Run
              </Button>
              <SheetContent side="right" className="w-full sm:max-w-xl overflow-y-auto">
                <SheetHeader className="mb-6">
                  <SheetTitle>Start New DrawDocs Run</SheetTitle>
                  <SheetDescription>
                    Configure and trigger a new document processing run
                  </SheetDescription>
                </SheetHeader>
                <RunTriggerForm 
                  onSuccess={handleRunSuccess}
                  agentType="drawdocs"
                  className="border-0 shadow-none"
                />
              </SheetContent>
            </Sheet>
          </div>
        }
      />
      
      <div className="px-8 pb-8">
        {/* Runs List Card */}
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <CardTitle>Run History</CardTitle>
                <CardDescription>
                  {runs && runs.length > 0 
                    ? "Click on a run to view details"
                    : "DrawDocs runs will appear here"
                  }
                </CardDescription>
              </div>
              {!isLoading && !error && runs && runs.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => refetch()}
                  className="self-start"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {/* Filters */}
            {!isLoading && !error && runs && runs.length > 0 && (
              <RunFilters
                status={statusFilter}
                onStatusChange={setStatusFilter}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                totalRuns={runs.length}
                filteredRuns={filteredRuns.length}
                className="mb-4"
              />
            )}

            {/* Content */}
            {isLoading && <LoadingSkeleton />}

            {error && <ErrorState error={error} onRetry={() => refetch()} />}

            {!isLoading && !error && runs && runs.length === 0 && (
              <EmptyState onNewRun={() => setIsNewRunOpen(true)} hasFilters={false} />
            )}

            {!isLoading && !error && runs && runs.length > 0 && filteredRuns.length === 0 && (
              <EmptyState onNewRun={() => setIsNewRunOpen(true)} hasFilters={hasActiveFilters} />
            )}

            {!isLoading && !error && filteredRuns.length > 0 && (
              <>
                {/* Desktop: List view */}
                <div className="hidden md:block space-y-2">
                  {filteredRuns.map((run) => (
                    <RunListItem key={run.run_id} run={run} basePath="/drawdocs/runs" />
                  ))}
                </div>

                {/* Mobile: Card view */}
                <div className="md:hidden space-y-3">
                  {filteredRuns.map((run) => (
                    <RunListItemCard key={run.run_id} run={run} basePath="/drawdocs/runs" />
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

