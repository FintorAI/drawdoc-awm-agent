/**
 * API client for the Multi-Agent Dashboard backend
 * 
 * Supports DrawDocs, Disclosure, and LOA agent pipelines.
 */

import type { AgentType } from "@/types/agents";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// =============================================================================
// TYPES
// =============================================================================

export type RunStatusValue = "running" | "success" | "failed" | "blocked";
export type AgentStatusValue = "pending" | "running" | "success" | "failed" | "blocked";

export interface AgentResultDetail {
  status: AgentStatusValue;
  attempts: number;
  elapsed_seconds: number;
  output: unknown;
  error: string | null;
}

export interface ProgressData {
  documents_found: number;
  documents_processed: number;
  fields_extracted: number;
  current_document: string | null;
}

export interface LogEntry {
  timestamp: string;
  level: "info" | "warning" | "error" | "success";
  agent: string;
  message: string;
  event_type?: string;
  details?: Record<string, unknown>;
}

export interface CorrectedFieldSummary {
  field_id: string;
  field_name: string;
  corrected_value: string;
  source_document: string | null;
  document_filename: string;
}

export interface RunSummary {
  run_id: string;
  loan_id: string;
  agent_type: AgentType;
  status: RunStatusValue;
  demo_mode: boolean;
  created_at: string;
  duration_seconds: number;
  documents_processed: number;
  documents_found: number;
  /** Flexible agents dict - keys depend on agent_type */
  agents: Record<string, AgentStatusValue>;
}

export interface RunDetail {
  loan_id: string;
  run_id: string;
  agent_type: AgentType;
  execution_timestamp: string;
  demo_mode: boolean;
  config?: {
    document_types: string[] | null;
    max_retries: number;
  };
  summary: Record<string, unknown>;
  /** Flexible agents dict - keys depend on agent_type */
  agents: Record<string, AgentResultDetail>;
  logs?: LogEntry[];
  progress?: ProgressData;
  overall_status?: RunStatusValue;
  total_duration_seconds?: number;
  completed_at?: string;
  summary_text?: string;
  corrected_fields_summary?: CorrectedFieldSummary[];
  // Disclosure-specific fields
  blocking_issues?: string[];
  tracking_id?: string | null;
}

export interface CreateRunRequest {
  loan_id: string;
  agent_type?: AgentType;
  demo_mode?: boolean;
  max_retries?: number;
  document_types?: string[] | null;
}

export interface CreateRunResponse {
  run_id: string;
  agent_type: AgentType;
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

/**
 * Fetch all runs, optionally filtered by agent type
 */
export async function getRuns(agentType?: AgentType): Promise<RunSummary[]> {
  const url = new URL(`${API_BASE_URL}/api/runs`);
  if (agentType) {
    url.searchParams.set("agent_type", agentType);
  }
  
  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`Failed to fetch runs: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch runs for a specific agent type
 */
export async function getRunsByAgentType(agentType: AgentType): Promise<RunSummary[]> {
  return getRuns(agentType);
}

/**
 * Fetch a single run's details
 */
export async function getRunDetail(runId: string): Promise<RunDetail> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch run detail: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Create a new run
 */
export async function createRun(request: CreateRunRequest): Promise<CreateRunResponse> {
  const response = await fetch(`${API_BASE_URL}/api/runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Failed to create run: ${response.statusText}`);
  }
  return response.json();
}

