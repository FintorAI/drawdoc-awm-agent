"use client";

import * as React from "react";
import { AlertTriangle, CheckCircle2, Clock, AlertCircle, ChevronRight, FileText } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface ExecutiveSummaryProps {
  runDetail: any;
  className?: string;
}

export function ExecutiveSummary({ runDetail, className }: ExecutiveSummaryProps) {
  const verificationOutput = runDetail?.agents?.verification?.output;
  const preparationOutput = runDetail?.agents?.preparation?.output;
  const sendOutput = runDetail?.agents?.send?.output;
  
  const status = runDetail?.status;
  const blockingIssues = runDetail?.blocking_issues || [];
  
  // Determine overall status
  const isBlocked = status === "blocked" || blockingIssues.length > 0;
  const isSuccess = status === "success" && !isBlocked;
  const hasWarnings = status === "warning" || (!isBlocked && !isSuccess);
  
  // Key findings
  const tridCompliance = verificationOutput?.trid_compliance;
  const isPastDue = tridCompliance?.is_past_due === true;
  const tridStatus = isPastDue ? "Past Due" : tridCompliance?.compliant ? "Compliant" : "Non-Compliant";
  
  const formValidation = verificationOutput?.form_validation;
  const formsPassed = formValidation?.forms_passed || 0;
  const formsChecked = formValidation?.forms_checked || 0;
  
  const maventResult = sendOutput?.mavent_result;
  const maventStatus = maventResult?.error 
    ? "Error" 
    : maventResult?.passed 
      ? "Passed" 
      : `${maventResult?.total_issues || 0} Issues`;
  
  const ctcResult = preparationOutput?.ctc_result;
  const ctcMatched = ctcResult?.matched === true;
  const ctcDifference = ctcResult?.difference || 0;
  
  const atrQmResult = sendOutput?.atr_qm_result;
  const atrQmStatus = atrQmResult?.passed === true ? "Passed" : "Issues Found";
  
  // Required actions
  const requiredActions: string[] = [];
  
  if (isPastDue) {
    requiredActions.push("URGENT: Escalate to Supervisor - LE Due Date passed");
  }
  if (verificationOutput?.closing_date_check?.blocking) {
    requiredActions.push("Set closing date (minimum 15 days from application date)");
  }
  if (!ctcMatched && ctcDifference !== 0) {
    requiredActions.push(`Resolve CTC mismatch: $${Math.abs(ctcDifference).toLocaleString()}`);
  }
  if (formValidation?.missing_fields?.length > 0) {
    const missingCount = formValidation.missing_fields.length;
    requiredActions.push(`Populate ${missingCount} missing field${missingCount !== 1 ? 's' : ''}`);
  }
  if (maventResult && !maventResult.passed) {
    if (maventResult.error) {
      requiredActions.push("Resolve Mavent compliance check error");
    } else {
      requiredActions.push(`Address ${maventResult.total_issues || 0} Mavent compliance issue${maventResult.total_issues !== 1 ? 's' : ''}`);
    }
  }
  
  return (
    <Card className={cn("border-2", className)}>
      <CardHeader>
        <CardTitle className="text-xl flex items-center gap-2">
          {isBlocked && <AlertTriangle className="h-6 w-6 text-red-600" />}
          {isSuccess && <CheckCircle2 className="h-6 w-6 text-emerald-600" />}
          {hasWarnings && <AlertCircle className="h-6 w-6 text-amber-600" />}
          Executive Summary
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Overall Status */}
        <div>
          <h3 className="text-sm font-semibold mb-2">Overall Status</h3>
          <div className={cn(
            "p-4 rounded-lg border-2",
            isBlocked && "bg-red-50 border-red-200",
            isSuccess && "bg-emerald-50 border-emerald-200",
            hasWarnings && "bg-amber-50 border-amber-200"
          )}>
            <div className="flex items-center gap-3">
              {isBlocked && <AlertTriangle className="h-8 w-8 text-red-600 shrink-0" />}
              {isSuccess && <CheckCircle2 className="h-8 w-8 text-emerald-600 shrink-0" />}
              {hasWarnings && <AlertCircle className="h-8 w-8 text-amber-600 shrink-0" />}
              <div>
                <p className={cn(
                  "text-lg font-bold",
                  isBlocked && "text-red-900",
                  isSuccess && "text-emerald-900",
                  hasWarnings && "text-amber-900"
                )}>
                  {isBlocked && "BLOCKED - Cannot Proceed"}
                  {isSuccess && "READY - All Checks Passed"}
                  {hasWarnings && "WARNING - Review Required"}
                </p>
                <p className={cn(
                  "text-sm",
                  isBlocked && "text-red-700",
                  isSuccess && "text-emerald-700",
                  hasWarnings && "text-amber-700"
                )}>
                  {isBlocked && "Disclosure cannot be sent until blocking issues are resolved"}
                  {isSuccess && "Disclosure is ready to be ordered and sent"}
                  {hasWarnings && "Some issues detected - review before proceeding"}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Key Findings */}
        <div>
          <h3 className="text-sm font-semibold mb-3">Key Findings</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* TRID */}
            <div className="flex items-start gap-2 p-3 rounded-lg bg-muted/30">
              <Clock className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium">TRID Compliance</p>
                <p className={cn(
                  "text-sm font-semibold",
                  tridStatus === "Compliant" && "text-emerald-700",
                  tridStatus === "Past Due" && "text-red-700",
                  tridStatus === "Non-Compliant" && "text-amber-700"
                )}>
                  {tridStatus}
                </p>
                {tridCompliance && (
                  <p className="text-xs text-muted-foreground">
                    {isPastDue 
                      ? `${Math.abs(tridCompliance.days_remaining || 0)} days overdue`
                      : tridCompliance.days_remaining 
                        ? `${tridCompliance.days_remaining} days remaining`
                        : ""}
                  </p>
                )}
              </div>
            </div>
            
            {/* Forms */}
            <div className="flex items-start gap-2 p-3 rounded-lg bg-muted/30">
              <FileText className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium">Forms Validation</p>
                <p className="text-sm font-semibold text-blue-700">
                  {formsPassed} of {formsChecked} Passed
                </p>
                {formValidation?.missing_fields?.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {formValidation.missing_fields.length} fields missing
                  </p>
                )}
              </div>
            </div>
            
            {/* Mavent */}
            <div className="flex items-start gap-2 p-3 rounded-lg bg-muted/30">
              <CheckCircle2 className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium">Mavent Compliance</p>
                <p className={cn(
                  "text-sm font-semibold",
                  maventStatus === "Passed" && "text-emerald-700",
                  maventStatus === "Error" && "text-red-700",
                  maventStatus.includes("Issues") && "text-amber-700"
                )}>
                  {maventStatus}
                </p>
              </div>
            </div>
            
            {/* CTC */}
            <div className="flex items-start gap-2 p-3 rounded-lg bg-muted/30">
              <CheckCircle2 className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium">Cash to Close</p>
                <p className={cn(
                  "text-sm font-semibold",
                  ctcMatched ? "text-emerald-700" : "text-amber-700"
                )}>
                  {ctcMatched ? "Matched" : "Mismatch"}
                </p>
                {!ctcMatched && ctcDifference !== 0 && (
                  <p className="text-xs text-amber-700">
                    ${Math.abs(ctcDifference).toLocaleString()} difference
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Blocking Issues */}
        {blockingIssues.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold mb-3 text-red-900">Blocking Issues</h3>
            <div className="space-y-2">
              {blockingIssues.map((issue: string, i: number) => (
                <div key={i} className="flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
                  <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 shrink-0" />
                  <p className="text-sm text-red-800">{issue}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Required Actions */}
        {requiredActions.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold mb-3">Required Actions</h3>
            <div className="space-y-2">
              {requiredActions.map((action, i) => (
                <div key={i} className="flex items-start gap-2">
                  <ChevronRight className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                  <p className="text-sm">{action}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Next Steps - Only show if there are clear next steps */}
        {(isBlocked || isSuccess) && (
          <div>
            <h3 className="text-sm font-semibold mb-3">Next Steps</h3>
            <div className={cn(
              "p-4 rounded-lg border",
              isBlocked && "bg-amber-50 border-amber-200",
              isSuccess && "bg-emerald-50 border-emerald-200"
            )}>
              {isBlocked && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-amber-900">Before Disclosure Can Proceed:</p>
                  <ol className="text-sm text-amber-800 space-y-1 ml-4 list-decimal">
                    {requiredActions.slice(0, 3).map((action, i) => (
                      <li key={i}>{action}</li>
                    ))}
                  </ol>
                  {requiredActions.length > 3 && (
                    <p className="text-xs text-amber-700">
                      +{requiredActions.length - 3} more action{requiredActions.length - 3 !== 1 ? 's' : ''} required
                    </p>
                  )}
                </div>
              )}
              {isSuccess && (
                <div className="space-y-1">
                  <p className="text-sm font-medium text-emerald-900">Ready to Proceed:</p>
                  <p className="text-sm text-emerald-800">
                    All compliance checks passed. You can now order the disclosure package.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

