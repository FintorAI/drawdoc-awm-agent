"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { getRunDetail } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Legacy run detail page - redirects to the appropriate agent-specific route.
 * Fetches the run to determine its agent type, then redirects accordingly.
 */
export default function LegacyRunDetailPage() {
  const params = useParams();
  const router = useRouter();
  const runId = params.runId as string;

  useEffect(() => {
    async function redirectToAgentRun() {
      try {
        const runDetail = await getRunDetail(runId);
        const agentType = runDetail.agent_type || "drawdocs";
        
        // Redirect to the appropriate agent-specific run detail page
        router.replace(`/${agentType}/runs/${runId}`);
      } catch (error) {
        // If we can't fetch the run, default to dashboard
        router.replace("/dashboard");
      }
    }

    redirectToAgentRun();
  }, [runId, router]);

  // Show loading state while redirecting
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <div className="space-y-4 text-center">
        <Skeleton className="h-8 w-48 mx-auto" />
        <p className="text-muted-foreground">Redirecting...</p>
      </div>
    </div>
  );
}
