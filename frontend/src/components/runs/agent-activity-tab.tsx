"use client";

import * as React from "react";
import { 
  Brain, 
  Wrench, 
  CheckCircle2, 
  XCircle, 
  Target, 
  MessageSquare,
  ChevronDown,
  ChevronRight,
  FileText,
  AlertTriangle
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

interface AgentActivityTabProps {
  runDetail: any;
  isLoading?: boolean;
  className?: string;
  agentType?: string;
}

interface ParsedMessage {
  type: "task" | "reasoning" | "tool_call" | "tool_result" | "report";
  content: string;
  toolName?: string;
  toolStatus?: "success" | "error" | "unknown";
  metadata?: any;
}

function parseAgentMessages(messages: any[]): ParsedMessage[] {
  const parsed: ParsedMessage[] = [];
  
  if (!messages || !Array.isArray(messages)) {
    return parsed;
  }
  
  for (const message of messages) {
    try {
      // Handle string representations from backend
      if (typeof message === 'string') {
        // Parse string representations like "content='...' additional_kwargs={} ..."
        
        // Check if it's a task message (HumanMessage)
        if (message.includes('CRITICAL WORKFLOW') || message.includes('=== STEP')) {
          // Extract content from string - handle both single and double quotes
          let contentMatch = message.match(/content='([\s\S]*?)'\s+additional_kwargs/);
          if (!contentMatch) {
            contentMatch = message.match(/content="([\s\S]*?)"\s+additional_kwargs/);
          }
          if (contentMatch) {
            const content = contentMatch[1]
              .replace(/\\n/g, '\n')
              .replace(/\\'/g, "'")
              .replace(/\\"/g, '"')
              .replace(/\\\\/g, '\\');
            
            parsed.push({
              type: "task",
              content: content
            });
          }
          continue;
        }
        
        // Check if it's an AI message with tool calls
        if (message.includes('tool_calls=[')) {
          // Extract tool calls
          const toolCallsMatch = message.match(/tool_calls=\[(.*?)\]/);
          if (toolCallsMatch) {
            // Try to extract tool names - handle various formats
            const nameMatches = [
              ...message.matchAll(/'name':\s*'([^']+)'/g),
              ...message.matchAll(/"name":\s*"([^"]+)"/g),
              ...message.matchAll(/'name':\s*"([^"]+)"/g)
            ];
            nameMatches.forEach(match => {
              parsed.push({
                type: "tool_call",
                content: `Calling ${match[1]}`,
                toolName: match[1],
                metadata: {}
              });
            });
          }
          
          // Also extract reasoning text if present
          let textMatch = message.match(/\{'text':\s*"([^"]+)"/);
          if (!textMatch) {
            textMatch = message.match(/\{"text":\s*"([^"]+)"/);
          }
          if (textMatch) {
            parsed.push({
              type: "reasoning",
              content: textMatch[1]
            });
          }
          continue;
        }
        
        // Check if it's a tool result - handle both single and double quotes
        let nameMatch = message.match(/name='([^']+)'/);
        if (!nameMatch) {
          nameMatch = message.match(/name="([^"]+)"/);
        }
        
        let contentMatch = message.match(/content='(\{[\s\S]*?\})'/);
        if (!contentMatch) {
          contentMatch = message.match(/content="(\{[\s\S]*?\})"/);
        }
        if (!contentMatch) {
          // Try without curly braces for non-JSON content
          contentMatch = message.match(/content='([^']*?)'\s+name=/);
          if (!contentMatch) {
            contentMatch = message.match(/content="([^"]*?)"\s+name=/);
          }
        }
        
        if (nameMatch && contentMatch) {
          const toolName = nameMatch[1];
          let toolData: any = {};
          let toolStatus: "success" | "error" | "unknown" = "unknown";
          
          try {
            // Clean up the JSON string
            const jsonStr = contentMatch[1]
              .replace(/\\"/g, '"')
              .replace(/\\'/g, "'")
              .replace(/\\\\/g, '\\');
            toolData = JSON.parse(jsonStr);
            
            // Determine status
            if (toolData.success === true || toolData.passed === true) {
              toolStatus = "success";
            } else if (toolData.success === false || toolData.error || toolData.blocking === true) {
              toolStatus = "error";
            }
          } catch (e) {
            // Not valid JSON, use as string
            toolData = { raw: contentMatch[1] };
          }
          
          parsed.push({
            type: "tool_result",
            content: JSON.stringify(toolData, null, 2),
            toolName,
            toolStatus,
            metadata: toolData
          });
          continue;
        }
        
        continue;
      }
      
      // Handle proper JSON objects
      const messageType = message.type || 'unknown';
      const content = message.content || '';
      
      // Task message (HumanMessage)
      if (messageType === 'human' || (typeof content === 'string' && content.includes('CRITICAL WORKFLOW'))) {
        parsed.push({
          type: "task",
          content: typeof content === 'string' ? content : String(content)
        });
      }
      // AI reasoning/response
      else if (messageType === 'ai' || messageType === 'AIMessage') {
        // Check if it's a tool call
        const toolCalls = message.tool_calls || [];
        if (toolCalls.length > 0) {
          toolCalls.forEach((tc: any) => {
            parsed.push({
              type: "tool_call",
              content: `Calling ${tc.name}`,
              toolName: tc.name,
              metadata: tc.args
            });
          });
        } else if (content) {
          // Check if it's a markdown report
          const contentStr = typeof content === 'string' ? content : String(content);
          if (contentStr.startsWith('#') || contentStr.startsWith('---') || contentStr.includes('## ')) {
            parsed.push({
              type: "report",
              content: contentStr
            });
          } else {
            parsed.push({
              type: "reasoning",
              content: contentStr
            });
          }
        }
      }
      // Tool result
      else if (messageType === 'tool' || message.name) {
        const toolName = message.name || 'unknown';
        let toolData: any = {};
        let toolStatus: "success" | "error" | "unknown" = "unknown";
        
        try {
          toolData = typeof content === 'string' ? JSON.parse(content) : content;
          
          // Determine status
          if (toolData.success === true || toolData.passed === true) {
            toolStatus = "success";
          } else if (toolData.success === false || toolData.error || toolData.blocking === true) {
            toolStatus = "error";
          }
        } catch (e) {
          // Not JSON, use as string
        }
        
        parsed.push({
          type: "tool_result",
          content: typeof content === 'string' ? content : JSON.stringify(content, null, 2),
          toolName,
          toolStatus,
          metadata: toolData
        });
      }
    } catch (e) {
      console.error('Error parsing message:', e, message);
    }
  }
  
  return parsed;
}

