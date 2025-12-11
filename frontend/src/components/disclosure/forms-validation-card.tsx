"use client";

import * as React from "react";
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, AlertTriangle, FileText } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

interface FormResult {
  form_name: string;
  all_valid: boolean;
  field_count: number;
  valid_count: number;
  missing_fields: string[];
  warnings: string[];
  valid_fields?: string[]; // We'll derive this
}

interface FormsValidationCardProps {
  formResults: Record<string, FormResult>;
  fieldDetails?: Record<string, { name: string; has_value: boolean; value: any }>;
  className?: string;
}

export function FormsValidationCard({ formResults, fieldDetails, className }: FormsValidationCardProps) {
  const [expandedForms, setExpandedForms] = React.useState<Set<string>>(new Set());

  const toggleForm = (formName: string) => {
    setExpandedForms(prev => {
      const next = new Set(prev);
      if (next.has(formName)) {
        next.delete(formName);
      } else {
        next.add(formName);
      }
      return next;
    });
  };

  const forms = Object.values(formResults);
  const totalForms = forms.length;
  const passedForms = forms.filter(f => f.all_valid).length;

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="text-lg">Form Validation Details</CardTitle>
            <CardDescription>
              {passedForms} of {totalForms} forms validated successfully
            </CardDescription>
          </div>
          <FileText className="h-6 w-6 text-muted-foreground" />
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {forms.map((form) => {
          const isExpanded = expandedForms.has(form.form_name);
          const isValid = form.all_valid;
          const hasWarnings = form.warnings.length > 0;
          
          // Derive valid fields from field_count - missing_fields
          const validFieldsCount = form.valid_count;
          const missingCount = form.missing_fields.length;

          return (
            <Collapsible
              key={form.form_name}
              open={isExpanded}
              onOpenChange={() => toggleForm(form.form_name)}
            >
              <CollapsibleTrigger asChild>
                <button
                  className={cn(
                    "w-full p-3 rounded-lg border transition-all text-left",
                    "hover:shadow-sm focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                    isValid && !hasWarnings && "bg-emerald-50/50 border-emerald-200",
                    !isValid && !hasWarnings && "bg-amber-50/50 border-amber-200",
                    hasWarnings && "bg-amber-50/50 border-amber-200"
                  )}
                >
                  <div className="flex items-center gap-3">
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                    )}
                    
                    {isValid ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
                    ) : (
                      <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0" />
                    )}
                    
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm">
                        {form.form_name.replace(/_/g, " ")}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {validFieldsCount} of {form.field_count} fields valid
                        {missingCount > 0 && ` • ${missingCount} missing`}
                      </p>
                    </div>
                    
                    <Badge
                      variant={isValid ? "default" : "secondary"}
                      className={cn(
                        "text-xs shrink-0",
                        isValid && "bg-emerald-100 text-emerald-800 hover:bg-emerald-100",
                        !isValid && "bg-amber-100 text-amber-800 hover:bg-amber-100"
                      )}
                    >
                      {isValid ? "✓" : missingCount}
                    </Badge>
                  </div>
                </button>
              </CollapsibleTrigger>
              
              <CollapsibleContent className="pt-2 pl-10 pr-3">
                <div className="space-y-3 pb-2">
                  {/* Valid Fields */}
                  {validFieldsCount > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-xs font-medium text-emerald-700 flex items-center gap-1.5">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Valid Fields ({validFieldsCount})
                      </p>
                      <div className="space-y-1 pl-5">
                        {/* Note: We'd need to derive valid fields from field_details or enhance backend */}
                        <p className="text-xs text-muted-foreground">
                          {validFieldsCount} field{validFieldsCount !== 1 ? "s" : ""} populated correctly
                        </p>
                      </div>
                    </div>
                  )}
                  
                  {/* Missing Fields */}
                  {missingCount > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-xs font-medium text-amber-700 flex items-center gap-1.5">
                        <XCircle className="h-3.5 w-3.5" />
                        Missing Fields ({missingCount})
                      </p>
                      <div className="space-y-1 pl-5">
                        {form.missing_fields.map((field, i) => (
                          <p key={i} className="text-xs text-amber-800 font-mono">
                            • {field}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Warnings */}
                  {hasWarnings && (
                    <div className="space-y-1.5">
                      <p className="text-xs font-medium text-amber-700 flex items-center gap-1.5">
                        <AlertTriangle className="h-3.5 w-3.5" />
                        Warnings ({form.warnings.length})
                      </p>
                      <div className="space-y-1 pl-5">
                        {form.warnings.map((warning, i) => (
                          <p key={i} className="text-xs text-amber-800">
                            • {warning}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CollapsibleContent>
            </Collapsible>
          );
        })}
      </CardContent>
    </Card>
  );
}

