/**
 * Multi-Agent Dashboard Types
 * 
 * Defines agent types, configurations, and sub-agent definitions
 * for DrawDocs, Disclosure, and LOA agent pipelines.
 */

import { FileSearch, Zap, CheckCircle, FileText, Shield, FilePen, Send, Mail } from "lucide-react";
import type { LucideIcon } from "lucide-react";

// =============================================================================
// AGENT TYPES
// =============================================================================

/**
 * Available agent pipeline types
 */
export type AgentType = "drawdocs" | "disclosure" | "loa";

/**
 * Status values for agent runs
 */
export type AgentStatusValue = "pending" | "running" | "success" | "failed" | "blocked";

/**
 * Overall run status values
 */
export type RunStatusValue = "running" | "success" | "failed" | "blocked";

// =============================================================================
// SUB-AGENT CONFIGURATIONS
// =============================================================================

/**
 * Configuration for a single sub-agent in a pipeline
 */
export interface SubAgentConfig {
  /** Unique identifier for the sub-agent */
  id: string;
  /** Display name */
  name: string;
  /** Short description */
  description: string;
  /** Icon component */
  icon: LucideIcon;
  /** Theme color (tailwind color name without shade) */
  color: string;
}

/**
 * Sub-agents for DrawDocs pipeline
 */
export const DRAWDOCS_SUB_AGENTS: SubAgentConfig[] = [
  {
    id: "preparation",
    name: "Preparation",
    description: "Extract fields from documents",
    icon: FileSearch,
    color: "blue",
  },
  {
    id: "drawcore",
    name: "Drawcore",
    description: "Write fields to Encompass",
    icon: Zap,
    color: "orange",
  },
  {
    id: "verification",
    name: "Verification",
    description: "Verify against SOP rules",
    icon: CheckCircle,
    color: "emerald",
  },
  {
    id: "orderdocs",
    name: "OrderDocs",
    description: "Order closing documents",
    icon: FileText,
    color: "purple",
  },
];

/**
 * Sub-agents for Disclosure pipeline
 */
export const DISCLOSURE_SUB_AGENTS: SubAgentConfig[] = [
  {
    id: "verification",
    name: "Verification",
    description: "TRID compliance & forms",
    icon: Shield,
    color: "blue",
  },
  {
    id: "preparation",
    name: "Preparation",
    description: "RegZ-LE, MI, CTC",
    icon: FilePen,
    color: "emerald",
  },
  {
    id: "send",
    name: "Send",
    description: "Mavent, ATR/QM, eDisc",
    icon: Send,
    color: "purple",
  },
];

/**
 * Sub-agents for LOA pipeline (placeholder)
 */
export const LOA_SUB_AGENTS: SubAgentConfig[] = [
  {
    id: "verification",
    name: "Verification",
    description: "Lorem ipsum dolor",
    icon: Shield,
    color: "blue",
  },
  {
    id: "generation",
    name: "Generation",
    description: "Lorem ipsum dolor",
    icon: FilePen,
    color: "emerald",
  },
  {
    id: "delivery",
    name: "Delivery",
    description: "Lorem ipsum dolor",
    icon: Mail,
    color: "purple",
  },
];

/**
 * Map of agent type to its sub-agent configuration
 */
export const AGENT_TYPE_SUB_AGENTS: Record<AgentType, SubAgentConfig[]> = {
  drawdocs: DRAWDOCS_SUB_AGENTS,
  disclosure: DISCLOSURE_SUB_AGENTS,
  loa: LOA_SUB_AGENTS,
};

// =============================================================================
// AGENT TYPE CONFIGURATIONS
// =============================================================================

/**
 * Full configuration for an agent type
 */
export interface AgentTypeConfig {
  /** Unique identifier */
  id: AgentType;
  /** Display name */
  name: string;
  /** Short description */
  description: string;
  /** Icon component */
  icon: LucideIcon;
  /** Theme color */
  color: string;
  /** Background color class */
  bgColor: string;
  /** Text color class */
  textColor: string;
  /** Whether the agent is currently enabled */
  enabled: boolean;
  /** Sub-agents in this pipeline */
  subAgents: SubAgentConfig[];
  /** Route path */
  route: string;
}

/**
 * DrawDocs agent configuration
 */
export const DRAWDOCS_CONFIG: AgentTypeConfig = {
  id: "drawdocs",
  name: "DrawDocs",
  description: "Lorem Ipsum",
  icon: FileText,
  color: "emerald",
  bgColor: "bg-emerald-100",
  textColor: "text-emerald-700",
  enabled: true,
  subAgents: DRAWDOCS_SUB_AGENTS,
  route: "/drawdocs",
};

/**
 * Disclosure agent configuration
 */
export const DISCLOSURE_CONFIG: AgentTypeConfig = {
  id: "disclosure",
  name: "Disclosure",
  description: "Loan Estimate processing",
  icon: Shield,
  color: "blue",
  bgColor: "bg-blue-100",
  textColor: "text-blue-700",
  enabled: true,
  subAgents: DISCLOSURE_SUB_AGENTS,
  route: "/disclosure",
};

/**
 * LOA agent configuration
 */
export const LOA_CONFIG: AgentTypeConfig = {
  id: "loa",
  name: "Loan Officer Assistant",
  description: "Lorem Ipsum",
  icon: Mail,
  color: "amber",
  bgColor: "bg-amber-100",
  textColor: "text-amber-700",
  enabled: true,
  subAgents: LOA_SUB_AGENTS,
  route: "/loa",
};

/**
 * All agent configurations
 */
export const AGENT_CONFIGS: AgentTypeConfig[] = [
  DISCLOSURE_CONFIG,
  DRAWDOCS_CONFIG,
  LOA_CONFIG,
];

/**
 * Map of agent type to its configuration
 */
export const AGENT_CONFIG_MAP: Record<AgentType, AgentTypeConfig> = {
  drawdocs: DRAWDOCS_CONFIG,
  disclosure: DISCLOSURE_CONFIG,
  loa: LOA_CONFIG,
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Get agent configuration by type
 */
export function getAgentConfig(agentType: AgentType): AgentTypeConfig {
  return AGENT_CONFIG_MAP[agentType];
}

/**
 * Get sub-agents for an agent type
 */
export function getSubAgents(agentType: AgentType): SubAgentConfig[] {
  return AGENT_TYPE_SUB_AGENTS[agentType];
}

/**
 * Get sub-agent IDs for an agent type
 */
export function getSubAgentIds(agentType: AgentType): string[] {
  return AGENT_TYPE_SUB_AGENTS[agentType].map((agent) => agent.id);
}

/**
 * Check if an agent type is enabled
 */
export function isAgentEnabled(agentType: AgentType): boolean {
  return AGENT_CONFIG_MAP[agentType].enabled;
}

/**
 * Get enabled agent configs only
 */
export function getEnabledAgentConfigs(): AgentTypeConfig[] {
  return AGENT_CONFIGS.filter((config) => config.enabled);
}

