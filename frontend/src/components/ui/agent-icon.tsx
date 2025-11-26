import * as React from "react";
import { FileSearch, CheckCircle, FileText, LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

type AgentType = "preparation" | "verification" | "orderdocs";

const agentIconMap: Record<AgentType, LucideIcon> = {
  preparation: FileSearch,
  verification: CheckCircle,
  orderdocs: FileText,
};

const agentColorMap: Record<AgentType, string> = {
  preparation: "text-blue-600",
  verification: "text-emerald-600",
  orderdocs: "text-purple-600",
};

const agentBgMap: Record<AgentType, string> = {
  preparation: "bg-blue-100",
  verification: "bg-emerald-100",
  orderdocs: "bg-purple-100",
};

export interface AgentIconProps extends React.HTMLAttributes<HTMLDivElement> {
  type: AgentType;
  size?: "sm" | "md" | "lg";
  showBackground?: boolean;
}

function AgentIcon({ 
  type, 
  size = "md", 
  showBackground = false, 
  className, 
  ...props 
}: AgentIconProps) {
  const Icon = agentIconMap[type];
  const colorClass = agentColorMap[type];
  const bgClass = agentBgMap[type];
  
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
    <Icon className={cn(sizeClasses[size], colorClass, className)} {...props} />
  );
}

export { AgentIcon };

