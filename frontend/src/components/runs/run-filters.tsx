"use client";

import * as React from "react";
import { Search, X, Filter } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { RunStatusValue } from "@/lib/api";

// =============================================================================
// TYPES
// =============================================================================

export type FilterStatus = RunStatusValue | "all";

interface RunFiltersProps {
  /** Current status filter */
  status: FilterStatus;
  /** Callback when status changes */
  onStatusChange: (status: FilterStatus) => void;
  /** Current search query */
  searchQuery: string;
  /** Callback when search query changes */
  onSearchChange: (query: string) => void;
  /** Total number of runs (for display) */
  totalRuns?: number;
  /** Number of filtered runs (for display) */
  filteredRuns?: number;
  className?: string;
}

// =============================================================================
// STATUS FILTER BUTTONS
// =============================================================================

const STATUS_OPTIONS: { value: FilterStatus; label: string; color?: string }[] = [
  { value: "all", label: "All" },
  { value: "running", label: "Running", color: "bg-blue-500" },
  { value: "success", label: "Success", color: "bg-emerald-500" },
  { value: "failed", label: "Failed", color: "bg-red-500" },
];

// =============================================================================
// MAIN COMPONENT
// =============================================================================

/**
 * Filter bar for the runs list.
 * 
 * Features:
 * - Status filter buttons (All, Running, Success, Failed)
 * - Search by Loan ID
 * - Clear filters button
 */
export function RunFilters({
  status,
  onStatusChange,
  searchQuery,
  onSearchChange,
  totalRuns,
  filteredRuns,
  className,
}: RunFiltersProps) {
  const hasActiveFilters = status !== "all" || searchQuery.length > 0;

  const clearFilters = () => {
    onStatusChange("all");
    onSearchChange("");
  };

  return (
    <div className={cn("space-y-3", className)}>
      {/* Main filter row */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Status filter buttons */}
        <div className="flex items-center gap-1 p-1 rounded-lg bg-muted/50 border border-border">
          {STATUS_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => onStatusChange(option.value)}
              className={cn(
                "px-3 py-1.5 text-sm font-medium rounded-md transition-all",
                "flex items-center gap-1.5",
                status === option.value
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-background/50"
              )}
            >
              {option.color && (
                <span
                  className={cn(
                    "h-2 w-2 rounded-full",
                    option.color,
                    option.value === "running" && "animate-pulse"
                  )}
                />
              )}
              {option.label}
            </button>
          ))}
        </div>

        {/* Search input */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search by Loan ID..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-9 pr-9"
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Clear filters button */}
        {hasActiveFilters && (
          <Button
            variant="outline"
            size="sm"
            onClick={clearFilters}
            className="whitespace-nowrap"
          >
            <X className="h-4 w-4 mr-1" />
            Clear filters
          </Button>
        )}
      </div>

      {/* Results count */}
      {totalRuns !== undefined && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Filter className="h-4 w-4" />
          {filteredRuns !== undefined && filteredRuns !== totalRuns ? (
            <span>
              Showing <span className="font-medium text-foreground">{filteredRuns}</span> of{" "}
              <span className="font-medium text-foreground">{totalRuns}</span> runs
            </span>
          ) : (
            <span>
              <span className="font-medium text-foreground">{totalRuns}</span> run
              {totalRuns !== 1 ? "s" : ""} total
            </span>
          )}
        </div>
      )}
    </div>
  );
}