function AgentSection({ agentName, messages, status }: { agentName: string; messages: any[]; status: string }) {
  const [isExpanded, setIsExpanded] = React.useState(true);
  const parsedMessages = parseAgentMessages(messages);
  
  // Debug logging
  React.useEffect(() => {
    console.log(`[AgentActivity] ${agentName}:`, {
      totalMessages: messages.length,
      parsedCount: parsedMessages.length,
      sampleMessage: messages[0]
    });
  }, [agentName, messages, parsedMessages]);
  
  const agentDisplayName = agentName.charAt(0).toUpperCase() + agentName.slice(1);
  const hasContent = parsedMessages.length > 0;
  
  const statusIcon = status === "success" ? (
    <CheckCircle2 className="h-5 w-5 text-emerald-600" />
  ) : status === "failed" ? (
    <XCircle className="h-5 w-5 text-red-600" />
  ) : (
    <AlertTriangle className="h-5 w-5 text-amber-600" />
  );
  
  // If no content, show simple header without toggle
  if (!hasContent) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-3">
            <Brain className="h-5 w-5 text-blue-600 shrink-0" />
            <div className="flex-1 min-w-0">
              <CardTitle className="text-base">{agentDisplayName} Agent</CardTitle>
              <p className="text-xs text-muted-foreground mt-0.5">
                No activities recorded
              </p>
            </div>
            {statusIcon}
          </div>
        </CardHeader>
      </Card>
    );
  }
  
  return (
    <Card>
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CardHeader className="pb-3">
          <CollapsibleTrigger asChild>
            <button className="flex items-center gap-3 w-full text-left hover:opacity-80 transition-opacity">
              {isExpanded ? (
                <ChevronDown className="h-5 w-5 text-muted-foreground shrink-0" />
              ) : (
                <ChevronRight className="h-5 w-5 text-muted-foreground shrink-0" />
              )}
              <Brain className="h-5 w-5 text-blue-600 shrink-0" />
              <div className="flex-1 min-w-0">
                <CardTitle className="text-base">{agentDisplayName} Agent</CardTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {parsedMessages.length} activities recorded
                </p>
              </div>
              {statusIcon}
            </button>
          </CollapsibleTrigger>
        </CardHeader>
        
        <CollapsibleContent>
          <CardContent className="space-y-3 pt-0">
            {parsedMessages.map((msg, i) => (
              <MessageItem key={i} message={msg} />
            ))}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}

