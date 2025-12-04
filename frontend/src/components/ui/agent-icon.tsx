import * as React from "react";
import { FileSearch, CheckCircle, FileText, Zap, Shield, FilePen, Send, Mail, LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { AGENT_TYPE_SUB_AGENTS } from "@/types/agents";
import type { AgentType as PipelineType } from "@/types/agents";

// Known sub-agent IDs for type-safe maps
type KnownSubAgentId = 
  // DrawDocs agents
  | "preparation" 
  | "drawcore" 
  | "verification" 
  | "orderdocs"
  // Disclosure agents
  | "send"
  // LOA agents
  | "generation"
  | "delivery";

// Default fallback icons (DrawDocs-style)
const defaultAgentIconMap: Record<KnownSubAgentId, LucideIcon> = {
  // DrawDocs
  preparation: FileSearch,
  drawcore: Zap,
  verification: CheckCircle,
  orderdocs: FileText,
  // Disclosure
  send: Send,
  // LOA
  generation: FilePen,
  delivery: Mail,
};

const defaultAgentColorMap: Record<KnownSubAgentId, string> = {
  // DrawDocs
  preparation: "text-blue-600",
  drawcore: "text-orange-600",
  verification: "text-emerald-600",
  orderdocs: "text-purple-600",
  // Disclosure
  send: "text-purple-600",
  // LOA
  generation: "text-emerald-600",
  delivery: "text-purple-600",
};

const defaultAgentBgMap: Record<KnownSubAgentId, string> = {
  // DrawDocs
  preparation: "bg-blue-100",
  drawcore: "bg-orange-100",
  verification: "bg-emerald-100",
  orderdocs: "bg-purple-100",
  // Disclosure
  send: "bg-purple-100",
  // LOA
  generation: "bg-emerald-100",
  delivery: "bg-purple-100",
};

export interface AgentIconProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Agent type ID - accepts any string, falls back gracefully for unknown types */
  type: string;
  size?: "sm" | "md" | "lg";
  showBackground?: boolean;
  pipelineType?: PipelineType; // Optional: helps get the right icon from config
}

function AgentIcon({ 
  type, 
  size = "md", 
  showBackground = false, 
  pipelineType,
  className, 
  ...props 
}: AgentIconProps) {
  // Default fallback values - cast to known type for map lookup, fallback handles unknown
  const knownType = type as KnownSubAgentId;
  let Icon: LucideIcon = defaultAgentIconMap[knownType] ?? FileSearch;
  let colorClass = defaultAgentColorMap[knownType] ?? "text-slate-600";
  let bgClass = defaultAgentBgMap[knownType] ?? "bg-slate-100";
  
  // Try to get icon from pipeline-specific config if pipelineType is provided
  if (pipelineType) {
    const subAgents = AGENT_TYPE_SUB_AGENTS[pipelineType];
    const agentConfig = subAgents?.find((a) => a.id === type);
    if (agentConfig?.icon) {
      Icon = agentConfig.icon;
      // Use the color from config
      const color = agentConfig.color;
      colorClass = `text-${color}-600`;
      bgClass = `bg-${color}-100`;
    }
  }
  
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-5 w-5",
    lg: "h-6 w-6",
  };
  
  const containerSizeClasses = {
    sm: "h-6 w-6",
    md: "h-8 w-8",
    lg: "h-10 w-10",
  };

  if (showBackground) {
    return (
      <div
        className={cn(
          "rounded-lg flex items-center justify-center",
          containerSizeClasses[size],
          bgClass,
          className
        )}
        {...props}
      >
        <Icon className={cn(sizeClasses[size], colorClass)} />
      </div>
    );
  }

  return (
    <Icon className={cn(sizeClasses[size], colorClass, className)} />
  );
}

export { AgentIcon };

