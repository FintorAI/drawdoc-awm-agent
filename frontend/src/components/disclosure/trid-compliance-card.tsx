"use client";

import * as React from "react";
import { Calendar, AlertTriangle, CheckCircle2, Clock } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface TRIDComplianceCardProps {
  tridData: {
    compliant: boolean;
    application_date?: string;
    le_due_date?: string;
    days_remaining?: number;
    is_past_due?: boolean;
    action?: string;
    blocking?: boolean;
  };
  className?: string;
}

export function TRIDComplianceCard({ tridData, className }: TRIDComplianceCardProps) {
  const isPastDue = tridData.is_past_due || false;
  const isCompliant = tridData.compliant && !isPastDue;
  const daysRemaining = tridData.days_remaining ?? 0;
  
  return (
    <Card className={cn(className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="text-lg">TRID Compliance</CardTitle>
            <CardDescription>Truth in Lending Act & RESPA Integrated Disclosure</CardDescription>
          </div>
          {isCompliant ? (
            <CheckCircle2 className="h-6 w-6 text-emerald-600" />
          ) : (
            <AlertTriangle className="h-6 w-6 text-red-600" />
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status Badge */}
        <div>
          <Badge
            variant={isCompliant ? "default" : "destructive"}
            className={cn(
              "text-sm",
              isCompliant && "bg-emerald-100 text-emerald-800 hover:bg-emerald-100"
            )}
          >
            {isCompliant ? "Compliant" : isPastDue ? "Past Due" : "Non-Compliant"}
          </Badge>
        </div>
        
        {/* Dates */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {tridData.application_date && (
            <div className="flex items-start gap-3">
              <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-sm font-medium">Application Date</p>
                <p className="text-sm text-muted-foreground">{tridData.application_date}</p>
              </div>
            </div>
          )}
          
          {tridData.le_due_date && (
            <div className="flex items-start gap-3">
              <Clock className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-sm font-medium">LE Due Date</p>
                <p className="text-sm text-muted-foreground">{tridData.le_due_date}</p>
              </div>
            </div>
          )}
        </div>
        
        {/* Days Remaining */}
        {!isPastDue && daysRemaining > 0 && (
          <div className={cn(
            "p-3 rounded-md border",
            daysRemaining <= 1 ? "bg-red-50 border-red-200" : 
            daysRemaining <= 2 ? "bg-amber-50 border-amber-200" :
            "bg-blue-50 border-blue-200"
          )}>
            <p className="text-sm font-medium">
              {daysRemaining} business day{daysRemaining !== 1 ? "s" : ""} remaining
            </p>
          </div>
        )}
        
        {/* Past Due Warning */}
        {isPastDue && (
          <div className="p-3 rounded-md bg-red-50 border border-red-200">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="text-sm font-semibold text-red-900">LE Due Date Passed</p>
                <p className="text-sm text-red-800">{tridData.action || "Escalate to Supervisor"}</p>
              </div>
            </div>
          </div>
        )}
        
        {/* Action Message */}
        {tridData.action && !isPastDue && (
          <div className="text-sm text-muted-foreground">
            {tridData.action}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

