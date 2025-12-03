"use client";

import { useMemo } from "react";
import { AgentTile } from "./agent-tile";
import { AGENT_CONFIGS, type AgentType } from "@/types/agents";
import type { RunSummary } from "@/lib/api";

interface AgentHubProps {
  runs?: RunSummary[];
  isLoading?: boolean;
}

export function AgentHub({ runs, isLoading }: AgentHubProps) {
  // Calculate stats for each agent type
  const agentStats = useMemo(() => {
    if (!runs) return {};
    
    const stats: Record<AgentType, {
      runsToday: number;
      inProgress: number;
      successRate: number;
      alerts: number;
    }> = {
      drawdocs: { runsToday: 0, inProgress: 0, successRate: 0, alerts: 0 },
      disclosure: { runsToday: 0, inProgress: 0, successRate: 0, alerts: 0 },
      loa: { runsToday: 0, inProgress: 0, successRate: 0, alerts: 0 },
    };
    
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    // Group runs by agent type and calculate stats
    runs.forEach((run) => {
      const agentType = run.agent_type || "drawdocs"; // Default to drawdocs for backwards compatibility
      const runDate = new Date(run.created_at);
      
      // Check if run is from today
      if (runDate >= today) {
        stats[agentType].runsToday++;
      }
      
      // Count in-progress runs
      if (run.status === "running") {
        stats[agentType].inProgress++;
      }
      
      // Count blocked/failed as alerts
      if (run.status === "blocked" || run.status === "failed") {
        stats[agentType].alerts++;
      }
    });
    
    // Calculate success rates
    Object.keys(stats).forEach((type) => {
      const agentType = type as AgentType;
      const agentRuns = runs.filter((r) => (r.agent_type || "drawdocs") === agentType);
      const completed = agentRuns.filter((r) => r.status !== "running");
      const successful = completed.filter((r) => r.status === "success");
      
      if (completed.length > 0) {
        stats[agentType].successRate = (successful.length / completed.length) * 100;
      }
    });
    
    return stats;
  }, [runs]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {AGENT_CONFIGS.map((config) => (
        <AgentTile
          key={config.id}
          config={config}
          stats={agentStats[config.id]}
          isLoading={isLoading}
        />
      ))}
    </div>
  );
}

