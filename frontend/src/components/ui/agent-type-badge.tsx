"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { AGENT_CONFIG_MAP, type AgentType } from "@/types/agents";

// =============================================================================
// TYPES
// =============================================================================

interface AgentTypeBadgeProps {
  /** Agent type */
  agentType: AgentType;
  /** Show icon */
  showIcon?: boolean;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Additional className */
  className?: string;
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function AgentTypeBadge({
  agentType,
  showIcon = true,
  size = "md",
  className,
}: AgentTypeBadgeProps) {
  const config = AGENT_CONFIG_MAP[agentType];
  const Icon = config.icon;

  const sizeClasses = {
    sm: "text-[10px] px-1.5 py-0.5 gap-1",
    md: "text-xs px-2 py-0.5 gap-1.5",
    lg: "text-sm px-2.5 py-1 gap-2",
  };

  const iconSizes = {
    sm: "h-2.5 w-2.5",
    md: "h-3 w-3",
    lg: "h-4 w-4",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center font-medium rounded",
        sizeClasses[size],
        config.bgColor,
        config.textColor,
        className
      )}
    >
      {showIcon && <Icon className={iconSizes[size]} />}
      <span>{config.name}</span>
    </span>
  );
}

// =============================================================================
// VARIANTS
// =============================================================================

interface AgentTypeIconProps {
  agentType: AgentType;
  size?: "sm" | "md" | "lg";
  className?: string;
}

/**
 * Just the icon with background, no text.
 */
export function AgentTypeIcon({
  agentType,
  size = "md",
  className,
}: AgentTypeIconProps) {
  const config = AGENT_CONFIG_MAP[agentType];
  const Icon = config.icon;

  const sizeClasses = {
    sm: "h-6 w-6",
    md: "h-8 w-8",
    lg: "h-10 w-10",
  };

  const iconSizes = {
    sm: "h-3 w-3",
    md: "h-4 w-4",
    lg: "h-5 w-5",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center justify-center rounded-lg",
        sizeClasses[size],
        config.bgColor,
        className
      )}
    >
      <Icon className={cn(iconSizes[size], config.textColor)} />
    </div>
  );
}

