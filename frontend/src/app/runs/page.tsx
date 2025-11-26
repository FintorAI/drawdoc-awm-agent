"use client";

import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { AgentIcon } from "@/components/ui/agent-icon";
import { Plus, Clock, CheckCircle2 } from "lucide-react";
import Link from "next/link";

// Mock data for demonstration
const mockRuns = [
  {
    id: "run-001",
    loanNumber: "LN-2024-001234",
    status: "success" as const,
    startedAt: "2024-01-15T10:30:00Z",
    completedAt: "2024-01-15T10:32:15Z",
    documentsProcessed: 8,
  },
  {
    id: "run-002",
    loanNumber: "LN-2024-001235",
    status: "processing" as const,
    startedAt: "2024-01-15T10:45:00Z",
    completedAt: null,
    documentsProcessed: 3,
  },
  {
    id: "run-003",
    loanNumber: "LN-2024-001236",
    status: "warning" as const,
    startedAt: "2024-01-15T09:15:00Z",
    completedAt: "2024-01-15T09:18:42Z",
    documentsProcessed: 12,
  },
  {
    id: "run-004",
    loanNumber: "LN-2024-001237",
    status: "error" as const,
    startedAt: "2024-01-15T08:00:00Z",
    completedAt: "2024-01-15T08:01:23Z",
    documentsProcessed: 2,
  },
];

export default function RunsPage() {
  return (
    <div className="flex flex-col">
      <Header 
        title="Runs" 
        subtitle="View and manage document verification runs"
        actions={
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            New Run
          </Button>
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
                      <p className="font-medium text-foreground">{run.loanNumber}</p>
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

