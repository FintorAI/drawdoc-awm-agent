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
} from "@/types";

// =============================================================================
// FORM COMPONENT
// =============================================================================

interface RunTriggerFormProps {
  /** Called when form is successfully submitted and run started */
  onSuccess?: (runId: string) => void;
  /** Called when form submission fails */
  onError?: (error: Error) => void;
  /** Additional className for the card container */
  className?: string;
}

export function RunTriggerForm({ onSuccess, onError, className }: RunTriggerFormProps) {
  const router = useRouter();
  const { addToast } = useToast();
  
  // Form state
  const [loanId, setLoanId] = React.useState("");
  const [userPrompt, setUserPrompt] = React.useState("");
  const [demoMode, setDemoMode] = React.useState(DEFAULT_RUN_CONFIG.demo_mode);
  const [maxRetries, setMaxRetries] = React.useState(DEFAULT_RUN_CONFIG.max_retries);
  const [selectedDocTypes, setSelectedDocTypes] = React.useState<string[]>([]);
  const [allDocuments, setAllDocuments] = React.useState(true);
  
  // Validation state
  const [validationError, setValidationError] = React.useState<string | null>(null);

  // Create run mutation
  const createRunMutation = useCreateRun({
    onSuccess: (data) => {
      addToast({
        title: "Run Started",
        description: `Agent run has been queued`,
        variant: "success",
      });
      onSuccess?.(data.run_id);
      router.push(`/runs/${data.run_id}`);
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
    
    // Clear validation error when user starts typing
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
    
    // Build config and submit
    createRunMutation.mutate({
      loan_id: loanId.trim(),
      demo_mode: demoMode,
      max_retries: maxRetries,
      document_types: allDocuments ? null : selectedDocTypes.length > 0 ? selectedDocTypes : null,
    });
  };

  const isSubmitting = createRunMutation.isPending;
  
  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle>New Agent Run</CardTitle>
        <CardDescription>
          Configure and start a new document verification run
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Two-column layout for larger screens */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left Column */}
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
            
            {/* Right Column */}
            <div className="space-y-4">
              {/* Document Types */}
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
                <p className="text-xs text-muted-foreground">
                  {allDocuments
                    ? "Processing all document types"
                    : selectedDocTypes.length > 0
                    ? `${selectedDocTypes.length} type(s) selected`
                    : "Select specific document types to process"}
                </p>
              </div>
            </div>
          </div>
          
          {/* Full-width User Prompt */}
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
          
          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full"
            size="lg"
            disabled={isSubmitting || !loanId.trim()}
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

