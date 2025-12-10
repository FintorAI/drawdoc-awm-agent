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
  agentType?: "drawdocs" | "disclosure" | "loa";
}

interface FlaggedItem {
  id: string;
  agent: "preparation" | "drawcore" | "verification" | "orderdocs" | "send" | "pre_check" | "system" | "orchestrator";
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

  // Safely extract from logs
  try {
    if (runDetail?.logs && Array.isArray(runDetail.logs)) {
      runDetail.logs.forEach(log => {
        if (log?.level === "error" || log?.level === "warning") {
          items.push({
            id: `log-${idCounter++}`,
            agent: (log.agent || "system") as FlaggedItem["agent"],
            severity: log.level as "error" | "warning",
            message: log.message || "Unknown error",
            details: log.details ? JSON.stringify(log.details) : undefined,
          });
        }
      });
    }
  } catch (error) {
    console.error("Error extracting flagged items from logs:", error);
  }

  // Extract from agent outputs - Drawcore issues
  try {
    const drawcoreOutput = runDetail?.agents?.drawcore?.output as {
      phases?: Record<string, { issues?: Array<{ type: string; message: string }> }>;
    };
    if (drawcoreOutput?.phases) {
      Object.entries(drawcoreOutput.phases).forEach(([phaseName, phase]) => {
        phase?.issues?.forEach((issue, idx) => {
          items.push({
            id: `drawcore-${phaseName}-${idx}`,
            agent: "drawcore",
            severity: issue.type === "error" ? "error" : "warning",
            message: issue.message || "Unknown issue",
            details: `Phase: ${phaseName}`,
          });
        });
      });
    }
  } catch (error) {
    console.error("Error extracting drawcore issues:", error);
  }

