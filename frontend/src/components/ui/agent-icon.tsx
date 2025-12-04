import * as React from "react";
import { FileSearch, CheckCircle, FileText, Zap, Shield, FilePen, Send, Mail, LucideIcon, Settings, AlertCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import { AGENT_TYPE_SUB_AGENTS } from "@/types/agents";
import type { AgentType as PipelineType } from "@/types/agents";

type SubAgentId = 
  // DrawDocs agents
  | "preparation" 
  | "drawcore" 
  | "verification" 
  | "orderdocs"
  // Disclosure agents
  | "send"
  | "pre_check"
  // LOA agents
  | "generation"
  | "delivery"
  // System agents
  | "system"
  | "orchestrator";

// Default fallback icons (DrawDocs-style)
const defaultAgentIconMap: Record<SubAgentId, LucideIcon> = {
  // DrawDocs
  preparation: FileSearch,
  drawcore: Zap,
  verification: CheckCircle,
  orderdocs: FileText,
  // Disclosure
  send: Send,
  pre_check: Shield,
  // LOA
  generation: FilePen,
  delivery: Mail,
  // System
  system: Settings,
  orchestrator: Settings,
};

const defaultAgentColorMap: Record<SubAgentId, string> = {
  // DrawDocs
  preparation: "text-blue-600",
  drawcore: "text-orange-600",
  verification: "text-emerald-600",
  orderdocs: "text-purple-600",
  // Disclosure
  send: "text-purple-600",
  pre_check: "text-blue-600",
  // LOA
  generation: "text-emerald-600",
  delivery: "text-purple-600",
  // System
  system: "text-slate-600",
  orchestrator: "text-slate-600",
};

const defaultAgentBgMap: Record<SubAgentId, string> = {
  // DrawDocs
  preparation: "bg-blue-100",
  drawcore: "bg-orange-100",
  verification: "bg-emerald-100",
  orderdocs: "bg-purple-100",
  // Disclosure
  send: "bg-purple-100",
  pre_check: "bg-blue-100",
  // LOA
  generation: "bg-emerald-100",
  delivery: "bg-purple-100",
  // System
  system: "bg-slate-100",
  orchestrator: "bg-slate-100",
};

export interface AgentIconProps extends React.HTMLAttributes<HTMLDivElement> {
  type: SubAgentId;
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
  // Try to get icon from pipeline-specific config if pipelineType is provided
  let Icon = defaultAgentIconMap[type];
  let colorClass = defaultAgentColorMap[type];
  let bgClass = defaultAgentBgMap[type];
  
  if (pipelineType) {
    const subAgents = AGENT_TYPE_SUB_AGENTS[pipelineType];
    const agentConfig = subAgents?.find((a: any) => a.id === type);
    if (agentConfig) {
      Icon = agentConfig.icon;
      // Use the color from config
      const color = agentConfig.color;
      colorClass = `text-${color}-600`;
      bgClass = `bg-${color}-100`;
    }
  }
  
  // Fallback to a default icon if Icon is still undefined
  if (!Icon) {
    console.warn(`AgentIcon: No icon found for agent type "${type}". Using fallback.`);
    Icon = AlertCircle;
    colorClass = colorClass || "text-slate-600";
    bgClass = bgClass || "bg-slate-100";
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

