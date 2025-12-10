/**
 * Timeline Event Types for Agent Activity Log
 */

export type LogLevel = 'info' | 'success' | 'warning' | 'error' | 'debug';
export type AgentName = 'system' | 'orchestrator' | 'preparation' | 'drawcore' | 'verification' | 'orderdocs' | 'send' | 'pre_check';

export interface TimelineEvent {
  id: string;
  timestamp: string;
  agent: AgentName;
  level: LogLevel;
  title: string;
  details?: string;
  event_type?: string;
  metadata?: {
    documents_count?: number;
    documents_found?: number;
    documents_processed?: number;
    fields_count?: number;
    field_name?: string;
    field_id?: string;
    new_value?: string;
    old_value?: string;
    duration_ms?: number;
    elapsed_seconds?: number;
    error?: string;
    document_name?: string;
    corrections_count?: number;
    [key: string]: unknown;
  };
}

export const AGENT_COLORS: Record<AgentName, { bg: string; text: string; border: string }> = {
  system: { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-400' },
  orchestrator: { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-400' },
  preparation: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-400' },
  drawcore: { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-400' },
  verification: { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-400' },
  orderdocs: { bg: 'bg-emerald-100', text: 'text-emerald-700', border: 'border-emerald-400' },
  send: { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-400' },
  pre_check: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-400' },
};

export const LEVEL_COLORS: Record<LogLevel, { dot: string; bg: string; text: string }> = {
  info: { dot: 'bg-blue-500', bg: 'bg-blue-50', text: 'text-blue-700' },
  success: { dot: 'bg-emerald-500', bg: 'bg-emerald-50', text: 'text-emerald-700' },
  warning: { dot: 'bg-amber-500', bg: 'bg-amber-50', text: 'text-amber-700' },
  error: { dot: 'bg-red-500', bg: 'bg-red-50', text: 'text-red-700' },
  debug: { dot: 'bg-slate-400', bg: 'bg-slate-50', text: 'text-slate-600' },
};

