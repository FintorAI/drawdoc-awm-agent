"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { AgentIcon } from "@/components/ui/agent-icon";
import { Badge } from "@/components/ui/badge";
import { 
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileText,
  Pencil,
  Flag,
  TrendingUp,
  ArrowRight,
  Download,
  Copy,
  Check,
  Zap,
  ShieldCheck,
  Package,
  Clock,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { RunDetail, AgentResultDetail } from "@/lib/api";
import type { AgentType } from "@/types/agents";
import { getSubAgents } from "@/types/agents";

// =============================================================================
// TYPES
// =============================================================================

interface FinalReportTabProps {
  runDetail: RunDetail | undefined;
  isLoading: boolean;
  className?: string;
}

interface FlaggedItem {
  id: string;
  agent: "preparation" | "drawcore" | "verification" | "orderdocs";
  severity: "error" | "warning" | "info";
  field?: string;
  fieldId?: string;
  message: string;
  details?: string;
}

interface FieldChange {
  fieldId: string;
  fieldName: string;
  oldValue: string | null;
  newValue: string;
  source: string;
  agent: "preparation" | "drawcore" | "verification";
}

// =============================================================================
// HELPERS
// =============================================================================

function extractFlaggedItems(runDetail: RunDetail): FlaggedItem[] {
  const items: FlaggedItem[] = [];
  let idCounter = 0;

  // Extract from logs
  if (runDetail.logs) {
    runDetail.logs.forEach(log => {
      if (log.level === "error" || log.level === "warning") {
        items.push({
          id: `log-${idCounter++}`,
          agent: log.agent as FlaggedItem["agent"],
          severity: log.level as "error" | "warning",
          message: log.message,
          details: log.details ? JSON.stringify(log.details) : undefined,
        });
      }
    });
  }

  // Extract from agent outputs - Drawcore issues
  const drawcoreOutput = runDetail.agents.drawcore?.output as {
    phases?: Record<string, { issues?: Array<{ type: string; message: string }> }>;
  };
  if (drawcoreOutput?.phases) {
    Object.entries(drawcoreOutput.phases).forEach(([phaseName, phase]) => {
      phase.issues?.forEach((issue, idx) => {
        items.push({
          id: `drawcore-${phaseName}-${idx}`,
          agent: "drawcore",
          severity: issue.type === "error" ? "error" : "warning",
          message: issue.message,
          details: `Phase: ${phaseName}`,
        });
      });
    });
  }

  // Extract from verification corrections
  const verificationOutput = runDetail.agents.verification?.output as {
    corrections?: Array<{ field_id: string; field_name: string; reason: string }>;
  };
  if (verificationOutput?.corrections) {
    verificationOutput.corrections.forEach((correction, idx) => {
      items.push({
        id: `verification-correction-${idx}`,
        agent: "verification",
        severity: "info",
        field: correction.field_name,
        fieldId: correction.field_id,
        message: `Field correction identified: ${correction.field_name}`,
        details: correction.reason,
      });
    });
  }

  // Extract from OrderDocs preflight warnings (loan readiness issues)
  const orderdocsOutput = runDetail.agents.orderdocs?.output as {
    preflight_warnings?: Array<{ flag: string; name: string; message: string }>;
  };
  if (orderdocsOutput?.preflight_warnings) {
    orderdocsOutput.preflight_warnings.forEach((warning, idx) => {
      items.push({
        id: `orderdocs-preflight-${idx}`,
        agent: "orderdocs",
        severity: "warning",
        message: `⚠️ ${warning.name}: Not Complete`,
        details: warning.message,
      });
    });
  }

  // Extract from Discrepancy Detection (Hard Stops & PTF Conditions)
  const discrepancyOutput = runDetail.agents.discrepancy?.output as {
    hard_stops?: Array<{
      field_id: string;
      field_name: string;
      extracted: string;
      encompass: string;
      action: string;
      message: string;
    }>;
    soft_discrepancies?: Array<{
      field_id: string;
      field_name: string;
      extracted: string;
      encompass: string;
      ptf_text: string;
    }>;
  };
  
  // Hard Stops (CRITICAL - blocks pipeline)
  if (discrepancyOutput?.hard_stops) {
    discrepancyOutput.hard_stops.forEach((stop, idx) => {
      items.push({
        id: `discrepancy-hardstop-${idx}`,
        agent: "drawcore", // Show as drawcore issue in main flagged items
        severity: "error",
        field: stop.field_name,
        fieldId: stop.field_id,
        message: `🛑 HARD STOP: ${stop.field_name} mismatch`,
        details: `Extracted: ${stop.extracted} | Encompass: ${stop.encompass} | Action: ${stop.action}`,
      });
    });
  }
  
  // PTF Conditions (Warnings)
  if (discrepancyOutput?.soft_discrepancies) {
    discrepancyOutput.soft_discrepancies.forEach((discrep, idx) => {
      items.push({
        id: `discrepancy-ptf-${idx}`,
        agent: "drawcore",
        severity: "warning",
        field: discrep.field_name,
        fieldId: discrep.field_id,
        message: `PTF Condition: ${discrep.field_name}`,
        details: discrep.ptf_text,
      });
    });
  }

  return items;
}

function extractFieldChanges(runDetail: RunDetail): FieldChange[] {
  const changes: FieldChange[] = [];

  // Extract from preparation output
  const prepOutput = runDetail.agents.preparation?.output as {
    results?: {
      field_mappings?: Record<string, { value: string; attachment_id?: string }>;
    };
  };
  if (prepOutput?.results?.field_mappings) {
    Object.entries(prepOutput.results.field_mappings).forEach(([fieldId, mapping]) => {
      if (mapping.value && mapping.value !== "" && mapping.value !== "0") {
        changes.push({
          fieldId,
          fieldName: fieldId, // Could map to friendly names
          oldValue: null,
          newValue: String(mapping.value),
          source: mapping.attachment_id || "Document",
          agent: "preparation",
        });
      }
    });
  }

  // Extract from corrected_fields_summary
  if (runDetail.corrected_fields_summary) {
    runDetail.corrected_fields_summary.forEach(field => {
      // Check if already in changes
      const existingIdx = changes.findIndex(c => c.fieldId === field.field_id);
      if (existingIdx >= 0) {
        changes[existingIdx].newValue = field.corrected_value;
        changes[existingIdx].agent = "verification";
      } else {
        changes.push({
          fieldId: field.field_id,
          fieldName: field.field_name,
          oldValue: null,
          newValue: field.corrected_value,
          source: field.document_filename || "Verification",
          agent: "verification",
        });
      }
    });
  }

  return changes;
}

function getSeverityColor(severity: FlaggedItem["severity"]) {
  switch (severity) {
    case "error":
      return { bg: "bg-red-50", border: "border-red-200", text: "text-red-700", icon: XCircle };
    case "warning":
      return { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", icon: AlertTriangle };
    case "info":
      return { bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700", icon: Flag };
  }
}

// =============================================================================
// SUMMARY CARD
// =============================================================================

interface SummaryCardProps {
  runDetail: RunDetail;
  flaggedItems: FlaggedItem[];
  fieldChanges: FieldChange[];
}

function SummaryCard({ runDetail, flaggedItems, fieldChanges }: SummaryCardProps) {
  const errorCount = flaggedItems.filter(i => i.severity === "error").length;
  const warningCount = flaggedItems.filter(i => i.severity === "warning").length;
  const infoCount = flaggedItems.filter(i => i.severity === "info").length;
  
  const prepOutput = runDetail.agents.preparation?.output as {
    documents_processed?: number;
    total_documents_found?: number;
  };

  const stats = [
    {
      label: "Documents Processed",
      value: prepOutput?.documents_processed || 0,
      total: prepOutput?.total_documents_found,
      icon: FileText,
      color: "text-blue-600",
    },
    {
      label: "Fields Updated",
      value: fieldChanges.length,
      icon: Pencil,
      color: "text-emerald-600",
    },
    {
      label: "Errors",
      value: errorCount,
      icon: XCircle,
      color: errorCount > 0 ? "text-red-600" : "text-slate-400",
    },
    {
      label: "Warnings",
      value: warningCount,
      icon: AlertTriangle,
      color: warningCount > 0 ? "text-amber-600" : "text-slate-400",
    },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
          Run Summary
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stats.map((stat) => (
            <div key={stat.label} className="text-center p-3 rounded-lg bg-muted/50">
              <stat.icon className={cn("h-6 w-6 mx-auto mb-2", stat.color)} />
              <p className="text-2xl font-bold">
                {stat.value}
                {stat.total && <span className="text-sm text-muted-foreground">/{stat.total}</span>}
              </p>
              <p className="text-xs text-muted-foreground">{stat.label}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// FLAGGED ITEMS CARD
// =============================================================================

interface FlaggedItemsCardProps {
  items: FlaggedItem[];
  agentType?: AgentType;
}

function FlaggedItemsCard({ items, agentType }: FlaggedItemsCardProps) {
  if (items.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Flag className="h-4 w-4 text-muted-foreground" />
            Flagged Items
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <CheckCircle2 className="h-5 w-5 mr-2 text-emerald-500" />
            No issues flagged
          </div>
        </CardContent>
      </Card>
    );
  }

  // Group by severity
  const errors = items.filter(i => i.severity === "error");
  const warnings = items.filter(i => i.severity === "warning");
  const infos = items.filter(i => i.severity === "info");

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Flag className="h-4 w-4 text-muted-foreground" />
          Flagged Items
          <span className="ml-auto text-xs font-normal text-muted-foreground">
            {items.length} total
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px] pr-4">
          <div className="space-y-4">
            {errors.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-red-700 mb-2 flex items-center gap-1">
                  <XCircle className="h-3 w-3" /> Errors ({errors.length})
                </h4>
                <div className="space-y-2">
                  {errors.map(item => {
                    const colors = getSeverityColor(item.severity);
                    return (
                      <div
                        key={item.id}
                        className={cn("p-3 rounded-lg border", colors.bg, colors.border)}
                      >
                        <div className="flex items-start gap-2">
                          <AgentIcon type={item.agent} size="sm" pipelineType={agentType} />
                          <div className="flex-1 min-w-0">
                            <p className={cn("text-sm font-medium", colors.text)}>
                              {item.message}
                            </p>
                            {item.details && (
                              <p className="text-xs text-muted-foreground mt-1 truncate">
                                {item.details}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {warnings.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-amber-700 mb-2 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" /> Warnings ({warnings.length})
                </h4>
                <div className="space-y-2">
                  {warnings.map(item => {
                    const colors = getSeverityColor(item.severity);
                    return (
                      <div
                        key={item.id}
                        className={cn("p-3 rounded-lg border", colors.bg, colors.border)}
                      >
                        <div className="flex items-start gap-2">
                          <AgentIcon type={item.agent} size="sm" pipelineType={agentType} />
                          <div className="flex-1 min-w-0">
                            <p className={cn("text-sm font-medium", colors.text)}>
                              {item.message}
                            </p>
                            {item.details && (
                              <p className="text-xs text-muted-foreground mt-1 truncate">
                                {item.details}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {infos.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-blue-700 mb-2 flex items-center gap-1">
                  <Flag className="h-3 w-3" /> Info ({infos.length})
                </h4>
                <div className="space-y-2">
                  {infos.map(item => {
                    const colors = getSeverityColor(item.severity);
                    return (
                      <div
                        key={item.id}
                        className={cn("p-3 rounded-lg border", colors.bg, colors.border)}
                      >
                        <div className="flex items-start gap-2">
                          <AgentIcon type={item.agent} size="sm" pipelineType={agentType} />
                          <div className="flex-1 min-w-0">
                            <p className={cn("text-sm font-medium", colors.text)}>
                              {item.message}
                            </p>
                            {item.fieldId && (
                              <p className="text-xs font-mono text-muted-foreground mt-1">
                                Field: {item.fieldId}
                              </p>
                            )}
                            {item.details && (
                              <p className="text-xs text-muted-foreground mt-1">
                                {item.details}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// FIELD CHANGES CARD
// =============================================================================

interface FieldChangesCardProps {
  changes: FieldChange[];
  agentType?: AgentType;
}

function FieldChangesCard({ changes, agentType }: FieldChangesCardProps) {
  const [copied, setCopied] = React.useState(false);

  const copyToClipboard = () => {
    const text = changes.map(c => `${c.fieldId}: ${c.newValue}`).join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (changes.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Pencil className="h-4 w-4 text-muted-foreground" />
            Field Updates
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            No field updates extracted
          </div>
        </CardContent>
      </Card>
    );
  }

  // Group by agent
  const byAgent = changes.reduce((acc, change) => {
    if (!acc[change.agent]) acc[change.agent] = [];
    acc[change.agent].push(change);
    return acc;
  }, {} as Record<string, FieldChange[]>);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Pencil className="h-4 w-4 text-muted-foreground" />
          Field Updates
          <span className="ml-auto flex items-center gap-2">
            <span className="text-xs font-normal text-muted-foreground">
              {changes.length} fields
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2"
              onClick={copyToClipboard}
            >
              {copied ? (
                <Check className="h-3 w-3 text-emerald-500" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
            </Button>
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-4">
          <div className="space-y-4">
            {Object.entries(byAgent).map(([agent, agentChanges]) => (
              <div key={agent}>
                <div className="flex items-center gap-2 mb-2">
                  <AgentIcon type={agent as FieldChange["agent"]} size="sm" pipelineType={agentType} />
                  <h4 className="text-xs font-semibold capitalize">
                    {agent} Agent ({agentChanges.length})
                  </h4>
                </div>
                <div className="space-y-1 ml-6">
                  {agentChanges.slice(0, 20).map((change, idx) => (
                    <div
                      key={`${change.fieldId}-${idx}`}
                      className="flex items-center gap-2 p-2 rounded bg-muted/50 text-sm"
                    >
                      <span className="font-mono text-xs text-muted-foreground w-32 truncate">
                        {change.fieldId}
                      </span>
                      <ArrowRight className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                      <span className="font-medium text-emerald-700 truncate flex-1">
                        {change.newValue || "(empty)"}
                      </span>
                    </div>
                  ))}
                  {agentChanges.length > 20 && (
                    <p className="text-xs text-muted-foreground text-center py-2">
                      +{agentChanges.length - 20} more fields
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// AGENT STATUS SUMMARY
// =============================================================================

interface AgentStatusSummaryProps {
  runDetail: RunDetail;
  agentType?: AgentType;
}

function AgentStatusSummary({ runDetail, agentType = "drawdocs" }: AgentStatusSummaryProps) {
  const subAgents = getSubAgents(agentType);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Agent Status</CardTitle>
      </CardHeader>
      <CardContent>
        <div className={cn(
          "grid gap-3",
          subAgents.length === 3 ? "grid-cols-3" : "grid-cols-2 md:grid-cols-4"
        )}>
          {subAgents.map((subAgent) => {
            const agent = runDetail.agents[subAgent.id];
            const status = agent?.status || "pending";
            const time = agent?.elapsed_seconds || 0;

            return (
              <div
                key={subAgent.id}
                className={cn(
                  "p-3 rounded-lg border text-center",
                  status === "success" && "bg-emerald-50 border-emerald-200",
                  status === "failed" && "bg-red-50 border-red-200",
                  status === "running" && "bg-blue-50 border-blue-200",
                  status === "blocked" && "bg-amber-50 border-amber-200",
                  status === "pending" && "bg-slate-50 border-slate-200"
                )}
              >
                <AgentIcon type={subAgent.id} size="sm" className="mx-auto mb-1" pipelineType={agentType} />
                <p className="text-xs font-medium">{subAgent.name}</p>
                <p className={cn(
                  "text-xs mt-1",
                  status === "success" && "text-emerald-600",
                  status === "failed" && "text-red-600",
                  status === "running" && "text-blue-600",
                  status === "blocked" && "text-amber-600",
                  status === "pending" && "text-slate-400"
                )}>
                  {status === "success" && `✓ ${time.toFixed(1)}s`}
                  {status === "failed" && "✗ Failed"}
                  {status === "running" && "Running..."}
                  {status === "blocked" && "⚠ Blocked"}
                  {status === "pending" && "Pending"}
                </p>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// DRAWCORE PHASES CARD
// =============================================================================

interface DrawcorePhasesCardProps {
  runDetail: RunDetail;
}

function DrawcorePhasesCard({ runDetail }: DrawcorePhasesCardProps) {
  const [expanded, setExpanded] = React.useState(false);
  
  const drawcoreOutput = runDetail.agents.drawcore?.output as {
    phases?: Record<string, {
      status: string;
      fields_processed: number;
      fields_updated: number;
      issues_logged: number;
      updates?: Array<{ field_id: string; value: string }>;
      issues?: Array<{ type: string; message: string }>;
    }>;
    summary?: {
      total_fields_processed: number;
      total_fields_updated: number;
      total_issues_logged: number;
      phases_completed: number;
      phases_failed: number;
    };
    dry_run?: boolean;
  };

  if (!drawcoreOutput?.phases) {
    return null;
  }

  const phases = Object.entries(drawcoreOutput.phases);
  const summary = drawcoreOutput.summary;

  const phaseNames: Record<string, string> = {
    phase_1: "Borrower & LO Info",
    phase_2: "File Contacts (Title, Escrow, Insurance)",
    phase_3: "Property & Program",
    phase_4: "Financial Setup",
    phase_5: "Closing Disclosure",
    phase_7: "Escrow Calculations (SOP Step 19)",
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Zap className="h-4 w-4 text-orange-500" />
          Drawcore Phases
          {drawcoreOutput.dry_run && (
            <Badge variant="outline" className="ml-2 text-xs">Dry Run</Badge>
          )}
          <span className="ml-auto text-xs font-normal text-muted-foreground">
            {summary?.phases_completed || 0}/{phases.length} completed
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {/* Summary Row */}
          <div className="flex items-center justify-between p-2 bg-muted/50 rounded-lg text-sm">
            <span className="text-muted-foreground">Total Fields Updated:</span>
            <span className="font-semibold">{summary?.total_fields_updated || 0}</span>
          </div>
          
          {/* Phase List */}
          <div className="space-y-1">
            {phases.map(([phaseKey, phase]) => (
              <div
                key={phaseKey}
                className={cn(
                  "flex items-center gap-2 p-2 rounded text-sm border",
                  phase.status === "success" && "bg-emerald-50/50 border-emerald-200",
                  phase.status === "failed" && "bg-red-50/50 border-red-200",
                  phase.status === "skipped" && "bg-slate-50 border-slate-200"
                )}
              >
                {phase.status === "success" ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0" />
                ) : phase.status === "failed" ? (
                  <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                ) : (
                  <Clock className="h-4 w-4 text-slate-400 flex-shrink-0" />
                )}
                <span className="flex-1">{phaseNames[phaseKey] || phaseKey}</span>
                <span className="text-xs text-muted-foreground">
                  {phase.fields_updated}/{phase.fields_processed} fields
                </span>
              </div>
            ))}
          </div>

          {/* Expandable Updates */}
          {expanded && (
            <div className="mt-3 pt-3 border-t">
              <h4 className="text-xs font-semibold mb-2">Field Updates</h4>
              <ScrollArea className="h-[200px]">
                {phases.flatMap(([, phase]) => phase.updates || []).length === 0 ? (
                  <p className="text-xs text-muted-foreground">No field updates recorded</p>
                ) : (
                  <div className="space-y-1">
                    {phases.flatMap(([phaseKey, phase]) =>
                      (phase.updates || []).map((update, idx) => (
                        <div key={`${phaseKey}-${idx}`} className="flex items-center gap-2 text-xs p-1 bg-muted/30 rounded">
                          <span className="font-mono text-muted-foreground">{update.field_id}</span>
                          <ArrowRight className="h-3 w-3" />
                          <span className="text-emerald-700 truncate">{update.value}</span>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </ScrollArea>
            </div>
          )}

          <Button
            variant="ghost"
            size="sm"
            className="w-full mt-2"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <>
                <ChevronDown className="h-4 w-4 mr-1" /> Hide Details
              </>
            ) : (
              <>
                <ChevronRight className="h-4 w-4 mr-1" /> Show Details
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// DISCREPANCY DETECTION CARD (Phase 1: PTF Conditions)
// =============================================================================

interface DiscrepancyDetectionCardProps {
  runDetail: RunDetail;
}

function DiscrepancyDetectionCard({ runDetail }: DiscrepancyDetectionCardProps) {
  const [expandedHardStops, setExpandedHardStops] = React.useState(true);
  const [expandedPTF, setExpandedPTF] = React.useState(true);
  
  const discrepancyOutput = runDetail.agents.discrepancy?.output as {
    status?: string;
    hard_stops?: Array<{
      field_id: string;
      field_name: string;
      extracted: string;
      encompass: string;
      action: string;
      message: string;
      source_doc?: string;
    }>;
    soft_discrepancies?: Array<{
      field_id: string;
      field_name: string;
      extracted: string;
      encompass: string;
      ptf_text: string;
      assigned_to?: string;
      severity?: string;
      ptf_added?: boolean;
      condition_id?: string;
    }>;
    ptf_conditions_added?: number;
    fields_checked?: number;
    discrepancies_found?: number;
    acceptable_variances?: number;
    summary?: string;
  };

  if (!discrepancyOutput) {
    return null;
  }

  const hardStops = discrepancyOutput.hard_stops || [];
  const softDiscrepancies = discrepancyOutput.soft_discrepancies || [];
  const status = discrepancyOutput.status || "unknown";
  const fieldsChecked = discrepancyOutput.fields_checked || 0;
  const discrepanciesFound = discrepancyOutput.discrepancies_found || 0;
  const ptfCount = discrepancyOutput.ptf_conditions_added || 0;
  const acceptableVariances = discrepancyOutput.acceptable_variances || 0;

  // Status badge
  let statusBadge;
  if (status === "blocked") {
    statusBadge = (
      <Badge variant="outline" className="border-red-600 text-red-600 text-xs font-semibold">
        BLOCKED
      </Badge>
    );
  } else if (status === "proceed_with_conditions") {
    statusBadge = (
      <Badge variant="outline" className="border-amber-500 text-amber-600 text-xs font-medium">
        Dry Run
      </Badge>
    );
  } else if (status === "success") {
    statusBadge = (
      <Badge variant="outline" className="border-emerald-500 text-emerald-600 text-xs font-medium">
        ✓ Clean
      </Badge>
    );
  }

  return (
    <Card className={cn(
      status === "blocked" && "border-red-300 bg-red-50/30"
    )}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <AlertTriangle className={cn(
                "h-5 w-5 flex-shrink-0",
                status === "blocked" ? "text-red-600" : "text-amber-500"
              )} />
              Discrepancy Detection
            </CardTitle>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-xs text-slate-500">{fieldsChecked} fields checked</span>
              <span className="text-xs text-slate-300">•</span>
              <span className="text-xs text-amber-600 font-medium">{discrepanciesFound} discrepancies</span>
            </div>
          </div>
          {statusBadge}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Demo Mode Warning - Hard Stops Detected */}
        {hardStops.length > 0 && runDetail.demo_mode && (
          <div className="flex items-start gap-2 p-3 rounded-md bg-amber-50 border border-amber-200">
            <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-amber-900">
                Demo Mode Active
              </div>
              <div className="text-xs text-amber-700 mt-1 leading-relaxed">
                Pipeline continued for testing. In production, hard stops would HALT the process.
              </div>
            </div>
          </div>
        )}
        {/* Quick Stats */}
        <div className="flex items-center gap-4 text-xs pb-2 border-b">
          {acceptableVariances > 0 && (
            <div className="flex items-center gap-1.5">
              <div className="h-2 w-2 rounded-full bg-emerald-500"></div>
              <span className="text-slate-600">{acceptableVariances} acceptable</span>
            </div>
          )}
          {ptfCount > 0 && (
            <div className="flex items-center gap-1.5">
              <div className="h-2 w-2 rounded-full bg-amber-500"></div>
              <span className="text-slate-600">{ptfCount} PTF added</span>
            </div>
          )}
        </div>

        {/* Hard Stops Section */}
        {hardStops.length > 0 && (
          <div className="border border-red-300 rounded-lg bg-red-50/50">
            <button
              onClick={() => setExpandedHardStops(!expandedHardStops)}
              className="w-full p-3 flex items-center justify-between hover:bg-red-100/50 transition-colors rounded-t-lg"
            >
              <div className="flex items-center gap-2">
                <XCircle className="h-4 w-4 text-red-600" />
                <span className="text-sm font-medium text-red-900">
                  Hard Stops ({hardStops.length})
                </span>
              </div>
              {expandedHardStops ? (
                <ChevronDown className="h-4 w-4 text-red-600" />
              ) : (
                <ChevronRight className="h-4 w-4 text-red-600" />
              )}
            </button>
            
            {expandedHardStops && (
              <div className="p-4 space-y-4 border-t border-red-200 bg-white">
                {hardStops.map((stop, idx) => (
                  <div key={idx} className="space-y-3">
                    {/* Header */}
                    <div className="flex items-start gap-2">
                      <XCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-sm text-slate-900">
                          {stop.field_name}
                        </div>
                        <code className="text-xs text-slate-500 font-mono mt-0.5 inline-block">
                          {stop.field_id}
                        </code>
                      </div>
                    </div>
                    
                    {/* Values Comparison - Side by Side */}
                    <div className="grid grid-cols-2 gap-3 pl-7">
                      <div>
                        <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-1">
                          Extracted
                        </div>
                        <div className="font-mono text-sm text-red-600 font-semibold break-words">
                          {stop.extracted}
                        </div>
                        {stop.source_doc && (
                          <div className="text-[11px] text-slate-500 mt-1">
                            from {stop.source_doc}
                          </div>
                        )}
                      </div>
                      <div>
                        <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-1">
                          Encompass
                        </div>
                        <div className="font-mono text-sm text-slate-700 break-words">
                          {stop.encompass}
                        </div>
                      </div>
                    </div>
                    
                    {/* Action Required */}
                    <div className="pl-7 pt-2 border-t border-slate-100">
                      <div className="text-xs font-medium text-red-900 mb-1">
                        ⚠️ Action Required
                      </div>
                      <div className="text-xs text-slate-600 leading-relaxed">
                        {stop.action}
                      </div>
                    </div>
                    
                    {idx < hardStops.length - 1 && (
                      <div className="border-b border-slate-200 mt-4"></div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* PTF Conditions Section */}
        {softDiscrepancies.length > 0 && (
          <div className="border border-amber-300 rounded-lg bg-amber-50/50">
            <button
              onClick={() => setExpandedPTF(!expandedPTF)}
              className="w-full p-3 flex items-center justify-between hover:bg-amber-100/50 transition-colors rounded-t-lg"
            >
              <div className="flex items-center gap-2">
                <Flag className="h-4 w-4 text-amber-600" />
                <span className="text-sm font-medium text-amber-900">
                  PTF Conditions ({softDiscrepancies.length})
                </span>
              </div>
              {expandedPTF ? (
                <ChevronDown className="h-4 w-4 text-amber-600" />
              ) : (
                <ChevronRight className="h-4 w-4 text-amber-600" />
              )}
            </button>
            
            {expandedPTF && (
              <div className="p-4 space-y-4 border-t border-amber-200 bg-white">
                {softDiscrepancies.map((discrep, idx) => (
                  <div key={idx} className="space-y-3">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-2 flex-1 min-w-0">
                        <Flag className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-sm text-slate-900">
                            {discrep.field_name}
                          </div>
                          <code className="text-xs text-slate-500 font-mono mt-0.5 inline-block">
                            {discrep.field_id}
                          </code>
                        </div>
                      </div>
                      {discrep.ptf_added && (
                        <Badge variant="outline" className="text-[10px] bg-emerald-50 text-emerald-600 border-emerald-400 flex-shrink-0">
                          ✓ PTF
                        </Badge>
                      )}
                    </div>
                    
                    {/* Values Comparison */}
                    <div className="grid grid-cols-2 gap-3 pl-7">
                      <div>
                        <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-1">
                          Extracted
                        </div>
                        <div className="font-mono text-sm text-amber-700 font-medium break-words">
                          {discrep.extracted}
                        </div>
                      </div>
                      <div>
                        <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-1">
                          Encompass
                        </div>
                        <div className="font-mono text-sm text-slate-700 break-words">
                          {discrep.encompass}
                        </div>
                      </div>
                    </div>
                    
                    {/* PTF Text */}
                    <div className="pl-7 pt-2 border-t border-slate-100">
                      <div className="text-xs font-medium text-amber-900 mb-1">
                        📋 PTF Condition
                      </div>
                      <div className="text-xs text-slate-600 leading-relaxed">
                        {discrep.ptf_text}
                      </div>
                      {discrep.assigned_to && (
                        <div className="text-[11px] text-slate-500 mt-2">
                          Assigned to: <span className="font-medium text-slate-700">{discrep.assigned_to}</span>
                        </div>
                      )}
                    </div>
                    
                    {idx < softDiscrepancies.length - 1 && (
                      <div className="border-b border-slate-200 mt-4"></div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* No Issues */}
        {hardStops.length === 0 && softDiscrepancies.length === 0 && status === "success" && (
          <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-center">
            <CheckCircle2 className="h-8 w-8 text-emerald-600 mx-auto mb-2" />
            <div className="text-sm font-medium text-emerald-900">
              No Discrepancies Found
            </div>
            <div className="text-xs text-emerald-700 mt-1">
              All {fieldsChecked} extracted fields match Encompass values
            </div>
          </div>
        )}

        {/* Summary */}
        {discrepancyOutput.summary && (
          <div className="text-xs text-slate-600 italic border-t pt-2">
            {discrepancyOutput.summary}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// ORDERDOCS STEPS CARD
// =============================================================================

interface OrderDocsStepsCardProps {
  runDetail: RunDetail;
}

function OrderDocsStepsCard({ runDetail }: OrderDocsStepsCardProps) {
  const orderdocsOutput = runDetail.agents.orderdocs?.output as {
    steps?: {
      mavent_check?: {
        audit_id?: string;
        status?: string;
        issues?: Array<{ message: string }>;
        error?: string;
        dry_run?: boolean;
      };
      order_documents?: {
        doc_set_id?: string;
        status?: string;
        documents?: string[];
        error?: string;
        dry_run?: boolean;
      };
      deliver_documents?: {
        status?: string;
        delivery_method?: string;
        error?: string;
        dry_run?: boolean;
      };
    };
    preflight_warnings?: Array<{
      flag: string;
      name: string;
      field_id?: string;
      value?: string | null;
      expected?: string;
      status: boolean;
      message: string;
    }>;
    preflight_checks?: {
      loan_id: string;
      all_passed: boolean;
      core_checks_passed: boolean;
      g1_passed: boolean;
      mvp_passed: boolean;
      checks: Record<string, {
        passed: boolean;
        field_id: string;
        field_name: string;
        value: string | null;
        expected_value: string;
        rule: string;
        failure_reason: string | null;
        additional_fields?: Record<string, { name: string; value: string | null; passed?: boolean }>;
      }>;
      g1_requirements?: Record<string, {
        passed: boolean;
        field_id: string;
        field_name: string;
        value: string | null;
        rule: string;
        failure_reason: string | null;
      }>;
      mvp_eligibility?: Record<string, {
        passed: boolean;
        field_id: string;
        field_name: string;
        value: string | null;
        rule: string;
        failure_reason: string | null;
      }>;
      blockers: Array<{ check: string; field_id: string; field_name: string; value: string | null; message: string }>;
      warnings: Array<{ check: string; field_id: string; field_name: string; value: string | null; message: string }>;
      raw_field_values: Record<string, string>;
    };
    summary?: {
      audit_id?: string;
      doc_set_id?: string;
      compliance_issues?: number;
      documents_ordered?: number;
      delivery_method?: string;
    };
    dry_run?: boolean;
    status?: string;
  };

  if (!orderdocsOutput?.steps) {
    return null;
  }

  const steps = orderdocsOutput.steps;
  const summary = orderdocsOutput.summary;
  const preflightWarnings = orderdocsOutput.preflight_warnings || [];
  const preflightChecks = orderdocsOutput.preflight_checks;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Package className="h-4 w-4 text-purple-500" />
          Order Documents Pipeline
          {orderdocsOutput.dry_run && (
            <Badge variant="outline" className="ml-2 text-xs">Dry Run</Badge>
          )}
          {preflightChecks?.all_passed && (
            <Badge variant="outline" className="ml-2 text-xs bg-emerald-100 border-emerald-300 text-emerald-700">
              ✓ All Checks Passed
            </Badge>
          )}
          {!preflightChecks?.all_passed && preflightWarnings.length > 0 && (
            <Badge variant="outline" className="ml-2 text-xs bg-amber-100 border-amber-300 text-amber-700">
              {preflightWarnings.length} Warning{preflightWarnings.length > 1 ? 's' : ''}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {/* Pre-flight Checks - Detailed View */}
          {preflightChecks && (
            <div className={cn(
              "p-3 rounded-lg border mb-4",
              preflightChecks.all_passed ? "bg-emerald-50/50 border-emerald-200" : "bg-amber-50/50 border-amber-200"
            )}>
              <div className="flex items-center gap-2 mb-3">
                {preflightChecks.all_passed ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                )}
                <span className={cn(
                  "font-medium text-sm",
                  preflightChecks.all_passed ? "text-emerald-800" : "text-amber-800"
                )}>
                  Loan Readiness Pre-flight Checks
                </span>
              </div>

              {/* Core Checks: CTC, CD Approved, CD Acknowledged */}
              <div className="space-y-2 mb-3">
                <p className="text-xs font-semibold text-slate-700 uppercase tracking-wide">Core Prerequisites</p>
                {Object.entries(preflightChecks.checks || {}).map(([checkName, checkData]) => (
                  <div key={checkName} className={cn(
                    "p-2 rounded border text-xs",
                    checkData.passed ? "bg-white border-emerald-200" : "bg-red-50 border-red-200"
                  )}>
                    <div className="flex items-start gap-2">
                      {checkData.passed ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 mt-0.5 flex-shrink-0" />
                      ) : (
                        <XCircle className="h-3.5 w-3.5 text-red-500 mt-0.5 flex-shrink-0" />
                      )}
                      <div className="flex-1 min-w-0 overflow-hidden">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium break-words">{checkData.field_name}</span>
                          <code className="text-[10px] bg-slate-100 px-1 py-0.5 rounded text-slate-600 flex-shrink-0">
                            {checkData.field_id}
                          </code>
                        </div>
                        <div className="mt-1 flex flex-col gap-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-slate-500 flex-shrink-0">Value:</span>
                            <span className={cn(
                              "font-mono text-[11px] break-all",
                              checkData.value ? "text-slate-800" : "text-red-600 italic"
                            )}>
                              {checkData.value ?? "(empty)"}
                            </span>
                          </div>
                          {!checkData.passed && checkData.expected_value && (
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-slate-500 flex-shrink-0">Expected:</span>
                              <span className="text-emerald-700 font-mono text-[11px] break-all">{checkData.expected_value}</span>
                            </div>
                          )}
                        </div>
                        {checkData.rule && (
                          <p className="mt-1 text-slate-500 text-[11px] break-words">{checkData.rule}</p>
                        )}
                        {!checkData.passed && checkData.failure_reason && (
                          <p className="mt-1 text-red-600 font-medium text-[11px] break-words">⚠ {checkData.failure_reason}</p>
                        )}
                        {/* Additional Fields */}
                        {checkData.additional_fields && Object.keys(checkData.additional_fields).length > 0 && (
                          <div className="mt-2 pl-3 border-l-2 border-slate-200 space-y-1">
                            {Object.entries(checkData.additional_fields).map(([fieldId, fieldData]) => (
                              <div key={fieldId} className="flex items-center gap-2 text-[11px]">
                                <code className="bg-slate-100 px-1 rounded">{fieldId}</code>
                                <span className="text-slate-500">{fieldData.name}:</span>
                                <span className="font-mono">{fieldData.value ?? "(empty)"}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* G1 Requirements */}
              {preflightChecks.g1_requirements && Object.keys(preflightChecks.g1_requirements).length > 0 && (
                <div className="space-y-2 mb-3">
                  <p className="text-xs font-semibold text-slate-700 uppercase tracking-wide">G1 Required Fields</p>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(preflightChecks.g1_requirements).map(([checkName, checkData]) => (
                      <div key={checkName} className={cn(
                        "p-2 rounded border text-xs",
                        checkData.passed ? "bg-white border-emerald-200" : "bg-red-50 border-red-200"
                      )}>
                        <div className="flex items-center gap-2">
                          {checkData.passed ? (
                            <CheckCircle2 className="h-3 w-3 text-emerald-500 flex-shrink-0" />
                          ) : (
                            <XCircle className="h-3 w-3 text-red-500 flex-shrink-0" />
                          )}
                          <span className="font-medium truncate">{checkData.field_name}</span>
                        </div>
                        <div className="mt-1 flex items-center gap-1">
                          <code className="text-[10px] bg-slate-100 px-1 rounded">{checkData.field_id}</code>
                          <span className={cn(
                            "font-mono text-[11px]",
                            checkData.value ? "text-slate-800" : "text-red-600"
                          )}>
                            {checkData.value ? `✓ ${String(checkData.value).substring(0, 20)}${String(checkData.value).length > 20 ? '...' : ''}` : "MISSING"}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* MVP Eligibility */}
              {preflightChecks.mvp_eligibility && Object.keys(preflightChecks.mvp_eligibility).length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-slate-700 uppercase tracking-wide">MVP Eligibility</p>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(preflightChecks.mvp_eligibility).map(([checkName, checkData]) => (
                      <div key={checkName} className={cn(
                        "p-2 rounded border text-xs",
                        checkData.passed ? "bg-white border-emerald-200" : "bg-yellow-50 border-yellow-200"
                      )}>
                        <div className="flex items-center gap-2">
                          {checkData.passed ? (
                            <CheckCircle2 className="h-3 w-3 text-emerald-500 flex-shrink-0" />
                          ) : (
                            <AlertTriangle className="h-3 w-3 text-yellow-500 flex-shrink-0" />
                          )}
                          <span className="font-medium truncate">{checkData.field_name}</span>
                        </div>
                        <div className="mt-1 flex items-center gap-1">
                          <code className="text-[10px] bg-slate-100 px-1 rounded">{checkData.field_id}</code>
                          <span className="font-mono text-[11px] text-slate-800">
                            {checkData.value ?? "(empty)"}
                          </span>
                        </div>
                        {!checkData.passed && checkData.failure_reason && (
                          <p className="mt-1 text-yellow-700 text-[11px]">{checkData.failure_reason}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Legacy Pre-flight Warnings (fallback if no detailed checks) */}
          {!preflightChecks && preflightWarnings.length > 0 && (
            <div className="p-3 rounded-lg border bg-amber-50/50 border-amber-200 mb-4">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="h-4 w-4 text-amber-600" />
                <span className="font-medium text-sm text-amber-800">Loan Readiness Warnings</span>
              </div>
              <p className="text-xs text-amber-700 mb-2">
                The following prerequisites are not met - this may cause document generation to fail:
              </p>
              <div className="space-y-1.5">
                {preflightWarnings.map((warning, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-xs">
                    <XCircle className="h-3.5 w-3.5 text-red-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="text-amber-900 font-medium">{warning.name}</span>
                      {warning.field_id && (
                        <code className="ml-1 text-[10px] bg-amber-100 px-1 rounded">{warning.field_id}</code>
                      )}
                      <span className="text-amber-700">: {warning.value ?? "Not Set"}</span>
                      {warning.expected && (
                        <span className="text-slate-500 ml-1">(expected: {warning.expected})</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-amber-600 mt-2 italic">
                Ensure the loan is Clear to Close and the Closing Disclosure is approved/acknowledged before ordering closing documents.
              </p>
            </div>
          )}
          {/* Step 1: Mavent Check */}
          <div className={cn(
            "p-3 rounded-lg border",
            steps.mavent_check?.status === "Completed" ? "bg-emerald-50/50 border-emerald-200" : 
            steps.mavent_check?.error ? "bg-red-50/50 border-red-200" :
            "bg-slate-50/50 border-slate-200"
          )}>
            <div className="flex items-center gap-2">
              <ShieldCheck className={cn(
                "h-4 w-4",
                steps.mavent_check?.status === "Completed" ? "text-emerald-500" : 
                steps.mavent_check?.error ? "text-red-500" : "text-slate-400"
              )} />
              <span className="font-medium text-sm">Mavent Compliance Check</span>
              <Badge variant="outline" className={cn(
                "ml-auto text-xs",
                steps.mavent_check?.error && "bg-red-100 border-red-300 text-red-700"
              )}>
                {steps.mavent_check?.error ? "Error" : steps.mavent_check?.status || "Pending"}
              </Badge>
            </div>
            {steps.mavent_check?.audit_id && !steps.mavent_check?.error && (
              <p className="text-xs text-muted-foreground mt-1 font-mono">
                Audit ID: {steps.mavent_check.audit_id}
              </p>
            )}
            {steps.mavent_check?.error && (
              <div className="mt-2 p-2 bg-red-100 border border-red-200 rounded text-xs text-red-700">
                <strong>Error:</strong> {steps.mavent_check.error}
              </div>
            )}
            {steps.mavent_check?.issues && steps.mavent_check.issues.length > 0 && (
              <div className="mt-2 space-y-1">
                {steps.mavent_check.issues.map((issue, idx) => (
                  <p key={idx} className="text-xs text-amber-700 bg-amber-50 p-1 rounded">
                    ⚠ {issue.message}
                  </p>
                ))}
              </div>
            )}
            {(summary?.compliance_issues ?? 0) > 0 && !steps.mavent_check?.issues?.length && (
              <p className="text-xs text-amber-600 mt-1">
                ⚠ {summary?.compliance_issues} compliance issues found
              </p>
            )}
          </div>

          {/* Step 2: Order Documents */}
          <div className={cn(
            "p-3 rounded-lg border",
            steps.order_documents?.status === "Completed" ? "bg-emerald-50/50 border-emerald-200" : 
            steps.order_documents?.error ? "bg-red-50/50 border-red-200" :
            "bg-slate-50/50 border-slate-200"
          )}>
            <div className="flex items-center gap-2">
              <FileText className={cn(
                "h-4 w-4",
                steps.order_documents?.status === "Completed" ? "text-emerald-500" : 
                steps.order_documents?.error ? "text-red-500" : "text-slate-400"
              )} />
              <span className="font-medium text-sm">Document Generation</span>
              <Badge variant="outline" className={cn(
                "ml-auto text-xs",
                steps.order_documents?.error && "bg-red-100 border-red-300 text-red-700"
              )}>
                {steps.order_documents?.error ? "Error" : steps.order_documents?.status || "Pending"}
              </Badge>
            </div>
            {steps.order_documents?.doc_set_id && !steps.order_documents?.error && (
              <p className="text-xs text-muted-foreground mt-1 font-mono">
                Doc Set ID: {steps.order_documents.doc_set_id}
              </p>
            )}
            {steps.order_documents?.error && (
              <div className="mt-2 p-2 bg-red-100 border border-red-200 rounded text-xs text-red-700">
                <strong>Error:</strong> {steps.order_documents.error}
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              {summary?.documents_ordered || 0} documents generated
            </p>
          </div>

          {/* Step 3: Deliver Documents */}
          <div className={cn(
            "p-3 rounded-lg border",
            steps.deliver_documents?.status === "Success" ? "bg-emerald-50/50 border-emerald-200" : 
            steps.deliver_documents?.error ? "bg-red-50/50 border-red-200" :
            "bg-slate-50/50 border-slate-200"
          )}>
            <div className="flex items-center gap-2">
              <Download className={cn(
                "h-4 w-4",
                steps.deliver_documents?.status === "Success" ? "text-emerald-500" : 
                steps.deliver_documents?.error ? "text-red-500" : "text-slate-400"
              )} />
              <span className="font-medium text-sm">Document Delivery</span>
              <Badge variant="outline" className={cn(
                "ml-auto text-xs",
                steps.deliver_documents?.error && "bg-red-100 border-red-300 text-red-700"
              )}>
                {steps.deliver_documents?.error ? "Error" : steps.deliver_documents?.status || "Pending"}
              </Badge>
            </div>
            {steps.deliver_documents?.error && (
              <div className="mt-2 p-2 bg-red-100 border border-red-200 rounded text-xs text-red-700">
                <strong>Error:</strong> {steps.deliver_documents.error}
              </div>
            )}
            {steps.deliver_documents?.delivery_method && !steps.deliver_documents?.error && (
              <p className="text-xs text-muted-foreground mt-1">
                Method: {steps.deliver_documents.delivery_method}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// VERIFICATION SUMMARY CARD
// =============================================================================

interface VerificationSummaryCardProps {
  runDetail: RunDetail;
}

function VerificationSummaryCard({ runDetail }: VerificationSummaryCardProps) {
  const verificationOutput = runDetail.agents.verification?.output as {
    messages?: string[];
    status?: string;
  };

  if (!verificationOutput?.messages) {
    return null;
  }

  // Try to parse the JSON report from the agent's response
  let verificationReport: {
    status?: string;
    fields_validated?: number;
    valid_fields?: number;
    invalid_fields?: number;
    corrected_fields?: number;
    error?: string;
    recommendation?: string;
  } | null = null;

  for (const msg of verificationOutput.messages) {
    const jsonMatch = msg.match(/```json\s*([\s\S]*?)\s*```/);
    if (jsonMatch) {
      try {
        verificationReport = JSON.parse(jsonMatch[1]);
        break;
      } catch {
        // Continue searching
      }
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-blue-500" />
          Verification Results
        </CardTitle>
      </CardHeader>
      <CardContent>
        {verificationReport ? (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <div className="p-2 bg-muted/50 rounded text-center">
                <p className="text-lg font-bold">{verificationReport.fields_validated || 0}</p>
                <p className="text-xs text-muted-foreground">Fields Checked</p>
              </div>
              <div className="p-2 bg-muted/50 rounded text-center">
                <p className="text-lg font-bold text-emerald-600">{verificationReport.valid_fields || 0}</p>
                <p className="text-xs text-muted-foreground">Valid</p>
              </div>
              <div className="p-2 bg-muted/50 rounded text-center">
                <p className="text-lg font-bold text-amber-600">{verificationReport.corrected_fields || 0}</p>
                <p className="text-xs text-muted-foreground">Corrected</p>
              </div>
              <div className="p-2 bg-muted/50 rounded text-center">
                <p className="text-lg font-bold text-red-600">{verificationReport.invalid_fields || 0}</p>
                <p className="text-xs text-muted-foreground">Invalid</p>
              </div>
            </div>
            
            {verificationReport.error && (
              <div className="p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
                {verificationReport.error}
              </div>
            )}
            
            {verificationReport.recommendation && (
              <div className="p-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-700">
                <strong>Recommendation:</strong> {verificationReport.recommendation}
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-4 text-muted-foreground">
            <p className="text-sm">
              {verificationOutput.status === "success" 
                ? "Verification completed - see logs for details" 
                : "No verification data available"}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// EXPORT BUTTON
// =============================================================================

interface ExportButtonProps {
  runDetail: RunDetail;
}

function ExportButton({ runDetail }: ExportButtonProps) {
  const handleExport = () => {
    const blob = new Blob([JSON.stringify(runDetail, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report_${runDetail.loan_id}_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Button variant="outline" size="sm" onClick={handleExport}>
      <Download className="h-4 w-4 mr-2" />
      Export Report
    </Button>
  );
}

// =============================================================================
// LOADING SKELETON
// =============================================================================

function ReportSkeleton() {
  return (
    <div className="space-y-4">
      {[...Array(4)].map((_, i) => (
        <Card key={i}>
          <CardHeader className="pb-3">
            <Skeleton className="h-4 w-32" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-24 w-full" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// =============================================================================
// SOP FIELDS VERIFICATION CARD
// =============================================================================

interface SOPFieldData {
  field_id: string;
  field_name: string;
  value: string | null;
  status: "populated" | "missing";
  category: string;
  primary_document: string;
  secondary_documents: string;
  required_disclosure: boolean;
}

interface CategorySummary {
  display_name: string;
  total: number;
  populated: number;
  missing: number;
  completion_pct: number;
  fields: {
    populated: SOPFieldData[];
    missing: SOPFieldData[];
  };
}

interface DocumentNeeded {
  document_name: string;
  missing_field_count: number;
  required_disclosure_count: number;
  fields: Array<{ field_id: string; field_name: string; required_disclosure: boolean }>;
  priority: "high" | "medium" | "low";
}

function SOPFieldsCard({ runDetail }: { runDetail: RunDetail }) {
  const [expandedCategories, setExpandedCategories] = React.useState<Set<string>>(new Set());
  const [showMissingOnly, setShowMissingOnly] = React.useState(false);

  // Extract SOP verification data from verification agent output
  const verificationOutput = runDetail.agents.verification?.output as {
    sop_verification?: {
      fields_by_category?: Record<string, CategorySummary>;
      summary?: {
        total: number;
        populated: number;
        missing: number;
        required_missing: number;
        completion_pct: number;
      };
    };
  };

  const sopData = verificationOutput?.sop_verification;
  
  if (!sopData?.fields_by_category) {
    return null; // No SOP data available
  }

  const categories = sopData.fields_by_category;
  const summary = sopData.summary;

  const toggleCategory = (cat: string) => {
    const newSet = new Set(expandedCategories);
    if (newSet.has(cat)) {
      newSet.delete(cat);
    } else {
      newSet.add(cat);
    }
    setExpandedCategories(newSet);
  };

  const categoryOrder = [
    "borrower_info",
    "property_loan", 
    "closing_disclosure",
    "fees_escrow",
    "contacts_vendors",
    "loan_estimate",
    "dates_compliance",
    "other"
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-blue-500" />
            SOP Field Verification
            {summary && (
              <Badge variant="outline" className={cn(
                "ml-2 text-xs",
                summary.completion_pct >= 80 ? "bg-emerald-100 border-emerald-300 text-emerald-700" :
                summary.completion_pct >= 50 ? "bg-amber-100 border-amber-300 text-amber-700" :
                "bg-red-100 border-red-300 text-red-700"
              )}>
                {summary.completion_pct}% Complete
              </Badge>
            )}
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowMissingOnly(!showMissingOnly)}
            className="text-xs"
          >
            {showMissingOnly ? "Show All" : "Missing Only"}
          </Button>
        </div>
        {summary && (
          <p className="text-xs text-muted-foreground mt-1">
            {summary.populated} of {summary.total} fields populated
            {summary.required_missing > 0 && (
              <span className="text-red-600 ml-2">
                ({summary.required_missing} required fields missing)
              </span>
            )}
          </p>
        )}
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px]">
          <div className="space-y-2">
            {categoryOrder.map(catKey => {
              const catData = categories[catKey];
              if (!catData) return null;
              
              const isExpanded = expandedCategories.has(catKey);
              const fieldsToShow = showMissingOnly ? catData.fields.missing : [...catData.fields.populated, ...catData.fields.missing];
              
              if (showMissingOnly && catData.fields.missing.length === 0) return null;
              
              return (
                <div key={catKey} className="border rounded-lg overflow-hidden">
                  <button
                    onClick={() => toggleCategory(catKey)}
                    className="w-full p-3 flex items-center justify-between bg-slate-50 hover:bg-slate-100 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-slate-500" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-slate-500" />
                      )}
                      <span className="font-medium text-sm">{catData.display_name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        "text-xs font-medium",
                        catData.completion_pct >= 80 ? "text-emerald-600" :
                        catData.completion_pct >= 50 ? "text-amber-600" :
                        "text-red-600"
                      )}>
                        {catData.completion_pct}%
                      </span>
                      <span className="text-xs text-muted-foreground">
                        ({catData.populated}/{catData.total})
                      </span>
                      {catData.missing > 0 && (
                        <Badge variant="outline" className="text-xs bg-red-50 border-red-200 text-red-700">
                          {catData.missing} missing
                        </Badge>
                      )}
                    </div>
                  </button>
                  
                  {isExpanded && (
                    <div className="p-2 space-y-1 max-h-[300px] overflow-y-auto">
                      {fieldsToShow.map((field, idx) => (
                        <div
                          key={`${field.field_id}-${idx}`}
                          className={cn(
                            "p-2 rounded text-xs flex items-start gap-2",
                            field.status === "populated" ? "bg-white border border-slate-200" : "bg-red-50 border border-red-200"
                          )}
                        >
                          {field.status === "populated" ? (
                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 mt-0.5 flex-shrink-0" />
                          ) : (
                            <XCircle className="h-3.5 w-3.5 text-red-500 mt-0.5 flex-shrink-0" />
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-medium truncate">{field.field_name}</span>
                              <code className="text-[10px] bg-slate-100 px-1 rounded">{field.field_id}</code>
                              {field.required_disclosure && (
                                <Badge variant="outline" className="text-[9px] bg-purple-50 border-purple-200 text-purple-700">
                                  Required
                                </Badge>
                              )}
                            </div>
                            <div className="mt-1">
                              {field.status === "populated" ? (
                                <span className="text-slate-700 font-mono">
                                  {String(field.value).length > 50 
                                    ? String(field.value).substring(0, 50) + "..." 
                                    : field.value}
                                </span>
                              ) : (
                                <span className="text-red-600 italic">
                                  Missing - Source: {field.primary_document || "Not specified"}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// DOCUMENTS NEEDED CARD
// =============================================================================

function DocumentsNeededCard({ runDetail }: { runDetail: RunDetail }) {
  // Extract documents needed from verification agent output
  const verificationOutput = runDetail.agents.verification?.output as {
    sop_verification?: {
      documents_needed?: DocumentNeeded[];
      summary?: {
        documents_needed_count: number;
      };
    };
  };

  const documentsNeeded = verificationOutput?.sop_verification?.documents_needed;
  
  if (!documentsNeeded || documentsNeeded.length === 0) {
    return null;
  }

  // Sort by priority
  const priorityOrder = { high: 0, medium: 1, low: 2 };
  const sortedDocs = [...documentsNeeded].sort((a, b) => 
    priorityOrder[a.priority] - priorityOrder[b.priority]
  );

  return (
    <Card className="border-red-200 bg-red-50/30">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Download className="h-4 w-4 text-red-500" />
          Documents Needed
          <Badge variant="outline" className="ml-2 text-xs bg-red-100 border-red-300 text-red-700">
            {documentsNeeded.length} documents
          </Badge>
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          The following documents are needed to populate missing fields
        </p>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[350px]">
          <div className="space-y-2">
            {sortedDocs.map((doc, idx) => (
              <div
                key={idx}
                className={cn(
                  "p-3 rounded-lg border",
                  doc.priority === "high" ? "bg-red-50 border-red-200" :
                  doc.priority === "medium" ? "bg-amber-50 border-amber-200" :
                  "bg-slate-50 border-slate-200"
                )}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <FileText className={cn(
                      "h-4 w-4",
                      doc.priority === "high" ? "text-red-500" :
                      doc.priority === "medium" ? "text-amber-500" :
                      "text-slate-500"
                    )} />
                    <span className="font-medium text-sm">{doc.document_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={cn(
                      "text-xs",
                      doc.priority === "high" ? "bg-red-100 border-red-300 text-red-700" :
                      doc.priority === "medium" ? "bg-amber-100 border-amber-300 text-amber-700" :
                      "bg-slate-100 border-slate-300 text-slate-700"
                    )}>
                      {doc.priority.toUpperCase()}
                    </Badge>
                  </div>
                </div>
                
                <div className="text-xs text-muted-foreground mb-2">
                  {doc.missing_field_count} missing field{doc.missing_field_count > 1 ? 's' : ''}
                  {doc.required_disclosure_count > 0 && (
                    <span className="text-red-600 ml-1">
                      ({doc.required_disclosure_count} required for disclosure)
                    </span>
                  )}
                </div>
                
                <div className="space-y-1">
                  {doc.fields.slice(0, 5).map((field, fieldIdx) => (
                    <div key={fieldIdx} className="flex items-center gap-2 text-xs">
                      <XCircle className="h-3 w-3 text-red-400 flex-shrink-0" />
                      <span className="truncate">{field.field_name}</span>
                      <code className="text-[10px] bg-white/50 px-1 rounded">{field.field_id}</code>
                      {field.required_disclosure && (
                        <span className="text-purple-600 text-[10px]">*</span>
                      )}
                    </div>
                  ))}
                  {doc.fields.length > 5 && (
                    <p className="text-xs text-muted-foreground italic">
                      + {doc.fields.length - 5} more fields
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function FinalReportTab({ runDetail, isLoading, className }: FinalReportTabProps) {
  if (isLoading || !runDetail) {
    return <ReportSkeleton />;
  }

  const flaggedItems = extractFlaggedItems(runDetail);
  const fieldChanges = extractFieldChanges(runDetail);
  const agentType = runDetail.agent_type || "drawdocs";

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header with Export */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Final Report</h2>
          <p className="text-sm text-muted-foreground">
            Summary of agent processing for loan {runDetail.loan_id.slice(0, 8)}...
          </p>
        </div>
        <ExportButton runDetail={runDetail} />
      </div>

      {/* Summary Stats */}
      <SummaryCard
        runDetail={runDetail}
        flaggedItems={flaggedItems}
        fieldChanges={fieldChanges}
      />

      {/* Agent Status */}
      <AgentStatusSummary runDetail={runDetail} agentType={agentType} />

      {/* Agent-Specific Details - 3 column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        <DrawcorePhasesCard runDetail={runDetail} />
        <DiscrepancyDetectionCard runDetail={runDetail} />
        <OrderDocsStepsCard runDetail={runDetail} />
      </div>
      
      {/* Verification Summary - Full Width */}
      <VerificationSummaryCard runDetail={runDetail} />

      {/* Two Column Layout for Flagged Items and Field Changes */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <FlaggedItemsCard items={flaggedItems} agentType={agentType} />
        <FieldChangesCard changes={fieldChanges} agentType={agentType} />
      </div>

      {/* SOP Field Verification - Full Width */}
      <SOPFieldsCard runDetail={runDetail} />

      {/* Documents Needed - Full Width */}
      <DocumentsNeededCard runDetail={runDetail} />

      {/* Summary Text */}
      {runDetail.summary_text && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              Execution Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[300px]">
              <pre className="text-xs font-mono whitespace-pre-wrap bg-slate-900 text-slate-100 p-4 rounded-lg overflow-x-auto">
                {runDetail.summary_text}
              </pre>
            </ScrollArea>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

