/**
 * Log parser utilities for timeline events
 */

import type { TimelineEvent, AgentName, LogLevel } from "@/types/log-events";

/**
 * Get a human-readable label for an event type
 */
export function getEventTypeLabel(eventType: string | undefined): string {
  if (!eventType) return "";
  
  const labels: Record<string, string> = {
    // Agent lifecycle events
    agent_start: "Agent Started",
    agent_complete: "Agent Complete",
    agent_failed: "Agent Failed",
    
    // Preparation agent events
    prep_summary: "Preparation Summary",
    document: "Document Processing",
    fields_extracted: "Fields Extracted",
    field_mappings: "Field Mappings",
    
    // Drawcore agent events
    drawcore_summary: "Drawcore Summary",
    phase_start: "Phase Started",
    phase_complete: "Phase Complete",
    field_update: "Field Updated",
    
    // Verification agent events (Disclosure)
    verification_summary: "Verification Summary",
    correction: "Field Correction",
    trid_check: "TRID Compliance Check",
    form_validation: "Form Validation",
    
    // Preparation agent events (Disclosure)
    regz_le_update: "RegZ-LE Update",
    mi_calculation: "MI Calculation",
    ctc_match: "CTC Match",
    
    // Send agent events (Disclosure)
    mavent_check: "Mavent Compliance",
    atr_qm_check: "ATR/QM Check",
    order_disclosure: "Order Disclosure",
    
    // OrderDocs agent events
    orderdocs_summary: "OrderDocs Summary",
    order_docs: "Order Documents",
    
    // Pre-check events
    pre_check: "Pre-Check",
    milestone_check: "Milestone Check",
    disclosure_tracking: "Disclosure Tracking",
    
    // General events
    progress: "Progress Update",
    error: "Error",
    warning: "Warning",
  };
  
  return labels[eventType] || eventType.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Parse raw log entries into timeline events
 */
export function parseLogEntry(log: {
  timestamp: string;
  level: string;
  agent: string;
  message: string;
  event_type?: string;
  details?: Record<string, unknown>;
}, index: number): TimelineEvent {
  return {
    id: `${log.timestamp}-${index}`,
    timestamp: log.timestamp,
    agent: log.agent as AgentName,
    level: log.level as LogLevel,
    title: log.message,
    event_type: log.event_type,
    metadata: log.details as TimelineEvent["metadata"],
  };
}

/**
 * Parse an array of log entries into timeline events
 */
export function parseLogEntries(logs: Array<{
  timestamp: string;
  level: string;
  agent: string;
  message: string;
  event_type?: string;
  details?: Record<string, unknown>;
}> | undefined): TimelineEvent[] {
  if (!logs) return [];
  return logs.map((log, index) => parseLogEntry(log, index));
}

/**
 * Filter timeline events by agent
 */
export function filterByAgent(events: TimelineEvent[], agent: AgentName | "all"): TimelineEvent[] {
  if (agent === "all") return events;
  return events.filter(event => event.agent === agent);
}

/**
 * Filter timeline events by log level
 */
export function filterByLevel(events: TimelineEvent[], level: LogLevel | "all"): TimelineEvent[] {
  if (level === "all") return events;
  return events.filter(event => event.level === level);
}

/**
 * Filter timeline events by search query
 */
export function filterBySearch(events: TimelineEvent[], query: string): TimelineEvent[] {
  if (!query.trim()) return events;
  const lowerQuery = query.toLowerCase();
  return events.filter(event => 
    event.title.toLowerCase().includes(lowerQuery) ||
    event.details?.toLowerCase().includes(lowerQuery) ||
    event.agent.toLowerCase().includes(lowerQuery) ||
    event.event_type?.toLowerCase().includes(lowerQuery)
  );
}

