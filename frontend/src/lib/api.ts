/**
 * API client for the DrawDoc Agent backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// =============================================================================
// TYPES
// =============================================================================

export type RunStatusValue = "running" | "success" | "failed";
export type AgentStatusValue = "pending" | "running" | "success" | "failed";

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
  status: RunStatusValue;
  demo_mode: boolean;
  created_at: string;
  duration_seconds: number;
  documents_processed: number;
  documents_found: number;
  agents: {
    preparation: AgentStatusValue;
    drawcore: AgentStatusValue;
    verification: AgentStatusValue;
    orderdocs: AgentStatusValue;
  };
}

export interface RunDetail {
  loan_id: string;
  run_id: string;
  execution_timestamp: string;
  demo_mode: boolean;
  config?: {
    document_types: string[] | null;
    max_retries: number;
  };
  summary: Record<string, unknown>;
  agents: {
    preparation?: AgentResultDetail;
    drawcore?: AgentResultDetail;
    verification?: AgentResultDetail;
    orderdocs?: AgentResultDetail;
  };
  logs?: LogEntry[];
  progress?: ProgressData;
  overall_status?: RunStatusValue;
  total_duration_seconds?: number;
  completed_at?: string;
  summary_text?: string;
  corrected_fields_summary?: CorrectedFieldSummary[];
}

export interface CreateRunRequest {
  loan_id: string;
  demo_mode?: boolean;
  max_retries?: number;
  document_types?: string[] | null;
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

/**
 * Fetch all runs
 */
export async function getRuns(): Promise<RunSummary[]> {
  const response = await fetch(`${API_BASE_URL}/api/runs`);
  if (!response.ok) {
    throw new Error(`Failed to fetch runs: ${response.statusText}`);
  }
  return response.json();
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
export async function createRun(request: CreateRunRequest): Promise<{ run_id: string }> {
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

