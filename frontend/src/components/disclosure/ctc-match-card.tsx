"use client";

import * as React from "react";
import { DollarSign, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface CTCMatchCardProps {
  ctcData: {
    matched?: boolean;
    loan_purpose?: string;
    calculated_ctc?: number | null;
    displayed_ctc?: number | null;
    difference?: number | null;
    warnings?: string[];
    blocking?: boolean;
  };
  className?: string;
}

export function CTCMatchCard({ ctcData, className }: CTCMatchCardProps) {
  const isMatched = ctcData.matched ?? false;
  const hasValues = ctcData.calculated_ctc !== null && ctcData.displayed_ctc !== null;
  const calculatedCTC = ctcData.calculated_ctc ?? 0;
  const displayedCTC = ctcData.displayed_ctc ?? 0;
  const difference = ctcData.difference ?? 0;
  
  return (
    <Card className={cn(className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="text-lg">Cash to Close (CTC)</CardTitle>
            <CardDescription>Verification of CTC calculation accuracy</CardDescription>
          </div>
          {hasValues ? (
            isMatched ? (
              <CheckCircle2 className="h-6 w-6 text-emerald-600" />
            ) : (
              <XCircle className="h-6 w-6 text-red-600" />
            )
          ) : (
            <AlertTriangle className="h-6 w-6 text-amber-600" />
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status Badge */}
        <div className="flex items-center gap-2">
          <Badge
            variant={hasValues ? (isMatched ? "default" : "destructive") : "secondary"}
            className={cn(
              "text-sm",
              hasValues && isMatched && "bg-emerald-100 text-emerald-800 hover:bg-emerald-100"
            )}
          >
            {hasValues ? (isMatched ? "CTC Matched" : "Mismatch Detected") : "Values Not Available"}
          </Badge>
          {ctcData.loan_purpose && (
            <span className="text-xs text-muted-foreground">
              ({ctcData.loan_purpose})
            </span>
          )}
        </div>
        
        {hasValues ? (
          <>
            {/* CTC Values */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1 p-3 rounded-md border bg-muted/30">
                <p className="text-xs font-medium text-muted-foreground">Calculated CTC</p>
                <p className="text-lg font-semibold">
                  ${calculatedCTC.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>
              
              <div className="space-y-1 p-3 rounded-md border bg-muted/30">
                <p className="text-xs font-medium text-muted-foreground">Displayed CTC</p>
                <p className="text-lg font-semibold">
                  ${displayedCTC.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>
            </div>
            
            {/* Difference */}
            {!isMatched && difference !== 0 && (
              <div className="p-3 rounded-md bg-red-50 border border-red-200">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-red-900">Difference:</span>
                  <span className="text-sm font-semibold text-red-900">
                    ${Math.abs(difference).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
              </div>
            )}
            
            {/* Match Success */}
            {isMatched && (
              <div className="p-3 rounded-md bg-emerald-50 border border-emerald-200">
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-emerald-900">
                    CTC values match. Calculation is accurate.
                  </p>
                </div>
              </div>
            )}
          </>
        ) : (
          /* No Values Available */
          <div className="p-3 rounded-md bg-amber-50 border border-amber-200">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="text-sm font-medium text-amber-900">CTC Values Not Available</p>
                <p className="text-xs text-amber-800">
                  The LE may need to be calculated/regenerated in Encompass to populate CTC values
                </p>
              </div>
            </div>
          </div>
        )}
        
        {/* Warnings */}
        {ctcData.warnings && ctcData.warnings.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Warnings:</p>
            <ul className="space-y-1">
              {ctcData.warnings.map((warning, idx) => (
                <li key={idx} className="text-xs text-amber-800 flex items-start gap-1.5">
                  <span className="text-amber-400 mt-1">•</span>
                  <span>{warning}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Blocking Warning */}
        {ctcData.blocking && (
          <div className="pt-2 border-t">
            <Badge variant="destructive" className="text-xs">
              Blocking Issue
            </Badge>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

