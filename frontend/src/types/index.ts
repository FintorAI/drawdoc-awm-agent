/**
 * DrawDoc Agent Types
 * 
 * Core data types for the DrawDoc verification agent system.
 * Matches the backend orchestrator_agent.py configuration structure.
 */

// =============================================================================
// RUN CONFIGURATION
// =============================================================================

/**
 * Configuration for triggering an agent run.
 * Matches the structure in example_input.json
 */
export interface RunConfig {
  /** Encompass loan GUID (required) */
  loan_id: string;
  
  /** Optional user prompt for special instructions (e.g., 'only prep', 'skip verification', 'summary only') */
  user_prompt: string | null;
  
  /** Demo mode: true = no actual writes to Encompass (default), false = production mode */
  demo_mode: boolean;
  
  /** Number of retry attempts per agent (default: 2, range: 0-5) */
  max_retries: number;
  
  /** 
   * Optional list of document types to process.
   * Available types: ID, Title Report, Appraisal, LE, 1003, CD, Insurance, VOE, Bank Statements
   * null = process all documents
   */
  document_types: string[] | null;
}

// =============================================================================
// AGENT RUN STATUS
// =============================================================================

export type RunStatus = 'pending' | 'running' | 'success' | 'failed';

/**
 * Result from an individual agent (Preparation, Verification, or OrderDocs)
 */
export interface AgentResult {
  /** Current status of the agent */
  status: RunStatus;
  
  /** Number of retry attempts made */
  attempts: number;
  
  /** Time taken in seconds */
  elapsed_seconds: number;
  
  /** Agent output data (varies by agent type) */
  output: AgentOutput | null;
  
  /** Error message if failed */
  error: string | null;
}

/**
 * Union type for different agent outputs
 */
export type AgentOutput = PreparationOutput | VerificationOutput | OrderDocsOutput;

/**
 * Output from the Preparation Agent
 */
export interface PreparationOutput {
  loan_id: string;
  total_documents_found: number;
  documents_processed: number;
  results: {
    extracted_entities: Record<string, Record<string, unknown>>;
    field_mappings: Record<string, FieldMapping>;
  };
  timing: {
    total_time_seconds: number;
    total_time_minutes: number;
    average_time_per_document_seconds: number;
    get_documents_time_seconds: number;
    preload_schemas_time_seconds: number;
    processing_time_seconds: number;
    aggregation_time_seconds: number;
  };
}

/**
 * Field mapping with value and source document
 */
export interface FieldMapping {
  value: string | number;
  attachment_id: string | null;
}

/**
 * Output from the Verification Agent
 */
export interface VerificationOutput {
  messages: string[];
}

/**
 * Output from the OrderDocs Agent
 */
export interface OrderDocsOutput {
  [fieldId: string]: {
    value: string;
    has_value: boolean;
    correction_applied?: boolean;
  };
}

/**
 * Complete agent run record
 */
export interface AgentRun {
  /** Unique run identifier */
  id: string;
  
  /** Encompass loan GUID */
  loan_id: string;
  
  /** Run configuration */
  config: RunConfig;
  
  /** Overall run status */
  status: RunStatus;
  
  /** ISO timestamp when run was created */
  created_at: string;
  
  /** ISO timestamp of last update */
  updated_at: string;
  
  /** Results from each agent */
  agents: {
    preparation: AgentResult | null;
    verification: AgentResult | null;
    orderdocs: AgentResult | null;
  };
  
  /** Human-readable summary text */
  summary_text?: string;
  
  /** Structured JSON output */
  json_output?: AgentRunJsonOutput;
}

/**
 * Structured JSON output from orchestrator
 */
export interface AgentRunJsonOutput {
  loan_id: string;
  execution_timestamp: string;
  demo_mode: boolean;
  summary: Record<string, unknown>;
  agents: {
    preparation: AgentResultJson | null;
    verification: AgentResultJson | null;
    orderdocs: AgentResultJson | null;
  };
  corrected_fields_summary?: CorrectedFieldSummary[];
}

export interface AgentResultJson {
  status: RunStatus;
  attempts: number;
  elapsed_seconds: number;
  output: unknown;
  error: string | null;
}

export interface CorrectedFieldSummary {
  field_id: string;
  field_name: string;
  corrected_value: string;
  source_document: string | null;
  document_filename: string;
}

// =============================================================================
// DOCUMENT TYPES
// =============================================================================

/**
 * Available document types for processing
 */
export const DOCUMENT_TYPES = [
  'ID',
  'Title Report',
  'Appraisal',
  'LE',
  '1003',
  'CD',
  'Insurance',
  'VOE',
  'Bank Statements',
] as const;

export type DocumentType = typeof DOCUMENT_TYPES[number];

// =============================================================================
// HELPER TYPES
// =============================================================================

/**
 * Default configuration values
 */
export const DEFAULT_RUN_CONFIG: Omit<RunConfig, 'loan_id'> = {
  user_prompt: null,
  demo_mode: true,
  max_retries: 2,
  document_types: null,
};

/**
 * Validation result for loan ID format
 */
export interface ValidationResult {
  valid: boolean;
  message?: string;
}

/**
 * UUID regex pattern for loan ID validation
 */
export const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Validate loan ID format
 */
export function validateLoanId(loanId: string): ValidationResult {
  const trimmed = loanId.trim();
  if (!trimmed) {
    return { valid: false, message: 'Loan ID is required' };
  }
  if (!UUID_PATTERN.test(trimmed)) {
    return { valid: false, message: 'Loan ID must be a valid UUID format' };
  }
  return { valid: true };
}