  // Extract from verification corrections
  try {
    const verificationOutput = runDetail?.agents?.verification?.output as {
      corrections?: Array<{ field_id: string; field_name: string; reason: string }>;
    };
    if (verificationOutput?.corrections && Array.isArray(verificationOutput.corrections)) {
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
  } catch (error) {
    console.error("Error extracting verification corrections:", error);
  }

  // Extract from OrderDocs preflight warnings (loan readiness issues)
  try {
    const orderdocsOutput = runDetail?.agents?.orderdocs?.output as {
      preflight_warnings?: Array<{ flag: string; name: string; message: string }>;
    };
    if (orderdocsOutput?.preflight_warnings && Array.isArray(orderdocsOutput.preflight_warnings)) {
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
  } catch (error) {
    console.error("Error extracting orderdocs warnings:", error);
  }

  // Extract from disclosure blocking issues
  try {
    const blockingIssues = (runDetail as any)?.blocking_issues;
    if (blockingIssues && Array.isArray(blockingIssues)) {
      blockingIssues.forEach((issue, idx) => {
        items.push({
          id: `blocking-${idx}`,
          agent: "verification",
          severity: "error",
          message: String(issue),
        });
      });
    }
  } catch (error) {
    console.error("Error extracting blocking issues:", error);
  }

  return items;
}

function extractFieldChanges(runDetail: RunDetail): FieldChange[] {
  const changes: FieldChange[] = [];

  // Extract from preparation output
  try {
    const prepOutput = runDetail?.agents?.preparation?.output as {
      results?: {
        field_mappings?: Record<string, { value: string; attachment_id?: string }>;
      };
    };
    if (prepOutput?.results?.field_mappings) {
      Object.entries(prepOutput.results.field_mappings).forEach(([fieldId, mapping]) => {
        if (mapping?.value && mapping.value !== "" && mapping.value !== "0") {
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
  } catch (error) {
    console.error("Error extracting field changes from preparation:", error);
  }

  // Extract from corrected_fields_summary
  try {
    if (runDetail?.corrected_fields_summary && Array.isArray(runDetail.corrected_fields_summary)) {
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
  } catch (error) {
    console.error("Error extracting corrected fields summary:", error);
  }

  // Extract from disclosure RegZ-LE updates
  try {
    const regzLeResult = (runDetail?.agents?.preparation?.output as any)?.regz_le_result;
    if (regzLeResult?.updates_made) {
      Object.entries(regzLeResult.updates_made).forEach(([fieldId, value]) => {
        changes.push({
          fieldId,
          fieldName: fieldId,
          oldValue: null,
          newValue: String(value),
          source: "RegZ-LE",
          agent: "preparation",
        });
      });
    }
  } catch (error) {
    console.error("Error extracting RegZ-LE updates:", error);
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
  
  const agentType = runDetail.agent_type || "drawdocs";
  const prepOutput = runDetail.agents.preparation?.output as {
    documents_processed?: number;
    total_documents_found?: number;
  };
  const verificationOutput = runDetail.agents.verification?.output as any;
  const sendOutput = runDetail.agents.send?.output as any;

  // Disclosure-specific stats
  const tridCompliant = verificationOutput?.trid_compliance?.compliant === true;
  const formsChecked = verificationOutput?.form_validation?.forms_checked || 0;
  const formsPassed = verificationOutput?.form_validation?.forms_passed || 0;
  const maventPassed = sendOutput?.mavent_result?.passed === true;

  const stats = agentType === "disclosure"
    ? [
        {
          label: "TRID Compliant",
          value: tridCompliant ? 1 : 0,
          icon: CheckCircle2,
          color: tridCompliant ? "text-emerald-600" : "text-red-600",
        },
        {
          label: "Forms Passed",
          value: formsPassed,
          total: formsChecked,
          icon: FileText,
          color: "text-blue-600",
        },
        {
          label: "Mavent Status",
          value: maventPassed ? 1 : 0,
          icon: CheckCircle2,
          color: maventPassed ? "text-emerald-600" : "text-amber-600",
        },
        {
          label: "Warnings",
          value: warningCount,
          icon: AlertTriangle,
          color: warningCount > 0 ? "text-amber-600" : "text-slate-400",
        },
      ]
    : [
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
    phase_1: "System-Calculated Fields",
    phase_2: "Document-Sourced Fields",
    phase_3: "Title & Third Party",
    phase_4: "Government & Compliance",
    phase_5: "Final Review",
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
// DISCLOSURE DETAILS CARDS
// =============================================================================

interface DisclosureDetailsCardsProps {
  runDetail: RunDetail;
}

function DisclosureDetailsCards({ runDetail }: DisclosureDetailsCardsProps) {
  const verificationOutput = runDetail?.agents?.verification?.output as any;
  const preparationOutput = runDetail?.agents?.preparation?.output as any;
  const sendOutput = runDetail?.agents?.send?.output as any;

  const tridCompliance = verificationOutput?.trid_compliance || {};
  const formValidation = verificationOutput?.form_validation || {};
  const miResult = preparationOutput?.mi_result || {};
  const ctcResult = preparationOutput?.ctc_result || {};
  const regzLeResult = preparationOutput?.regz_le_result || {};
  const maventResult = sendOutput?.mavent_result || {};
  const atrQmResult = sendOutput?.atr_qm_result || {};
  const orderResult = sendOutput?.order_result || {};
  
  // Handle missing data gracefully
  if (!verificationOutput && !preparationOutput && !sendOutput) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          <p>No disclosure data available yet.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* TRID Compliance Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-blue-500" />
            TRID Compliance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className={cn(
              "p-3 rounded-lg border",
              tridCompliance.compliant ? "bg-emerald-50 border-emerald-200" : "bg-red-50 border-red-200"
            )}>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Status</span>
                <span className={cn(
                  "text-sm font-semibold",
                  tridCompliance.compliant ? "text-emerald-600" : "text-red-600"
                )}>
                  {tridCompliance.compliant ? "✓ Compliant" : "✗ Non-Compliant"}
                </span>
              </div>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Application Date:</span>
                <span className="font-mono">{tridCompliance.application_date || "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">LE Due Date:</span>
                <span className="font-mono">{tridCompliance.le_due_date || "—"}</span>
              </div>
              {tridCompliance.days_remaining !== undefined && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Days Remaining:</span>
                  <span className={cn(
                    "font-semibold",
                    tridCompliance.days_remaining > 0 ? "text-emerald-600" : "text-red-600"
                  )}>
                    {tridCompliance.days_remaining}
                  </span>
                </div>
              )}
              {tridCompliance.action && (
                <p className="text-xs text-muted-foreground pt-2 border-t">
                  {tridCompliance.action}
                </p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Form Validation Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <FileText className="h-4 w-4 text-blue-500" />
            Form Validation
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <div className="text-center p-2 bg-muted/50 rounded">
                <p className="text-lg font-bold">{formValidation.forms_checked || 0}</p>
                <p className="text-xs text-muted-foreground">Checked</p>
              </div>
              <div className="text-center p-2 bg-emerald-50 rounded">
                <p className="text-lg font-bold text-emerald-600">{formValidation.forms_passed || 0}</p>
                <p className="text-xs text-muted-foreground">Passed</p>
              </div>
              <div className="text-center p-2 bg-amber-50 rounded">
                <p className="text-lg font-bold text-amber-600">
                  {(formValidation.forms_checked || 0) - (formValidation.forms_passed || 0)}
                </p>
                <p className="text-xs text-muted-foreground">Issues</p>
              </div>
            </div>
            {formValidation.missing_fields && formValidation.missing_fields.length > 0 && (
              <div className="pt-2 border-t">
                <p className="text-xs font-medium text-muted-foreground mb-1">
                  Missing Fields ({formValidation.missing_fields.length}):
                </p>
                <div className="space-y-1">
                  {formValidation.missing_fields.slice(0, 3).map((field: string, i: number) => (
                    <p key={i} className="text-xs font-mono text-amber-700 bg-amber-50 px-2 py-1 rounded">
                      {field}
                    </p>
                  ))}
                  {formValidation.missing_fields.length > 3 && (
                    <p className="text-xs text-muted-foreground">
                      +{formValidation.missing_fields.length - 3} more
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* MI Calculation Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Package className="h-4 w-4 text-amber-500" />
            MI Calculation
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className={cn(
              "p-3 rounded-lg border text-center",
              miResult.requires_mi ? "bg-amber-50 border-amber-200" : "bg-slate-50 border-slate-200"
            )}>
              <p className="text-sm text-muted-foreground">MI Required</p>
              <p className={cn(
                "text-2xl font-bold",
                miResult.requires_mi ? "text-amber-600" : "text-slate-500"
              )}>
                {miResult.requires_mi ? "Yes" : "No"}
              </p>
            </div>
            {miResult.requires_mi && (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">LTV Ratio:</span>
                  <span className="font-mono">{miResult.ltv_ratio?.toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Monthly MI:</span>
                  <span className="font-mono">${miResult.monthly_amount?.toFixed(2) || "0.00"}</span>
                </div>
                {miResult.upfront_amount > 0 && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Upfront MI:</span>
                    <span className="font-mono">${miResult.upfront_amount?.toFixed(2)}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Mavent Compliance Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-500" />
            Mavent Compliance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className={cn(
              "p-3 rounded-lg border",
              maventResult.passed ? "bg-emerald-50 border-emerald-200" : "bg-amber-50 border-amber-200"
            )}>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Status</span>
                <span className={cn(
                  "text-sm font-semibold",
                  maventResult.passed ? "text-emerald-600" : "text-amber-600"
                )}>
                  {maventResult.passed ? "✓ Passed" : "⚠ Issues Found"}
                </span>
              </div>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total Issues:</span>
                <span className="font-semibold">{maventResult.total_issues || 0}</span>
              </div>
              {maventResult.audit_id && (
                <div className="pt-2 border-t">
                  <p className="text-xs text-muted-foreground">Audit ID:</p>
                  <p className="text-xs font-mono text-muted-foreground break-all">
                    {maventResult.audit_id}
                  </p>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* RegZ-LE Updates Card */}
      {regzLeResult.updates_made && Object.keys(regzLeResult.updates_made).length > 0 && (
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Pencil className="h-4 w-4 text-emerald-500" />
              RegZ-LE Updates
              <span className="ml-auto text-xs font-normal text-muted-foreground">
                {Object.keys(regzLeResult.updates_made).length} fields
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[200px]">
              <div className="space-y-1 pr-3">
                {Object.entries(regzLeResult.updates_made).map(([fieldId, value]: [string, any], idx: number) => (
                  <div key={idx} className="flex items-center justify-between gap-2 text-xs p-2 rounded bg-muted/50">
                    <span className="font-mono text-muted-foreground">{fieldId}</span>
                    <ArrowRight className="h-3 w-3 flex-shrink-0" />
                    <span className="font-medium text-emerald-700 truncate">{String(value)}</span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}
    </div>
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
      status: boolean;
      message: string;
    }>;
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

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Package className="h-4 w-4 text-purple-500" />
          Order Documents Pipeline
          {orderdocsOutput.dry_run && (
            <Badge variant="outline" className="ml-2 text-xs">Dry Run</Badge>
          )}
          {preflightWarnings.length > 0 && (
            <Badge variant="outline" className="ml-2 text-xs bg-amber-100 border-amber-300 text-amber-700">
              {preflightWarnings.length} Warning{preflightWarnings.length > 1 ? 's' : ''}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {/* Pre-flight Warnings */}
          {preflightWarnings.length > 0 && (
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
                  <div key={idx} className="flex items-center gap-2 text-xs">
                    <XCircle className="h-3.5 w-3.5 text-red-500 flex-shrink-0" />
                    <span className="text-amber-900 font-medium">{warning.name}:</span>
                    <span className="text-amber-700">Not Complete</span>
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
// MAIN COMPONENT
// =============================================================================

export function FinalReportTab({ runDetail, isLoading, className, agentType: agentTypeProp }: FinalReportTabProps) {
  if (isLoading || !runDetail) {
    return <ReportSkeleton />;
  }

  const flaggedItems = extractFlaggedItems(runDetail);
  const fieldChanges = extractFieldChanges(runDetail);
  const agentType = agentTypeProp || runDetail.agent_type || "drawdocs";

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
      {agentType === "drawdocs" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <DrawcorePhasesCard runDetail={runDetail} />
          <VerificationSummaryCard runDetail={runDetail} />
          <OrderDocsStepsCard runDetail={runDetail} />
        </div>
      )}
      
      {/* Disclosure-Specific Details */}
      {agentType === "disclosure" && (
        <DisclosureDetailsCards runDetail={runDetail} />
      )}

      {/* Two Column Layout for Flagged Items and Field Changes */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <FlaggedItemsCard items={flaggedItems} agentType={agentType} />
        <FieldChangesCard changes={fieldChanges} agentType={agentType} />
      </div>

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

