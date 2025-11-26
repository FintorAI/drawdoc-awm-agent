"use client";

import * as React from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { AgentIcon } from "@/components/ui/agent-icon";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { RunTriggerForm } from "@/components/runs/run-trigger-form";
import { Plus, Clock, CheckCircle2 } from "lucide-react";
import Link from "next/link";

// Mock data for demonstration
const mockRuns = [
  {
    id: "run-001",
    loanNumber: "387596ee-7090-47ca-8385-206e22c9c9da",
    status: "success" as const,
    startedAt: "2024-01-15T10:30:00Z",
    completedAt: "2024-01-15T10:32:15Z",
    documentsProcessed: 8,
    demoMode: true,
  },
  {
    id: "run-002",
    loanNumber: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    status: "processing" as const,
    startedAt: "2024-01-15T10:45:00Z",
    completedAt: null,
    documentsProcessed: 3,
    demoMode: true,
  },
  {
    id: "run-003",
    loanNumber: "12345678-1234-1234-1234-123456789012",
    status: "warning" as const,
    startedAt: "2024-01-15T09:15:00Z",
    completedAt: "2024-01-15T09:18:42Z",
    documentsProcessed: 12,
    demoMode: false,
  },
  {
    id: "run-004",
    loanNumber: "fedcba98-7654-3210-fedc-ba9876543210",
    status: "error" as const,
    startedAt: "2024-01-15T08:00:00Z",
    completedAt: "2024-01-15T08:01:23Z",
    documentsProcessed: 2,
    demoMode: true,
  },
];

export default function RunsPage() {
  const [isNewRunOpen, setIsNewRunOpen] = React.useState(false);

  const handleRunSuccess = (_runId: string) => {
    setIsNewRunOpen(false);
    // Navigation is handled inside RunTriggerForm
  };

  return (
    <div className="flex flex-col">
      <Header 
        title="Runs" 
        subtitle="View and manage document verification runs"
        actions={
          <Sheet open={isNewRunOpen} onOpenChange={setIsNewRunOpen}>
            <Button onClick={() => setIsNewRunOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Run
            </Button>
            <SheetContent side="right" className="w-full sm:max-w-xl overflow-y-auto">
              <SheetHeader className="mb-6">
                <SheetTitle>Start New Run</SheetTitle>
                <SheetDescription>
                  Configure and trigger a new document verification run
                </SheetDescription>
              </SheetHeader>
              <RunTriggerForm 
                onSuccess={handleRunSuccess}
                className="border-0 shadow-none"
              />
            </SheetContent>
          </Sheet>
        }
      />
      
      <div className="px-8 pb-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-emerald-100 flex items-center justify-center">
                  <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                </div>
                <div>
                  <p className="text-2xl font-semibold">24</p>
                  <p className="text-sm text-muted-foreground">Completed Today</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
                  <Clock className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-semibold">3</p>
                  <p className="text-sm text-muted-foreground">In Progress</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <AgentIcon type="preparation" showBackground size="lg" />
                <div>
                  <p className="text-2xl font-semibold">156</p>
                  <p className="text-sm text-muted-foreground">Docs Processed</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <AgentIcon type="verification" showBackground size="lg" />
                <div>
                  <p className="text-2xl font-semibold">98.5%</p>
                  <p className="text-sm text-muted-foreground">Success Rate</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
        
        {/* Runs List */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Runs</CardTitle>
            <CardDescription>View recent document verification runs</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockRuns.map((run) => (
                <Link 
                  key={run.id} 
                  href={`/runs/${run.id}`}
                  className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <AgentIcon type="orderdocs" showBackground />
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-foreground font-mono text-sm">
                          {run.loanNumber.substring(0, 8)}...
                        </p>
                        {run.demoMode && (
                          <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-medium">
                            DEMO
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Started {new Date(run.startedAt).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-sm font-medium">{run.documentsProcessed} docs</p>
                    </div>
                    <StatusBadge variant={run.status} size="md">
                      {run.status === "success" && "Completed"}
                      {run.status === "processing" && "Processing"}
                      {run.status === "warning" && "Warnings"}
                      {run.status === "error" && "Failed"}
                    </StatusBadge>
                  </div>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
