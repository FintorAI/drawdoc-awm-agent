"use client";

import { useQuery } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { AgentHub } from "@/components/dashboard/agent-hub";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { getRuns } from "@/lib/api";

export default function DashboardPage() {
  const { data: runs, isLoading } = useQuery({
    queryKey: ["runs"],
    queryFn: () => getRuns(),
    refetchInterval: 5000, // Poll every 5 seconds
  });

  return (
    <div className="flex flex-col">
      <Header 
        title="Agent Hub" 
        subtitle="Select an agent to view its dashboard and runs"
      />
      
      <div className="px-8 pb-8 space-y-8">
        {/* Agent Tiles */}
        <section>
          <h2 className="text-lg font-semibold text-foreground mb-4">Agents</h2>
          <AgentHub runs={runs} isLoading={isLoading} />
        </section>

        {/* Recent Activity */}
        <section>
          <ActivityFeed runs={runs} isLoading={isLoading} maxItems={10} />
        </section>
      </div>
    </div>
  );
}
