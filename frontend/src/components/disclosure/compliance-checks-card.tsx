"use client";

import * as React from "react";
import { Shield, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface ComplianceChecksCardProps {
  maventData?: {
    passed: boolean;
    total_issues?: number;
    has_fails?: boolean;
    has_alerts?: boolean;
    has_warnings?: boolean;
    fails?: string[];
    alerts?: string[];
    warnings?: string[];
    error?: string;
    blocking?: boolean;
  };
  atrQmData?: {
    passed: boolean;
    loan_features_flag?: string;
    points_fees_flag?: string;
    price_limit_flag?: string;
    red_flags?: string[];
    yellow_flags?: string[];
    blocking?: boolean;
  };
  className?: string;
}

export function ComplianceChecksCard({ maventData, atrQmData, className }: ComplianceChecksCardProps) {
  const maventPassed = maventData?.passed ?? false;
  const maventIssues = maventData?.total_issues ?? 0;
  const atrQmPassed = atrQmData?.passed ?? false;
  const hasRedFlags = (atrQmData?.red_flags?.length ?? 0) > 0;
  
  return (
    <Card className={cn(className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="text-lg">Compliance Checks</CardTitle>
            <CardDescription>Mavent & ATR/QM verification</CardDescription>
          </div>
          <Shield className="h-6 w-6 text-muted-foreground" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Mavent Section */}
        {maventData && (
          <div className="space-y-3 pb-4 border-b">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold">Mavent Compliance</h4>
              {maventData.error ? (
                <Badge variant="destructive" className="text-xs">
                  Error
                </Badge>
              ) : maventPassed ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              ) : (
                <XCircle className="h-5 w-5 text-red-600" />
              )}
            </div>
            
            {maventData.error ? (
              <div className="p-3 rounded-md bg-red-50 border border-red-200">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-red-600 flex-shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-red-900">Compliance Check Failed</p>
                    <p className="text-xs text-red-800">{maventData.error}</p>
                  </div>
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-4 text-sm">
                  <div>
                    <span className="font-medium">{maventIssues}</span>
                    <span className="text-muted-foreground"> total issue{maventIssues !== 1 ? "s" : ""}</span>
                  </div>
                  {maventData.has_fails && (
                    <Badge variant="destructive" className="text-xs">
                      {maventData.fails?.length ?? 0} Fail{(maventData.fails?.length ?? 0) !== 1 ? "s" : ""}
                    </Badge>
                  )}
                  {maventData.has_alerts && (
                    <Badge variant="default" className="text-xs bg-amber-100 text-amber-800 hover:bg-amber-100">
                      {maventData.alerts?.length ?? 0} Alert{(maventData.alerts?.length ?? 0) !== 1 ? "s" : ""}
                    </Badge>
                  )}
                  {maventData.has_warnings && (
                    <Badge variant="secondary" className="text-xs">
                      {maventData.warnings?.length ?? 0} Warning{(maventData.warnings?.length ?? 0) !== 1 ? "s" : ""}
                    </Badge>
                  )}
                </div>
                
                {/* Show fails */}
                {maventData.fails && maventData.fails.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-red-900">Fails:</p>
                    <ul className="space-y-1">
                      {maventData.fails.slice(0, 3).map((fail, idx) => (
                        <li key={idx} className="text-xs text-red-800 flex items-start gap-1.5">
                          <span className="text-red-400 mt-1">•</span>
                          <span>{fail}</span>
                        </li>
                      ))}
                      {maventData.fails.length > 3 && (
                        <li className="text-xs text-red-600">
                          +{maventData.fails.length - 3} more...
                        </li>
                      )}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>
        )}
        
        {/* ATR/QM Section */}
        {atrQmData && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold">ATR/QM Check</h4>
              {atrQmPassed && !hasRedFlags ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              ) : (
                <XCircle className="h-5 w-5 text-red-600" />
              )}
            </div>
            
            {/* Flags */}
            <div className="grid grid-cols-3 gap-2">
              {atrQmData.loan_features_flag && (
                <div className="p-2 rounded border text-center">
                  <p className="text-xs font-medium">Loan Features</p>
                  <p className={cn(
                    "text-xs mt-0.5",
                    atrQmData.loan_features_flag === "GREEN" ? "text-emerald-600" :
                    atrQmData.loan_features_flag === "YELLOW" ? "text-amber-600" :
                    atrQmData.loan_features_flag === "RED" ? "text-red-600" :
                    "text-muted-foreground"
                  )}>
                    {atrQmData.loan_features_flag}
                  </p>
                </div>
              )}
              {atrQmData.points_fees_flag && (
                <div className="p-2 rounded border text-center">
                  <p className="text-xs font-medium">Points & Fees</p>
                  <p className={cn(
                    "text-xs mt-0.5",
                    atrQmData.points_fees_flag === "GREEN" ? "text-emerald-600" :
                    atrQmData.points_fees_flag === "YELLOW" ? "text-amber-600" :
                    atrQmData.points_fees_flag === "RED" ? "text-red-600" :
                    "text-muted-foreground"
                  )}>
                    {atrQmData.points_fees_flag}
                  </p>
                </div>
              )}
              {atrQmData.price_limit_flag && (
                <div className="p-2 rounded border text-center">
                  <p className="text-xs font-medium">Price Limit</p>
                  <p className={cn(
                    "text-xs mt-0.5",
                    atrQmData.price_limit_flag === "GREEN" ? "text-emerald-600" :
                    atrQmData.price_limit_flag === "YELLOW" ? "text-amber-600" :
                    atrQmData.price_limit_flag === "RED" ? "text-red-600" :
                    "text-muted-foreground"
                  )}>
                    {atrQmData.price_limit_flag}
                  </p>
                </div>
              )}
            </div>
            
            {/* Red Flags */}
            {hasRedFlags && (
              <div className="p-3 rounded-md bg-red-50 border border-red-200">
                <p className="text-xs font-medium text-red-900 mb-2">Red Flags:</p>
                <ul className="space-y-1">
                  {atrQmData.red_flags?.map((flag, idx) => (
                    <li key={idx} className="text-xs text-red-800 flex items-start gap-1.5">
                      <span className="text-red-400 mt-1">•</span>
                      <span>{flag}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {/* Yellow Flags */}
            {(atrQmData.yellow_flags?.length ?? 0) > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-amber-900">Yellow Flags:</p>
                <ul className="space-y-1">
                  {atrQmData.yellow_flags?.map((flag, idx) => (
                    <li key={idx} className="text-xs text-amber-800 flex items-start gap-1.5">
                      <span className="text-amber-400 mt-1">•</span>
                      <span>{flag}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