function MessageItem({ message }: { message: ParsedMessage }) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  
  // Task message
  if (message.type === "task") {
    // Extract first meaningful line or section
    const lines = message.content.split('\n');
    const firstLine = lines[0] || '';
    const hasMore = message.content.length > 150;
    
    // Get a better preview - first 2-3 lines or first section
    let preview = lines.slice(0, 3).join('\n');
    if (preview.length > 150) {
      preview = preview.substring(0, 150);
    }
    
    return (
      <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
        <div className="flex items-start gap-2">
          <Target className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-blue-900 mb-1">Task Assigned</p>
            {isExpanded ? (
              <div className="text-xs text-blue-800 whitespace-pre-wrap font-mono bg-blue-100/50 p-2 rounded border border-blue-200 max-h-96 overflow-y-auto">
                {message.content}
              </div>
            ) : (
              <div className="text-xs text-blue-800">
                <p className="font-medium">{firstLine}</p>
                {hasMore && (
                  <p className="text-blue-700 mt-1 italic">
                    Click "Show more" to see full workflow steps
                  </p>
                )}
              </div>
            )}
            {hasMore && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-xs text-blue-600 hover:text-blue-700 mt-2 font-medium flex items-center gap-1"
              >
                {isExpanded ? (
                  <>
                    <ChevronDown className="h-3 w-3" />
                    Show less
                  </>
                ) : (
                  <>
                    <ChevronRight className="h-3 w-3" />
                    Show more
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }
  
  // Reasoning message
  if (message.type === "reasoning") {
    const hasMore = message.content.length > 200;
    const preview = message.content.substring(0, 200);
    
    return (
      <div className="p-3 rounded-lg bg-purple-50 border border-purple-200">
        <div className="flex items-start gap-2">
          <MessageSquare className="h-4 w-4 text-purple-600 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-purple-900 mb-1">Agent Reasoning</p>
            {isExpanded ? (
              <div className="text-xs text-purple-800 whitespace-pre-wrap bg-purple-100/50 p-2 rounded border border-purple-200">
                {message.content}
              </div>
            ) : (
              <p className="text-xs text-purple-800">
                {preview}{hasMore && '...'}
              </p>
            )}
            {hasMore && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-xs text-purple-600 hover:text-purple-700 mt-2 font-medium flex items-center gap-1"
              >
                {isExpanded ? (
                  <>
                    <ChevronDown className="h-3 w-3" />
                    Show less
                  </>
                ) : (
                  <>
                    <ChevronRight className="h-3 w-3" />
                    Show more
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }
  
  // Tool call message
  if (message.type === "tool_call") {
    return (
      <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
        <div className="flex items-start gap-2">
          <Wrench className="h-4 w-4 text-slate-600 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-slate-900">Tool Call</p>
            <p className="text-xs text-slate-700 font-mono">
              {message.toolName}
            </p>
          </div>
        </div>
      </div>
    );
  }
  
  // Tool result message
  if (message.type === "tool_result") {
    const isSuccess = message.toolStatus === "success";
    const isError = message.toolStatus === "error";
    const [showDetails, setShowDetails] = React.useState(false);
    
    // Get a friendly summary if possible
    let summary = "";
    let detailLines: string[] = [];
    
    if (message.metadata) {
      const meta = message.metadata;
      
      // TRID
      if (message.toolName === "check_trid_dates") {
        summary = meta.compliant ? "✓ Compliant" : meta.action || "Non-compliant";
        if (!meta.compliant) {
          detailLines.push(`Action: ${meta.action || 'N/A'}`);
          if (meta.days_remaining !== undefined) {
            detailLines.push(`Days remaining: ${meta.days_remaining}`);
          }
        }
      }
      // Hard stops
      else if (message.toolName === "check_hard_stops") {
        summary = meta.has_hard_stops ? "✗ Missing fields" : "✓ All present";
      }
      // RegZ-LE
      else if (message.toolName === "update_regz_le_fields") {
        const updateCount = Object.keys(meta.updates_made || {}).length;
        summary = `✓ Updated ${updateCount} fields`;
        if (meta.updates_made && Object.keys(meta.updates_made).length > 0) {
          detailLines.push('Updated fields:');
          Object.entries(meta.updates_made).forEach(([field, value]) => {
            detailLines.push(`  ${field}: ${value}`);
          });
        }
      }
      // CTC
      else if (message.toolName === "match_ctc") {
        summary = meta.matched ? "✓ Matched" : `⚠ Mismatch: $${Math.abs(meta.difference || 0).toLocaleString()}`;
        if (!meta.matched) {
          detailLines.push(`Difference: $${meta.difference || 0}`);
        }
      }
      // Mavent
      else if (message.toolName === "check_mavent") {
        summary = meta.passed ? "✓ Passed" : `✗ ${meta.total_issues || 0} issues`;
      }
      // MI Required Check
      else if (message.toolName === "check_mi_required") {
        summary = meta.mi_required ? "MI Required" : "MI Not Required";
        if (meta.ltv) {
          detailLines.push(`LTV: ${meta.ltv}%`);
        }
      }
      // Generic success/error
      else if (meta.success !== undefined) {
        summary = meta.success ? "✓ Success" : "✗ Failed";
      }
    }
    
    return (
      <div className={cn(
        "p-3 rounded-lg border",
        isSuccess && "bg-emerald-50 border-emerald-200",
        isError && "bg-red-50 border-red-200",
        !isSuccess && !isError && "bg-slate-50 border-slate-200"
      )}>
        <div className="flex items-start gap-2">
          {isSuccess && <CheckCircle2 className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" />}
          {isError && <XCircle className="h-4 w-4 text-red-600 mt-0.5 shrink-0" />}
          {!isSuccess && !isError && <CheckCircle2 className="h-4 w-4 text-slate-400 mt-0.5 shrink-0" />}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className={cn(
                "text-xs font-semibold font-mono",
                isSuccess && "text-emerald-900",
                isError && "text-red-900",
                !isSuccess && !isError && "text-slate-900"
              )}>
                {message.toolName}
              </p>
              <Badge variant="outline" className="text-xs">
                Result
              </Badge>
            </div>
            
            {summary && (
              <p className={cn(
                "text-xs mt-1.5 font-medium",
                isSuccess && "text-emerald-800",
                isError && "text-red-800",
                !isSuccess && !isError && "text-slate-700"
              )}>
                {summary}
              </p>
            )}
            
            {detailLines.length > 0 && (
              <div className="mt-2">
                <div className={cn(
                  "text-xs p-2 rounded bg-white/50 border font-mono",
                  isSuccess && "border-emerald-200",
                  isError && "border-red-200",
                  !isSuccess && !isError && "border-slate-200"
                )}>
                  {detailLines.map((line, i) => (
                    <div key={i} className="whitespace-pre">{line}</div>
                  ))}
                </div>
              </div>
            )}
            
            {message.metadata && Object.keys(message.metadata).length > 0 && (
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="text-xs text-muted-foreground hover:text-foreground mt-2 flex items-center gap-1"
              >
                {showDetails ? (
                  <>
                    <ChevronDown className="h-3 w-3" />
                    Hide raw data
                  </>
                ) : (
                  <>
                    <ChevronRight className="h-3 w-3" />
                    Show raw data
                  </>
                )}
              </button>
            )}
            
            {showDetails && message.metadata && (
              <pre className="mt-2 text-xs bg-white p-2 rounded border overflow-x-auto max-h-60">
                {JSON.stringify(message.metadata, null, 2)}
              </pre>
            )}
          </div>
        </div>
      </div>
    );
  }
  
  // Report message
  if (message.type === "report") {
    // Extract key sections from markdown report
    const lines = message.content.split('\n');
    const headers = lines.filter(line => line.trim().startsWith('#'));
    const mainHeader = headers[0]?.replace(/^#+\s*/, '') || "Agent Report";
    
    return (
      <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
        <Collapsible>
          <CollapsibleTrigger asChild>
            <button className="flex items-start gap-2 w-full text-left hover:opacity-80">
              <FileText className="h-4 w-4 text-slate-600 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-slate-900">Final Report Generated</p>
                <p className="text-xs text-slate-700">{mainHeader}</p>
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 pl-6">
            <div className="prose prose-sm max-w-none">
              <pre className="text-xs bg-white p-3 rounded border max-h-96 overflow-auto whitespace-pre-wrap">
                {message.content}
              </pre>
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>
    );
  }
  
  return null;
}

export function AgentActivityTab({ runDetail, isLoading, className, agentType = "disclosure" }: AgentActivityTabProps) {
  if (isLoading || !runDetail) {
    return (
      <div className={cn("space-y-4", className)}>
        <Card>
          <CardHeader>
            <div className="h-6 w-48 bg-muted animate-pulse rounded" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="h-4 bg-muted animate-pulse rounded" />
              <div className="h-4 bg-muted animate-pulse rounded w-3/4" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  const agents = runDetail.agents || {};
  const agentOrder = agentType === "disclosure" 
    ? ["verification", "preparation", "send"]
    : ["scan", "preparation", "orderdocs"];
  
  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 border-blue-200">
        <CardHeader className="pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-100">
              <Brain className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <CardTitle className="text-lg">Agent Activity</CardTitle>
              <p className="text-sm text-muted-foreground">
                See how AI agents analyzed and processed this loan
              </p>
            </div>
          </div>
        </CardHeader>
      </Card>
      
      {/* Agent Sections */}
      {agentOrder.map((agentKey) => {
        const agent = agents[agentKey];
        if (!agent) return null;
        
        const agentMessages = agent.output?.agent_messages || [];
        if (agentMessages.length === 0) return null;
        
        return (
          <AgentSection
            key={agentKey}
            agentName={agentKey}
            messages={agentMessages}
            status={agent.status}
          />
        );
      })}
      
      {/* Empty state */}
      {agentOrder.every(key => !agents[key]?.output?.agent_messages?.length) && (
        <Card>
          <CardContent className="py-12 text-center">
            <Brain className="h-12 w-12 text-muted-foreground mx-auto mb-3 opacity-50" />
            <p className="text-sm text-muted-foreground">
              No agent activity recorded for this run
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

