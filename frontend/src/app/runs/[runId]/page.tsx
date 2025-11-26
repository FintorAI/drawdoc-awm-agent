"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { AgentIcon } from "@/components/ui/agent-icon";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { ArrowLeft, RefreshCw, Download } from "lucide-react";

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.runId as string;

  return (
    <div className="flex flex-col">
      <Header 
        title={`Run Details`}
        subtitle={`Run ID: ${runId}`}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" asChild>
              <Link href="/runs">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Runs
              </Link>
            </Button>
            <Button variant="outline">
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
            <Button>
              <RefreshCw className="h-4 w-4 mr-2" />
              Rerun
            </Button>
          </div>
        }
      />
      
      <div className="px-8 pb-8">
        {/* Run Overview */}
        <Card className="mb-6">
          <CardContent className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                <AgentIcon type="orderdocs" showBackground size="lg" />
                <div>
                  <h2 className="text-xl font-semibold">LN-2024-001234</h2>
                  <p className="text-sm text-muted-foreground">
                    Started Jan 15, 2024 at 10:30 AM
                  </p>
                </div>
              </div>
              <StatusBadge variant="success" size="md">
                Completed
              </StatusBadge>
            </div>
            
            <Separator className="my-6" />
            
            <div className="grid grid-cols-4 gap-8">
              <div>
                <p className="text-sm text-muted-foreground">Duration</p>
                <p className="text-lg font-medium">2m 15s</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Documents</p>
                <p className="text-lg font-medium">8 processed</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Verifications</p>
                <p className="text-lg font-medium">24 passed</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Issues</p>
                <p className="text-lg font-medium">0 found</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tabs for different views */}
        <Tabs defaultValue="agents" className="space-y-4">
          <TabsList>
            <TabsTrigger value="agents">Agent Steps</TabsTrigger>
            <TabsTrigger value="documents">Documents</TabsTrigger>
            <TabsTrigger value="verifications">Verifications</TabsTrigger>
            <TabsTrigger value="logs">Logs</TabsTrigger>
          </TabsList>
          
          <TabsContent value="agents" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Agent Pipeline</CardTitle>
                <CardDescription>Steps executed during this run</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Preparation Agent */}
                  <div className="flex items-center gap-4 p-4 rounded-lg border border-border">
                    <AgentIcon type="preparation" showBackground />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">Preparation Agent</p>
                        <StatusBadge variant="success">Completed</StatusBadge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Extracted data from 8 documents
                      </p>
                    </div>
                    <p className="text-sm text-muted-foreground">45s</p>
                  </div>
                  
                  {/* Verification Agent */}
                  <div className="flex items-center gap-4 p-4 rounded-lg border border-border">
                    <AgentIcon type="verification" showBackground />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">Verification Agent</p>
                        <StatusBadge variant="success">Completed</StatusBadge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Verified 24 fields against SOP rules
                      </p>
                    </div>
                    <p className="text-sm text-muted-foreground">1m 10s</p>
                  </div>
                  
                  {/* OrderDocs Agent */}
                  <div className="flex items-center gap-4 p-4 rounded-lg border border-border">
                    <AgentIcon type="orderdocs" showBackground />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">OrderDocs Agent</p>
                        <StatusBadge variant="success">Completed</StatusBadge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Generated final document order
                      </p>
                    </div>
                    <p className="text-sm text-muted-foreground">20s</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="documents">
            <Card>
              <CardHeader>
                <CardTitle>Processed Documents</CardTitle>
                <CardDescription>Documents included in this run</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Document list will be displayed here.</p>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="verifications">
            <Card>
              <CardHeader>
                <CardTitle>Verification Results</CardTitle>
                <CardDescription>Field verification status</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Verification results will be displayed here.</p>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="logs">
            <Card>
              <CardHeader>
                <CardTitle>Run Logs</CardTitle>
                <CardDescription>Detailed execution logs</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Logs will be displayed here.</p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

