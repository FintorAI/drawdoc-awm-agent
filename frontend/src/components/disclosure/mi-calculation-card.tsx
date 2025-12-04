"use client";

import * as React from "react";
import { DollarSign, Percent, TrendingDown, Info } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface MICalculationCardProps {
  miData: {
    requires_mi: boolean;
    loan_type?: string;
    ltv?: number;
    monthly_amount?: number;
    annual_rate?: number;
    cancel_at_ltv?: number;
    first_renewal_months?: number;
    source?: string;
  };
  className?: string;
}

export function MICalculationCard({ miData, className }: MICalculationCardProps) {
  const requiresMI = miData.requires_mi;
  const monthlyAmount = miData.monthly_amount ?? 0;
  const ltv = miData.ltv ?? 0;
  const annualRate = (miData.annual_rate ?? 0) * 100; // Convert to percentage
  const cancelAtLTV = miData.cancel_at_ltv ?? 78;
  
  return (
    <Card className={cn(className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="text-lg">Mortgage Insurance (MI)</CardTitle>
            <CardDescription>Conventional MI calculation for LTV &gt; 80%</CardDescription>
          </div>
          <DollarSign className="h-6 w-6 text-muted-foreground" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* MI Status */}
        <div className="flex items-center gap-2">
          <Badge
            variant={requiresMI ? "default" : "secondary"}
            className={cn(
              "text-sm",
              requiresMI ? "bg-blue-100 text-blue-800 hover:bg-blue-100" : ""
            )}
          >
            {requiresMI ? "MI Required" : "No MI Required"}
          </Badge>
          {!requiresMI && ltv > 0 && (
            <span className="text-sm text-muted-foreground">
              (LTV: {ltv.toFixed(2)}% ≤ 80%)
            </span>
          )}
        </div>
        
        {requiresMI && (
          <>
            {/* Monthly Payment */}
            <div className="space-y-3">
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold">${monthlyAmount.toFixed(2)}</span>
                <span className="text-sm text-muted-foreground">/month</span>
              </div>
              
              {/* LTV Information */}
              <div className="grid grid-cols-2 gap-4 p-3 rounded-md bg-muted/50">
                <div className="space-y-1">
                  <div className="flex items-center gap-1.5">
                    <Percent className="h-4 w-4 text-muted-foreground" />
                    <p className="text-xs font-medium text-muted-foreground">Current LTV</p>
                  </div>
                  <p className="text-sm font-semibold">{ltv.toFixed(2)}%</p>
                </div>
                
                <div className="space-y-1">
                  <div className="flex items-center gap-1.5">
                    <Percent className="h-4 w-4 text-muted-foreground" />
                    <p className="text-xs font-medium text-muted-foreground">Annual Rate</p>
                  </div>
                  <p className="text-sm font-semibold">{annualRate.toFixed(2)}%</p>
                </div>
              </div>
            </div>
            
            {/* Cancellation Info */}
            {cancelAtLTV && (
              <div className="flex items-start gap-3 p-3 rounded-md border bg-emerald-50 border-emerald-200">
                <TrendingDown className="h-5 w-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="text-sm font-medium text-emerald-900">
                    MI Cancellation at {cancelAtLTV}% LTV
                  </p>
                  <p className="text-xs text-emerald-800">
                    Borrower can request MI removal when LTV reaches {cancelAtLTV}%
                  </p>
                </div>
              </div>
            )}
            
            {/* Renewal Info */}
            {miData.first_renewal_months && (
              <div className="flex items-start gap-2 text-xs text-muted-foreground">
                <Info className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <p>
                  First renewal at {miData.first_renewal_months} months ({(miData.first_renewal_months / 12).toFixed(1)} years)
                </p>
              </div>
            )}
          </>
        )}
        
        {/* Source */}
        {miData.source && (
          <div className="pt-2 border-t text-xs text-muted-foreground">
            Source: {miData.source === "calculated" ? "Calculated" : "Pre-existing"}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

