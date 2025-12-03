"use client";

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ChevronRight, Inbox } from "lucide-react";
import { cn } from "@/lib/utils";
import { AGENT_CONFIG_MAP, type AgentType } from "@/types/agents";
import type { RunSummary } from "@/lib/api";

interface ActivityFeedProps {
  runs?: RunSummary[];
  isLoading?: boolean;
  maxItems?: number;
}

function AgentTypeBadge({ agentType }: { agentType: AgentType }) {
  const config = AGENT_CONFIG_MAP[agentType];
  const Icon = config.icon;
  
  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded",
      config.bgColor,
      config.textColor
    )}>
      <Icon className="h-3 w-3" />
      {config.name}
    </span>
  );
}

function ActivityItem({ run }: { run: RunSummary }) {
  const agentType = run.agent_type || "drawdocs";
  const config = AGENT_CONFIG_MAP[agentType];
  const timeAgo = formatDistanceToNow(new Date(run.created_at), { addSuffix: true });
  
  // Truncate loan ID for display
  const displayLoanId = run.loan_id.length > 12 
    ? `${run.loan_id.slice(0, 8)}...` 
    : run.loan_id;
  
  return (
    <Link 
      href={`${config.route}/runs/${run.run_id}`}
      className="flex items-center justify-between py-3 px-4 hover:bg-muted/50 rounded-lg transition-colors group"
    >
      <div className="flex items-center gap-4 min-w-0">
        <AgentTypeBadge agentType={agentType} />
        
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground truncate">
            {displayLoanId}
          </p>
          <p className="text-xs text-muted-foreground">
            {timeAgo}
          </p>
        </div>
      </div>
      
      <div className="flex items-center gap-3">
        <StatusBadge
          variant={run.status === "success" ? "success" : 
                   run.status === "running" ? "processing" :
                   run.status === "blocked" ? "warning" : "error"}
          size="sm"
        >
          {run.status === "success" && "Success"}
          {run.status === "running" && "Running"}
          {run.status === "blocked" && "Blocked"}
          {run.status === "failed" && "Failed"}
        </StatusBadge>
        
        <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
      </div>
    </Link>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex items-center justify-between py-3 px-4">
          <div className="flex items-center gap-4">
            <Skeleton className="h-5 w-20 rounded" />
            <div className="space-y-1">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-16" />
            </div>
          </div>
          <Skeleton className="h-5 w-16 rounded-full" />
        </div>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-3">
        <Inbox className="h-6 w-6 text-muted-foreground" />
      </div>
      <p className="text-sm font-medium text-foreground">No recent activity</p>
      <p className="text-xs text-muted-foreground mt-1">
        Runs will appear here when you start processing
      </p>
    </div>
  );
}

export function ActivityFeed({ runs, isLoading, maxItems = 10 }: ActivityFeedProps) {
  const displayRuns = runs?.slice(0, maxItems) ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
        <CardDescription>Latest runs across all agents</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <LoadingSkeleton />
        ) : displayRuns.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-1">
            {displayRuns.map((run) => (
              <ActivityItem key={run.run_id} run={run} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

