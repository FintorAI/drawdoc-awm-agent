"use client";

/**
 * React Query hooks for runs data fetching
 * 
 * Features:
 * - Automatic polling every 2 seconds to catch live status updates
 * - Loading, error, and success states
 * - Automatic refetch on window focus
 * - Support for agent type filtering
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getRuns, getRunDetail, createRun, type RunSummary, type RunDetail, type CreateRunRequest, type CreateRunResponse } from '@/lib/api';
import type { AgentType } from '@/types/agents';
import { getSubAgentIds } from '@/types/agents';

// Query keys for cache management
export const queryKeys = {
  runs: (agentType?: AgentType) => agentType ? ['runs', agentType] : ['runs'] as const,
  allRuns: ['runs'] as const,
  runDetail: (runId: string) => ['runs', 'detail', runId] as const,
};

// =============================================================================
// RUNS LIST HOOK
// =============================================================================

interface UseRunsOptions {
  /** Filter by agent type (optional) */
  agentType?: AgentType;
  /** Polling interval in milliseconds (default: 2000) */
  refetchInterval?: number;
  /** Whether to enable polling (default: true) */
  enabled?: boolean;
}

/**
 * Hook to fetch and poll the list of runs.
 * Optionally filtered by agent type.
 * Polls every 2 seconds by default to catch live status updates.
 */
export function useRuns(options: UseRunsOptions = {}) {
  const { agentType, refetchInterval = 2000, enabled = true } = options;

  return useQuery({
    queryKey: queryKeys.runs(agentType),
    queryFn: () => getRuns(agentType),
    refetchInterval,
    refetchIntervalInBackground: false, // Only poll when tab is focused
    refetchOnWindowFocus: true,
    staleTime: 1000, // Consider data stale after 1 second
    enabled,
  });
}

/**
 * Hook to fetch runs for a specific agent type.
 */
export function useAgentRuns(agentType: AgentType, options: Omit<UseRunsOptions, 'agentType'> = {}) {
  return useRuns({ ...options, agentType });
}

// =============================================================================
// RUN DETAIL HOOK
// =============================================================================

interface UseRunDetailOptions {
  /** Polling interval in milliseconds (default: 2000) */
  refetchInterval?: number;
  /** Whether to enable the query (default: true) */
  enabled?: boolean;
}

/**
 * Hook to fetch and poll a single run's details.
 * Polls every 2 seconds by default for live status updates.
 * Stops polling once all agents are complete (success, failed, or blocked).
 */
export function useRunDetail(runId: string | null, options: UseRunDetailOptions = {}) {
  const { refetchInterval = 2000, enabled = true } = options;

  return useQuery({
    queryKey: queryKeys.runDetail(runId || ''),
    queryFn: () => getRunDetail(runId!),
    enabled: enabled && !!runId,
    refetchInterval: (query) => {
      // Stop polling if run is complete
      const data = query.state.data as RunDetail | undefined;
      if (data) {
        // Get the sub-agents for this run's agent type
        const agentType = data.agent_type || 'drawdocs';
        const subAgentIds = getSubAgentIds(agentType);
        
        // Check if all agents are done
        const allAgentsDone = subAgentIds.every(agentId => {
          const status = data.agents[agentId]?.status || 'pending';
          return ['success', 'failed', 'blocked'].includes(status);
        });
        
        if (allAgentsDone) {
          return false; // Stop polling
        }
      }
      return refetchInterval;
    },
    refetchOnWindowFocus: true,
    staleTime: 1000,
  });
}

// =============================================================================
// CREATE RUN MUTATION
// =============================================================================

interface UseCreateRunOptions {
  /** Called on successful run creation */
  onSuccess?: (data: CreateRunResponse) => void;
  /** Called on error */
  onError?: (error: Error) => void;
}

/**
 * Hook to create a new agent run.
 * Automatically invalidates the runs list cache on success.
 */
export function useCreateRun(options: UseCreateRunOptions = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createRun,
    onSuccess: (data) => {
      // Invalidate all runs queries to trigger refetch
      queryClient.invalidateQueries({ queryKey: queryKeys.allRuns });
      // Also invalidate the specific agent type runs
      if (data.agent_type) {
        queryClient.invalidateQueries({ queryKey: queryKeys.runs(data.agent_type) });
      }
      options.onSuccess?.(data);
    },
    onError: (error: Error) => {
      options.onError?.(error);
    },
  });
}

// =============================================================================
// UTILITY HOOKS
// =============================================================================

/**
 * Check if any runs are currently in progress.
 * Useful for determining if we should show activity indicators.
 */
export function useHasRunningRuns(agentType?: AgentType): boolean {
  const { data: runs } = useRuns({ agentType });
  return runs?.some(run => run.status === 'running') ?? false;
}

/**
 * Get runs filtered by status.
 */
export function useFilteredRuns(status?: RunSummary['status'] | 'all', agentType?: AgentType) {
  const { data: runs, ...rest } = useRuns({ agentType });
  
  const filteredRuns = runs?.filter(run => {
    if (!status || status === 'all') return true;
    return run.status === status;
  }) ?? [];

  return { data: filteredRuns, ...rest };
}
