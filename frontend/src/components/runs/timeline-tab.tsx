"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  Search, 
  Filter, 
  ArrowDown,
  Activity,
  AlertCircle,
  CheckCircle2,
  Info,
  AlertTriangle,
} from "lucide-react";
import type { LogEntry, RunDetail } from "@/lib/api";
import type { TimelineEvent, AgentName, LogLevel } from "@/types/log-events";
import { parseLogEntries, filterByAgent, filterByLevel, filterBySearch } from "@/lib/log-parser";
import { TimelineEventItem } from "./timeline-event";

// =============================================================================
// TYPES
// =============================================================================

interface TimelineTabProps {
  runDetail: RunDetail | undefined;
  isLoading: boolean;
  className?: string;
}

type AgentFilter = AgentName | 'all';
type LevelFilter = LogLevel | 'all';

// =============================================================================
// FILTER BUTTONS
// =============================================================================

const AGENT_OPTIONS: { value: AgentFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'preparation', label: 'Preparation' },
  { value: 'drawcore', label: 'Drawcore' },
  { value: 'verification', label: 'Verification' },
  { value: 'orderdocs', label: 'OrderDocs' },
];

const LEVEL_OPTIONS: { value: LevelFilter; label: string; icon: React.ElementType }[] = [
  { value: 'all', label: 'All', icon: Filter },
  { value: 'info', label: 'Info', icon: Info },
  { value: 'success', label: 'Success', icon: CheckCircle2 },
  { value: 'warning', label: 'Warnings', icon: AlertTriangle },
  { value: 'error', label: 'Errors', icon: AlertCircle },
];

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function TimelineTab({ runDetail, isLoading, className }: TimelineTabProps) {
  const [agentFilter, setAgentFilter] = React.useState<AgentFilter>('all');
  const [levelFilter, setLevelFilter] = React.useState<LevelFilter>('all');
  const [searchQuery, setSearchQuery] = React.useState('');
  const [autoScroll, setAutoScroll] = React.useState(true);
  const scrollRef = React.useRef<HTMLDivElement>(null);
  
  // Parse and filter events
  const allEvents = React.useMemo(() => {
    return parseLogEntries(runDetail?.logs);
  }, [runDetail?.logs]);
  
  const filteredEvents = React.useMemo(() => {
    let events = allEvents;
    events = filterByAgent(events, agentFilter);
    events = filterByLevel(events, levelFilter);
    events = filterBySearch(events, searchQuery);
    return events;
  }, [allEvents, agentFilter, levelFilter, searchQuery]);
  
  // Check if run is still active
  const isRunning = runDetail?.agents?.preparation?.status === 'running' ||
    runDetail?.agents?.verification?.status === 'running' ||
    runDetail?.agents?.orderdocs?.status === 'running';
  
  // Auto-scroll to bottom when new events arrive
  React.useEffect(() => {
    if (autoScroll && scrollRef.current && isRunning) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [filteredEvents.length, autoScroll, isRunning]);
  
  // Count events by level for badges
  const counts = React.useMemo(() => ({
    all: allEvents.length,
    info: allEvents.filter(e => e.level === 'info').length,
    success: allEvents.filter(e => e.level === 'success').length,
    warning: allEvents.filter(e => e.level === 'warning').length,
    error: allEvents.filter(e => e.level === 'error').length,
  }), [allEvents]);

  if (isLoading) {
    return <TimelineSkeleton />;
  }

  return (
    <Card className={cn("flex flex-col h-[600px]", className)}>
      <CardHeader className="pb-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Activity className="h-4 w-4 text-muted-foreground" />
            Agent Activity Timeline
            <span className="text-muted-foreground font-normal">
              ({filteredEvents.length} events)
            </span>
          </CardTitle>
          
          {isRunning && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-blue-600 animate-pulse flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
                Streaming...
              </span>
              <Button
                variant={autoScroll ? "default" : "outline"}
                size="sm"
                className="h-7 text-xs"
                onClick={() => setAutoScroll(!autoScroll)}
              >
                <ArrowDown className="h-3 w-3 mr-1" />
                Auto-scroll
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="flex-1 flex flex-col gap-3 overflow-hidden pb-4">
        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search events..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 h-8 text-sm"
            />
          </div>
          
          {/* Agent Filter */}
          <div className="flex items-center gap-1 border rounded-md p-0.5">
            {AGENT_OPTIONS.map((option) => (
              <Button
                key={option.value}
                variant={agentFilter === option.value ? "default" : "ghost"}
                size="sm"
                className="h-7 text-xs px-2"
                onClick={() => setAgentFilter(option.value)}
              >
                {option.label}
              </Button>
            ))}
          </div>
          
          {/* Level Filter */}
          <div className="flex items-center gap-1 border rounded-md p-0.5">
            {LEVEL_OPTIONS.map((option) => {
              const count = counts[option.value as keyof typeof counts] || 0;
              return (
                <Button
                  key={option.value}
                  variant={levelFilter === option.value ? "default" : "ghost"}
                  size="sm"
                  className={cn(
                    "h-7 text-xs px-2 gap-1",
                    option.value === 'error' && count > 0 && levelFilter !== option.value && "text-red-600",
                    option.value === 'warning' && count > 0 && levelFilter !== option.value && "text-amber-600",
                  )}
                  onClick={() => setLevelFilter(option.value)}
                >
                  <option.icon className="h-3 w-3" />
                  {option.value !== 'all' && count > 0 && (
                    <span className="text-[10px]">({count})</span>
                  )}
                </Button>
              );
            })}
          </div>
        </div>
        
        {/* Timeline */}
        <ScrollArea className="flex-1" ref={scrollRef}>
          {filteredEvents.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full py-12 text-muted-foreground">
              <Activity className="h-12 w-12 opacity-20 mb-3" />
              <p className="text-sm">
                {allEvents.length === 0 
                  ? "No activity recorded yet"
                  : "No events match your filters"
                }
              </p>
              {searchQuery && (
                <Button
                  variant="link"
                  size="sm"
                  onClick={() => setSearchQuery('')}
                  className="mt-2"
                >
                  Clear search
                </Button>
              )}
            </div>
          ) : (
            <div className="pr-4">
              {filteredEvents.map((event, index) => (
                <TimelineEventItem
                  key={event.id}
                  event={event}
                  isLast={index === filteredEvents.length - 1}
                />
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// SKELETON
// =============================================================================

function TimelineSkeleton() {
  return (
    <Card className="h-[600px]">
      <CardHeader className="pb-3">
        <Skeleton className="h-5 w-48" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Skeleton className="h-8 flex-1" />
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-8 w-32" />
        </div>
        <div className="space-y-4 pt-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex gap-4">
              <Skeleton className="h-6 w-6 rounded-full flex-shrink-0" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-5 w-full" />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

