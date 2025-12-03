"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Play, Loader2, AlertCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { useCreateRun } from "@/hooks/use-runs";
import {
  DOCUMENT_TYPES,
  validateLoanId,
  DEFAULT_RUN_CONFIG,
  type AgentType,
} from "@/types";

// =============================================================================
// AGENT-SPECIFIC CONFIGS
// =============================================================================

const AGENT_FORM_CONFIG = {
  drawdocs: {
    title: "New DrawDocs Run",
    description: "Configure and start a new document verification run",
    requiresLoEmail: false,
    requiresDocTypes: true,
    showUserPrompt: true,
  },
  disclosure: {
    title: "New Disclosure Run",
    description: "Process Loan Estimate disclosure for a loan",
    requiresLoEmail: true,
    requiresDocTypes: false,
    showUserPrompt: false,
  },
  loa: {
    title: "New LOA Run",
    description: "Generate Letter of Authorization",
    requiresLoEmail: true,
    requiresDocTypes: false,
    showUserPrompt: false,
  },
} as const;

// =============================================================================
// FORM COMPONENT
// =============================================================================

interface RunTriggerFormProps {
  /** Called when form is successfully submitted and run started */
  onSuccess?: (runId: string) => void;
  /** Called when form submission fails */
  onError?: (error: Error) => void;
  /** Agent type for this form (default: "drawdocs") */
  agentType?: AgentType;
  /** Additional className for the card container */
  className?: string;
}

