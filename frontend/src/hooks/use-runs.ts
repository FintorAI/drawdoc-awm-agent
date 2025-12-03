"use client";

/**
 * React Query hooks for runs data fetching
 * 
 * Features:
 * - Automatic polling every 2 seconds to catch live status updates
 * - Loading, error, and success states
 * - Automatic refetch on window focus
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getRuns, getRunDetail, createRun, type RunSummary, type RunDetail, type CreateRunRequest } from '@/lib/api';

// Query keys for cache management
export const queryKeys = {
  runs: ['runs'] as const,
  runDetail: (runId: string) => ['runs', runId] as const,
};

// =============================================================================
// RUNS LIST HOOK
// =============================================================================

interface UseRunsOptions {
  /** Polling interval in milliseconds (default: 2000) */
  refetchInterval?: number;
  /** Whether to enable polling (default: true) */
  enabled?: boolean;
}

/**
 * Hook to fetch and poll the list of all runs.
 * Polls every 2 seconds by default to catch live status updates.
 */
export function useRuns(options: UseRunsOptions = {}) {
  const { refetchInterval = 2000, enabled = true } = options;

  return useQuery({
    queryKey: queryKeys.runs,
    queryFn: getRuns,
    refetchInterval,
    refetchIntervalInBackground: false, // Only poll when tab is focused
    refetchOnWindowFocus: true,
    staleTime: 1000, // Consider data stale after 1 second
    enabled,
  });
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
 * Stops polling once the run is complete (success or failed).
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
        const allAgentsDone = ['success', 'failed'].includes(data.agents.preparation?.status || 'pending') &&
                              ['success', 'failed'].includes(data.agents.verification?.status || 'pending') &&
                              ['success', 'failed'].includes(data.agents.orderdocs?.status || 'pending');
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
  onSuccess?: (data: { run_id: string }) => void;
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
      // Invalidate runs list to trigger refetch
      queryClient.invalidateQueries({ queryKey: queryKeys.runs });
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
export function useHasRunningRuns(): boolean {
  const { data: runs } = useRuns();
  return runs?.some(run => run.status === 'running') ?? false;
}

/**
 * Get runs filtered by status.
 */
export function useFilteredRuns(status?: RunSummary['status'] | 'all') {
  const { data: runs, ...rest } = useRuns();
  
  const filteredRuns = runs?.filter(run => {
    if (!status || status === 'all') return true;
    return run.status === status;
  }) ?? [];

  return { data: filteredRuns, ...rest };
}

