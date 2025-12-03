"use client";

import * as React from "react";
import { Check, X, Edit2, AlertCircle, Loader2, Save, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RunDetail } from "@/types";

// =============================================================================
// TYPES
// =============================================================================

type FieldDecision = "accept" | "reject" | "edit" | "pending";

interface PendingField {
  field_id: string;
  field_name: string;
  extracted_value: string | number | null;
  source_document: string;
  attachment_id: string;
  confidence: number | null;
}

interface FieldReviewState {
  decision: FieldDecision;
  editedValue?: string;
  rejectionReason?: string;
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchPendingFields(runId: string): Promise<{
  run_id: string;
  loan_id: string;
  status: string;
  fields: PendingField[];
  total_fields: number;
  documents_processed: number;
}> {
  const response = await fetch(`${API_BASE}/api/runs/${runId}/pending-fields`);
  if (!response.ok) {
    throw new Error(`Failed to fetch pending fields: ${response.statusText}`);
  }
  return response.json();
}

async function submitFieldReview(
  runId: string,
  decisions: Array<{
    field_id: string;
    decision: "accept" | "reject" | "edit";
    edited_value?: string;
    rejection_reason?: string;
  }>,
  proceed: boolean
): Promise<{
  success: boolean;
  accepted_count: number;
  rejected_count: number;
  edited_count: number;
  message: string;
}> {
  const response = await fetch(`${API_BASE}/api/runs/${runId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decisions, proceed }),
  });
  if (!response.ok) {
    throw new Error(`Failed to submit review: ${response.statusText}`);
  }
  return response.json();
}

// =============================================================================
// SKELETON
// =============================================================================

function FieldReviewSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-64" />
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center gap-4 p-3 rounded-lg border">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-5 w-48" />
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-8 w-24 ml-auto" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// EDIT DIALOG
// =============================================================================

interface EditDialogProps {
  field: PendingField | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (fieldId: string, newValue: string) => void;
}

function EditDialog({ field, isOpen, onClose, onSave }: EditDialogProps) {
  const [editValue, setEditValue] = React.useState("");

  React.useEffect(() => {
    if (field) {
      setEditValue(String(field.extracted_value || ""));
    }
  }, [field]);

  if (!field) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Field Value</DialogTitle>
          <DialogDescription>
            Modify the extracted value before writing to Encompass
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Field</label>
            <p className="text-sm text-muted-foreground">
              {field.field_name} ({field.field_id})
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Original Value</label>
            <p className="text-sm text-muted-foreground bg-muted p-2 rounded">
              {String(field.extracted_value || "(empty)")}
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">New Value</label>
            <Input
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              placeholder="Enter new value"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Source</label>
            <p className="text-sm text-muted-foreground">
              Extracted from: {field.source_document}
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => onSave(field.field_id, editValue)}>
            <Save className="h-4 w-4 mr-2" />
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// =============================================================================
// REJECT DIALOG
// =============================================================================

interface RejectDialogProps {
  field: PendingField | null;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (fieldId: string, reason: string) => void;
}

function RejectDialog({ field, isOpen, onClose, onConfirm }: RejectDialogProps) {
  const [reason, setReason] = React.useState("");

  if (!field) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reject Field</DialogTitle>
          <DialogDescription>
            This field will not be written to Encompass
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Field</label>
            <p className="text-sm text-muted-foreground">
              {field.field_name} ({field.field_id})
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Value to Reject</label>
            <p className="text-sm text-muted-foreground bg-muted p-2 rounded">
              {String(field.extracted_value || "(empty)")}
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Reason (optional)</label>
            <Textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Why are you rejecting this value?"
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={() => onConfirm(field.field_id, reason)}
          >
            <X className="h-4 w-4 mr-2" />
            Reject Field
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// =============================================================================
// FIELD ROW
// =============================================================================

interface FieldRowProps {
  field: PendingField;
  reviewState: FieldReviewState;
  onAccept: () => void;
  onReject: () => void;
  onEdit: () => void;
  onReset: () => void;
}

function FieldRow({ field, reviewState, onAccept, onReject, onEdit, onReset }: FieldRowProps) {
  const getDecisionBadge = () => {
    switch (reviewState.decision) {
      case "accept":
        return <Badge className="bg-green-100 text-green-800 border-green-200">✓ Accepted</Badge>;
      case "reject":
        return <Badge className="bg-red-100 text-red-800 border-red-200">✗ Rejected</Badge>;
      case "edit":
        return <Badge className="bg-blue-100 text-blue-800 border-blue-200">✎ Edited</Badge>;
      default:
        return <Badge variant="outline">Pending</Badge>;
    }
  };

  const displayValue = reviewState.decision === "edit" 
    ? reviewState.editedValue 
    : String(field.extracted_value || "(empty)");

  return (
    <TableRow className={cn(
      reviewState.decision === "accept" && "bg-green-50/50",
      reviewState.decision === "reject" && "bg-red-50/50 opacity-60",
      reviewState.decision === "edit" && "bg-blue-50/50",
    )}>
      <TableCell className="font-medium">
        <div>
          <span className="text-sm">{field.field_name}</span>
          <span className="text-xs text-muted-foreground ml-2">({field.field_id})</span>
        </div>
      </TableCell>
      <TableCell>
        <code className={cn(
          "text-sm px-2 py-1 rounded",
          reviewState.decision === "edit" ? "bg-blue-100 text-blue-800" : "bg-muted"
        )}>
          {displayValue}
        </code>
        {reviewState.decision === "edit" && (
          <span className="text-xs text-muted-foreground ml-2">
            (was: {String(field.extracted_value || "(empty)")})
          </span>
        )}
      </TableCell>
      <TableCell>
        <span className="text-sm text-muted-foreground">{field.source_document}</span>
      </TableCell>
      <TableCell>
        {getDecisionBadge()}
      </TableCell>
      <TableCell className="text-right">
        {reviewState.decision === "pending" ? (
          <div className="flex items-center justify-end gap-1">
            <Button
              size="sm"
              variant="ghost"
              className="h-8 text-green-600 hover:text-green-700 hover:bg-green-100"
              onClick={onAccept}
            >
              <Check className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-8 text-red-600 hover:text-red-700 hover:bg-red-100"
              onClick={onReject}
            >
              <X className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-8 text-blue-600 hover:text-blue-700 hover:bg-blue-100"
              onClick={onEdit}
            >
              <Edit2 className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <Button
            size="sm"
            variant="ghost"
            className="h-8"
            onClick={onReset}
          >
            <RotateCcw className="h-4 w-4" />
          </Button>
        )}
      </TableCell>
    </TableRow>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

interface FieldReviewTabProps {
  runDetail: RunDetail | undefined;
  runId: string;
  isLoading: boolean;
  className?: string;
}

export function FieldReviewTab({ runDetail, runId, isLoading, className }: FieldReviewTabProps) {
  // State
  const [pendingFields, setPendingFields] = React.useState<PendingField[]>([]);
  const [reviewStates, setReviewStates] = React.useState<Record<string, FieldReviewState>>({});
  const [isLoadingFields, setIsLoadingFields] = React.useState(true);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [submitResult, setSubmitResult] = React.useState<{ success: boolean; message: string } | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  // Dialog state
  const [editingField, setEditingField] = React.useState<PendingField | null>(null);
  const [rejectingField, setRejectingField] = React.useState<PendingField | null>(null);

  // Load pending fields
  React.useEffect(() => {
    if (!runId) return;

    const loadFields = async () => {
      try {
        setIsLoadingFields(true);
        setError(null);
        const data = await fetchPendingFields(runId);
        setPendingFields(data.fields);
        
        // Initialize review states
        const initialStates: Record<string, FieldReviewState> = {};
        data.fields.forEach((field) => {
          initialStates[field.field_id] = { decision: "pending" };
        });
        setReviewStates(initialStates);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load fields");
      } finally {
        setIsLoadingFields(false);
      }
    };

    loadFields();
  }, [runId]);

  // Actions
  const handleAccept = (fieldId: string) => {
    setReviewStates((prev) => ({
      ...prev,
      [fieldId]: { decision: "accept" },
    }));
  };

  const handleReject = (fieldId: string, reason: string) => {
    setReviewStates((prev) => ({
      ...prev,
      [fieldId]: { decision: "reject", rejectionReason: reason },
    }));
    setRejectingField(null);
  };

  const handleEdit = (fieldId: string, newValue: string) => {
    setReviewStates((prev) => ({
      ...prev,
      [fieldId]: { decision: "edit", editedValue: newValue },
    }));
    setEditingField(null);
  };

  const handleReset = (fieldId: string) => {
    setReviewStates((prev) => ({
      ...prev,
      [fieldId]: { decision: "pending" },
    }));
  };

  const handleAcceptAll = () => {
    const newStates: Record<string, FieldReviewState> = {};
    pendingFields.forEach((field) => {
      if (reviewStates[field.field_id]?.decision === "pending") {
        newStates[field.field_id] = { decision: "accept" };
      } else {
        newStates[field.field_id] = reviewStates[field.field_id];
      }
    });
    setReviewStates(newStates);
  };

  const handleSubmit = async (proceed: boolean) => {
    try {
      setIsSubmitting(true);
      setError(null);

      const decisions = Object.entries(reviewStates)
        .filter(([_, state]) => state.decision !== "pending")
        .map(([fieldId, state]) => ({
          field_id: fieldId,
          decision: state.decision as "accept" | "reject" | "edit",
          edited_value: state.editedValue,
          rejection_reason: state.rejectionReason,
        }));

      const result = await submitFieldReview(runId, decisions, proceed);
      setSubmitResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit review");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Computed values
  const stats = React.useMemo(() => {
    const decisions = Object.values(reviewStates);
    return {
      total: decisions.length,
      pending: decisions.filter((d) => d.decision === "pending").length,
      accepted: decisions.filter((d) => d.decision === "accept").length,
      rejected: decisions.filter((d) => d.decision === "reject").length,
      edited: decisions.filter((d) => d.decision === "edit").length,
    };
  }, [reviewStates]);

  const allDecided = stats.pending === 0 && stats.total > 0;

  // Render
  if (isLoading || isLoadingFields) {
    return <FieldReviewSkeleton />;
  }

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="py-12">
          <div className="flex flex-col items-center justify-center text-center">
            <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
            <h3 className="text-lg font-semibold mb-2">Error Loading Fields</h3>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button variant="outline" onClick={() => window.location.reload()}>
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (submitResult) {
    return (
      <Card className={className}>
        <CardContent className="py-12">
          <div className="flex flex-col items-center justify-center text-center">
            <div className={cn(
              "h-16 w-16 rounded-full flex items-center justify-center mb-4",
              submitResult.success ? "bg-green-100" : "bg-red-100"
            )}>
              {submitResult.success ? (
                <Check className="h-8 w-8 text-green-600" />
              ) : (
                <X className="h-8 w-8 text-red-600" />
              )}
            </div>
            <h3 className="text-lg font-semibold mb-2">
              {submitResult.success ? "Review Submitted" : "Submission Failed"}
            </h3>
            <p className="text-muted-foreground mb-4">{submitResult.message}</p>
            <div className="flex gap-2">
              <Badge className="bg-green-100 text-green-800">{stats.accepted} Accepted</Badge>
              <Badge className="bg-red-100 text-red-800">{stats.rejected} Rejected</Badge>
              <Badge className="bg-blue-100 text-blue-800">{stats.edited} Edited</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (pendingFields.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="py-12">
          <div className="flex flex-col items-center justify-center text-center">
            <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center mb-4">
              <span className="text-2xl">📋</span>
            </div>
            <h3 className="text-lg font-semibold mb-2">No Fields to Review</h3>
            <p className="text-muted-foreground">
              No fields were extracted from the documents, or the prep agent hasn't completed yet.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <span className="text-2xl">🔍</span>
              Field Review
            </CardTitle>
            <CardDescription>
              Review extracted fields before writing to Encompass
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{stats.total} fields</Badge>
            {stats.pending > 0 && (
              <Badge className="bg-amber-100 text-amber-800 border-amber-200">
                {stats.pending} pending
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Stats bar */}
        <div className="flex items-center gap-4 p-3 rounded-lg bg-muted/50">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Status:</span>
            <Badge className="bg-green-100 text-green-800">{stats.accepted} ✓</Badge>
            <Badge className="bg-red-100 text-red-800">{stats.rejected} ✗</Badge>
            <Badge className="bg-blue-100 text-blue-800">{stats.edited} ✎</Badge>
            <Badge variant="outline">{stats.pending} pending</Badge>
          </div>
          <div className="ml-auto">
            <Button
              size="sm"
              variant="outline"
              onClick={handleAcceptAll}
              disabled={stats.pending === 0}
            >
              <Check className="h-4 w-4 mr-1" />
              Accept All Pending
            </Button>
          </div>
        </div>

        {/* Fields table */}
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[200px]">Field</TableHead>
                <TableHead>Value</TableHead>
                <TableHead className="w-[150px]">Source</TableHead>
                <TableHead className="w-[100px]">Decision</TableHead>
                <TableHead className="w-[100px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pendingFields.map((field) => (
                <FieldRow
                  key={field.field_id}
                  field={field}
                  reviewState={reviewStates[field.field_id] || { decision: "pending" }}
                  onAccept={() => handleAccept(field.field_id)}
                  onReject={() => setRejectingField(field)}
                  onEdit={() => setEditingField(field)}
                  onReset={() => handleReset(field.field_id)}
                />
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>

      <CardFooter className="flex items-center justify-between border-t pt-6">
        <p className="text-sm text-muted-foreground">
          {allDecided
            ? "All fields reviewed. Ready to continue."
            : `${stats.pending} field(s) still need review`}
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => handleSubmit(false)}
            disabled={isSubmitting || stats.total === 0}
          >
            Cancel Run
          </Button>
          <Button
            onClick={() => handleSubmit(true)}
            disabled={isSubmitting || !allDecided}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Submitting...
              </>
            ) : (
              <>
                <Check className="h-4 w-4 mr-2" />
                Continue ({stats.accepted + stats.edited} fields)
              </>
            )}
          </Button>
        </div>
      </CardFooter>

      {/* Dialogs */}
      <EditDialog
        field={editingField}
        isOpen={!!editingField}
        onClose={() => setEditingField(null)}
        onSave={handleEdit}
      />
      <RejectDialog
        field={rejectingField}
        isOpen={!!rejectingField}
        onClose={() => setRejectingField(null)}
        onConfirm={handleReject}
      />
    </Card>
  );
}