export function RunTriggerForm({ onSuccess, onError, agentType = "drawdocs", className }: RunTriggerFormProps) {
  const router = useRouter();
  const { addToast } = useToast();
  
  // Get agent-specific config
  const formConfig = AGENT_FORM_CONFIG[agentType];
  
  // Get agent-specific route
  const getAgentRoute = (runId: string) => {
    const routes: Record<AgentType, string> = {
      drawdocs: `/drawdocs/runs/${runId}`,
      disclosure: `/disclosure/runs/${runId}`,
      loa: `/loa/runs/${runId}`,
    };
    return routes[agentType];
  };
  
  // Common form fields
  const [loanId, setLoanId] = React.useState("");
  const [demoMode, setDemoMode] = React.useState(DEFAULT_RUN_CONFIG.demo_mode);
  const [maxRetries, setMaxRetries] = React.useState(DEFAULT_RUN_CONFIG.max_retries);
  
  // Disclosure/LOA specific fields
  const [loEmail, setLoEmail] = React.useState("");
  
  // DrawDocs specific fields
  const [userPrompt, setUserPrompt] = React.useState("");
  const [selectedDocTypes, setSelectedDocTypes] = React.useState<string[]>([]);
  const [allDocuments, setAllDocuments] = React.useState(false);
  
  // Validation state
  const [validationError, setValidationError] = React.useState<string | null>(null);

  // Create run mutation
  const createRunMutation = useCreateRun({
    onSuccess: (data) => {
      addToast({
        title: "Run Started",
        description: `${formConfig.title} has been queued`,
        variant: "success",
      });
      onSuccess?.(data.run_id);
      router.push(getAgentRoute(data.run_id));
    },
    onError: (error) => {
      addToast({
        title: "Failed to Start Run",
        description: error.message,
        variant: "error",
      });
      onError?.(error);
    },
  });
  
  // Handle loan ID change with auto-trim
  const handleLoanIdChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.trim();
    setLoanId(value);
    
    if (validationError) {
      setValidationError(null);
    }
  };
  
  // Handle loan ID paste with auto-trim
  const handleLoanIdPaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedText = e.clipboardData.getData("text").trim();
    setLoanId(pastedText);
    
    if (validationError) {
      setValidationError(null);
    }
  };
  
  // Handle "All Documents" toggle
  const handleAllDocumentsChange = (checked: boolean) => {
    setAllDocuments(checked);
    if (checked) {
      setSelectedDocTypes([]);
    }
  };
  
  // Handle individual document type checkbox
  const handleDocTypeChange = (docType: string, checked: boolean) => {
    if (checked) {
      setSelectedDocTypes((prev) => [...prev, docType]);
      setAllDocuments(false);
    } else {
      setSelectedDocTypes((prev) => prev.filter((t) => t !== docType));
    }
  };
  
  // Handle max retries change with validation
  const handleMaxRetriesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value) && value >= 0 && value <= 5) {
      setMaxRetries(value);
    }
  };
  
  // Validate email (simple check)
  const validateEmail = (email: string): boolean => {
    if (!email) return false;
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };
  
  // Check if form is valid
  const isFormValid = (): boolean => {
    if (!loanId.trim()) return false;
    
    if (formConfig.requiresLoEmail) {
      if (!validateEmail(loEmail)) return false;
    }
    
    if (formConfig.requiresDocTypes) {
      if (!allDocuments && selectedDocTypes.length === 0) return false;
    }
    
    return true;
  };
  
  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate loan ID
    const validation = validateLoanId(loanId);
    if (!validation.valid) {
      setValidationError(validation.message || "Invalid loan ID");
      return;
    }
    
    setValidationError(null);
    
    // Build config based on agent type
    const baseConfig: any = {
      loan_id: loanId.trim(),
      agent_type: agentType,
      demo_mode: demoMode,
      max_retries: maxRetries,
    };
    
    // Add agent-specific fields
    if (formConfig.requiresLoEmail) {
      baseConfig.lo_email = loEmail.trim();
    }
    
    if (formConfig.requiresDocTypes) {
      baseConfig.document_types = allDocuments ? null : selectedDocTypes.length > 0 ? selectedDocTypes : null;
    }
    
    createRunMutation.mutate(baseConfig);
  };

  const isSubmitting = createRunMutation.isPending;
  
  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle>{formConfig.title}</CardTitle>
        <CardDescription>
          {formConfig.description}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Common Fields */}
          <div className="space-y-4">
            {/* Loan ID */}
            <div className="space-y-2">
              <Label htmlFor="loan-id">
                Loan ID <span className="text-red-500">*</span>
              </Label>
              <Input
                id="loan-id"
                type="text"
                placeholder="e.g., 387596ee-7090-47ca-8385-206e22c9c9da"
                value={loanId}
                onChange={handleLoanIdChange}
                onPaste={handleLoanIdPaste}
                disabled={isSubmitting}
                className={cn(validationError && "border-red-500 focus-visible:ring-red-500")}
              />
              <p className="text-xs text-muted-foreground">
                Encompass loan GUID (UUID format)
              </p>
              {validationError && (
                <div className="flex items-center gap-1 text-red-500 text-sm">
                  <AlertCircle className="h-4 w-4" />
                  <span>{validationError}</span>
                </div>
              )}
            </div>
            
            {/* LO Email (Disclosure/LOA only) */}
            {formConfig.requiresLoEmail && (
              <div className="space-y-2">
                <Label htmlFor="lo-email">
                  LO Email <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="lo-email"
                  type="email"
                  placeholder="e.g., loan.officer@example.com"
                  value={loEmail}
                  onChange={(e) => setLoEmail(e.target.value)}
                  disabled={isSubmitting}
                  className={cn(!validateEmail(loEmail) && loEmail && "border-amber-300")}
                />
                <p className="text-xs text-muted-foreground">
                  Loan officer email address
                </p>
              </div>
            )}
            
            {/* Max Retries */}
            <div className="space-y-2">
              <Label htmlFor="max-retries">Max Retries</Label>
              <Input
                id="max-retries"
                type="number"
                min={0}
                max={5}
                value={maxRetries}
                onChange={handleMaxRetriesChange}
                disabled={isSubmitting}
                className="w-24"
              />
              <p className="text-xs text-muted-foreground">
                Retry attempts per agent (0-5)
              </p>
            </div>
            
            {/* Demo Mode */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="demo-mode">Demo Mode</Label>
                  <p className="text-xs text-muted-foreground">
                    No writes to Encompass
                  </p>
                </div>
                <Switch
                  id="demo-mode"
                  checked={demoMode}
                  onCheckedChange={setDemoMode}
                  disabled={isSubmitting}
                />
              </div>
              {!demoMode && (
                <div className="flex items-center gap-2 p-2 rounded-md bg-amber-50 border border-amber-200 text-amber-800 text-xs">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span>Production mode: Changes WILL be written to Encompass</span>
                </div>
              )}
            </div>
          </div>
          
          {/* DrawDocs-specific fields */}
          {formConfig.requiresDocTypes && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Document Types</Label>
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="all-documents"
                    checked={allDocuments}
                    onCheckedChange={handleAllDocumentsChange}
                    disabled={isSubmitting}
                  />
                  <Label htmlFor="all-documents" className="text-sm font-normal cursor-pointer">
                    All Documents
                  </Label>
                </div>
              </div>
              
              <div className={cn(
                "grid grid-cols-2 gap-2 p-3 rounded-md border border-input bg-background",
                allDocuments && "opacity-50"
              )}>
                {DOCUMENT_TYPES.map((docType) => (
                  <div key={docType} className="flex items-center gap-2">
                    <Checkbox
                      id={`doc-${docType}`}
                      checked={selectedDocTypes.includes(docType)}
                      onCheckedChange={(checked) => handleDocTypeChange(docType, checked)}
                      disabled={isSubmitting || allDocuments}
                    />
                    <Label
                      htmlFor={`doc-${docType}`}
                      className="text-sm font-normal cursor-pointer"
                    >
                      {docType}
                    </Label>
                  </div>
                ))}
              </div>
              <p className={cn(
                "text-xs",
                !allDocuments && selectedDocTypes.length === 0 
                  ? "text-amber-600" 
                  : "text-muted-foreground"
              )}>
                {allDocuments
                  ? "Processing all document types"
                  : selectedDocTypes.length > 0
                  ? `${selectedDocTypes.length} type(s) selected`
                  : "⚠ Select document types or check 'All Documents'"}
              </p>
            </div>
          )}
          
          {/* User Prompt (DrawDocs only) */}
          {formConfig.showUserPrompt && (
            <div className="space-y-2">
              <Label htmlFor="user-prompt">Special Instructions (optional)</Label>
              <Textarea
                id="user-prompt"
                placeholder="e.g., 'only prep', 'skip verification', 'summary only'"
                value={userPrompt}
                onChange={(e) => setUserPrompt(e.target.value)}
                disabled={isSubmitting}
                rows={3}
              />
              <p className="text-xs text-muted-foreground">
                Add custom instructions for the agent orchestrator
              </p>
            </div>
          )}
          
          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full"
            size="lg"
            disabled={isSubmitting || !isFormValid()}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Starting Run...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Start Run
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
