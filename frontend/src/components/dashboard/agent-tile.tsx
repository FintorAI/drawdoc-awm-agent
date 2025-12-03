"use client";

import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { AgentTypeConfig } from "@/types/agents";

interface AgentStats {
  runsToday: number;
  inProgress: number;
  successRate: number;
  alerts?: number;
}

interface AgentTileProps {
  config: AgentTypeConfig;
  stats?: AgentStats;
  isLoading?: boolean;
}

export function AgentTile({ config, stats, isLoading }: AgentTileProps) {
  const Icon = config.icon;
  
  if (!config.enabled) {
    return (
      <Card className="opacity-60 cursor-not-allowed">
        <CardContent className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div className={cn("h-12 w-12 rounded-xl flex items-center justify-center", config.bgColor)}>
              <Icon className={cn("h-6 w-6", config.textColor)} />
            </div>
            <span className="text-xs font-medium text-muted-foreground bg-muted px-2 py-1 rounded">
              Coming Soon
            </span>
          </div>
          
          <h3 className="text-lg font-semibold text-foreground">{config.name}</h3>
          <p className="text-sm text-muted-foreground mt-1">{config.description}</p>
          
          <div className="mt-4 pt-4 border-t border-border">
            <span className="text-sm text-muted-foreground">Not yet available</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Link href={config.route}>
      <Card className="hover:shadow-lg transition-shadow cursor-pointer group">
        <CardContent className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div className={cn(
              "h-12 w-12 rounded-xl flex items-center justify-center transition-transform group-hover:scale-105",
              config.bgColor
            )}>
              <Icon className={cn("h-6 w-6", config.textColor)} />
            </div>
            {stats && stats.inProgress > 0 && (
              <span className="flex items-center gap-1.5 text-xs font-medium text-blue-600 bg-blue-100 px-2 py-1 rounded">
                <span className="h-1.5 w-1.5 rounded-full bg-blue-600 animate-pulse" />
                {stats.inProgress} running
              </span>
            )}
            {stats && stats.inProgress === 0 && (
              <span className="text-xs font-medium text-emerald-600 bg-emerald-100 px-2 py-1 rounded">
                Active
              </span>
            )}
          </div>
          
          <h3 className="text-lg font-semibold text-foreground group-hover:text-primary transition-colors">
            {config.name}
          </h3>
          <p className="text-sm text-muted-foreground mt-1">{config.description}</p>
          
          {isLoading ? (
            <div className="mt-4 pt-4 border-t border-border space-y-2">
              <div className="h-4 w-24 bg-muted rounded animate-pulse" />
              <div className="h-4 w-20 bg-muted rounded animate-pulse" />
            </div>
          ) : stats ? (
            <div className="mt-4 pt-4 border-t border-border grid grid-cols-2 gap-4">
              <div>
                <p className="text-2xl font-semibold text-foreground">{stats.runsToday}</p>
                <p className="text-xs text-muted-foreground">runs today</p>
              </div>
              <div>
                <p className="text-2xl font-semibold text-foreground">{stats.successRate.toFixed(0)}%</p>
                <p className="text-xs text-muted-foreground">success rate</p>
              </div>
            </div>
          ) : (
            <div className="mt-4 pt-4 border-t border-border">
              <p className="text-sm text-muted-foreground">No data yet</p>
            </div>
          )}
          
          {stats && stats.alerts && stats.alerts > 0 && (
            <div className="mt-3 flex items-center gap-2 text-amber-600">
              <span className="text-xs font-medium">⚠️ {stats.alerts} alert{stats.alerts > 1 ? 's' : ''}</span>
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

