"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { ChevronDown, ChevronRight, Clock } from "lucide-react";
import type { TimelineEvent as TimelineEventType } from "@/types/log-events";
import { AGENT_COLORS, LEVEL_COLORS } from "@/types/log-events";
import { getEventTypeLabel } from "@/lib/log-parser";

interface TimelineEventProps {
  event: TimelineEventType;
  isLast?: boolean;
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatDuration(ms: number | undefined): string | null {
  if (!ms) return null;
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function TimelineEventItem({ event, isLast }: TimelineEventProps) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const hasDetails = event.details || (event.metadata && Object.keys(event.metadata).length > 0);
  
  const agentColors = AGENT_COLORS[event.agent] || AGENT_COLORS.system;
  const levelColors = LEVEL_COLORS[event.level] || LEVEL_COLORS.info;
  const eventLabel = getEventTypeLabel(event.event_type);
  const duration = event.metadata?.elapsed_seconds 
    ? formatDuration(event.metadata.elapsed_seconds * 1000)
    : event.metadata?.duration_ms 
      ? formatDuration(event.metadata.duration_ms)
      : null;

  return (
    <div className="relative flex gap-4 pb-4">
      {/* Timeline line */}
      {!isLast && (
        <div className="absolute left-[11px] top-6 w-0.5 h-[calc(100%-12px)] bg-border" />
      )}
      
      {/* Dot */}
      <div className="relative z-10 flex-shrink-0">
        <div className={cn(
          "w-6 h-6 rounded-full flex items-center justify-center ring-4 ring-background",
          levelColors.dot
        )}>
          <div className="w-2 h-2 rounded-full bg-white" />
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 min-w-0 pt-0.5">
        <div 
          className={cn(
            "rounded-lg border p-3 transition-colors",
            levelColors.bg,
            hasDetails && "cursor-pointer hover:shadow-sm",
          )}
          onClick={() => hasDetails && setIsExpanded(!isExpanded)}
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              {/* Agent badge + Event type */}
              <div className="flex items-center gap-2 mb-1">
                <span className={cn(
                  "text-[10px] font-medium px-1.5 py-0.5 rounded capitalize",
                  agentColors.bg,
                  agentColors.text
                )}>
                  {event.agent}
                </span>
                {eventLabel && (
                  <span className={cn(
                    "text-[9px] font-semibold px-1.5 py-0.5 rounded",
                    levelColors.bg,
                    levelColors.text
                  )}>
                    {eventLabel}
                  </span>
                )}
              </div>
              
              {/* Title */}
              <p className="text-sm font-medium text-foreground leading-tight">
                {event.title}
              </p>
            </div>
            
            {/* Right side: Time + expand */}
            <div className="flex items-center gap-2 flex-shrink-0">
              {duration && (
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {duration}
                </span>
              )}
              <span className="text-[10px] text-muted-foreground font-mono">
                {formatTimestamp(event.timestamp)}
              </span>
              {hasDetails && (
                isExpanded 
                  ? <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  : <ChevronRight className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
          </div>
          
          {/* Expandable details */}
          {isExpanded && hasDetails && (
            <div className="mt-3 pt-3 border-t border-border/50">
              {event.details && (
                <p className="text-xs text-muted-foreground mb-2">
                  {event.details}
                </p>
              )}
              {event.metadata && Object.keys(event.metadata).length > 0 && (
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {event.metadata.document_name && (
                    <div>
                      <span className="text-muted-foreground">Document:</span>
                      <span className="ml-1 font-medium">{String(event.metadata.document_name)}</span>
                    </div>
                  )}
                  {event.metadata.field_count && (
                    <div>
                      <span className="text-muted-foreground">Fields:</span>
                      <span className="ml-1 font-medium">{event.metadata.field_count}</span>
                    </div>
                  )}
                  {event.metadata.field_name && (
                    <div>
                      <span className="text-muted-foreground">Field:</span>
                      <span className="ml-1 font-medium">{String(event.metadata.field_name)}</span>
                    </div>
                  )}
                  {event.metadata.new_value && (
                    <div className="col-span-2">
                      <span className="text-muted-foreground">Value:</span>
                      <span className="ml-1 font-mono text-[11px]">
                        {String(event.metadata.new_value).slice(0, 100)}
                      </span>
                    </div>
                  )}
                  {event.metadata.error && (
                    <div className="col-span-2 text-red-600">
                      <span className="text-muted-foreground">Error:</span>
                      <span className="ml-1">{String(event.metadata.error).slice(0, 200)}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

