"use client";

import { Header } from "@/components/layout/header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { AgentIcon } from "@/components/ui/agent-icon";
import { TrendingUp, Clock, AlertTriangle, CheckCircle2 } from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="flex flex-col">
      <Header 
        title="Dashboard" 
        subtitle="Overview of your document verification system"
      />
      
      <div className="px-8 pb-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Runs</p>
                  <p className="text-3xl font-semibold mt-1">1,284</p>
                  <p className="text-sm text-emerald-600 flex items-center gap-1 mt-2">
                    <TrendingUp className="h-3 w-3" />
                    +12% from last week
                  </p>
                </div>
                <div className="h-12 w-12 rounded-xl bg-primary-light flex items-center justify-center">
                  <CheckCircle2 className="h-6 w-6 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Active Now</p>
                  <p className="text-3xl font-semibold mt-1">7</p>
                  <p className="text-sm text-muted-foreground mt-2">
                    runs in progress
                  </p>
                </div>
                <div className="h-12 w-12 rounded-xl bg-blue-100 flex items-center justify-center">
                  <Clock className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Success Rate</p>
                  <p className="text-3xl font-semibold mt-1">98.5%</p>
                  <p className="text-sm text-emerald-600 flex items-center gap-1 mt-2">
                    <TrendingUp className="h-3 w-3" />
                    +2.3% improvement
                  </p>
                </div>
                <div className="h-12 w-12 rounded-xl bg-emerald-100 flex items-center justify-center">
                  <TrendingUp className="h-6 w-6 text-emerald-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Issues</p>
                  <p className="text-3xl font-semibold mt-1">3</p>
                  <p className="text-sm text-amber-600 mt-2">
                    require attention
                  </p>
                </div>
                <div className="h-12 w-12 rounded-xl bg-amber-100 flex items-center justify-center">
                  <AlertTriangle className="h-6 w-6 text-amber-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Agent Performance */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle>Agent Performance</CardTitle>
              <CardDescription>Processing times by agent type</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <AgentIcon type="preparation" showBackground />
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">Preparation Agent</span>
                      <span className="text-sm text-muted-foreground">45s avg</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full" style={{ width: "75%" }} />
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <AgentIcon type="verification" showBackground />
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">Verification Agent</span>
                      <span className="text-sm text-muted-foreground">1m 10s avg</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-emerald-500 rounded-full" style={{ width: "85%" }} />
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <AgentIcon type="orderdocs" showBackground />
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">OrderDocs Agent</span>
                      <span className="text-sm text-muted-foreground">20s avg</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-purple-500 rounded-full" style={{ width: "60%" }} />
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Latest verification runs</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { loan: "LN-2024-001234", status: "success" as const, time: "2 min ago" },
                  { loan: "LN-2024-001235", status: "processing" as const, time: "5 min ago" },
                  { loan: "LN-2024-001236", status: "warning" as const, time: "12 min ago" },
                  { loan: "LN-2024-001237", status: "success" as const, time: "25 min ago" },
                ].map((item, index) => (
                  <div key={index} className="flex items-center justify-between py-2">
                    <div className="flex items-center gap-3">
                      <AgentIcon type="orderdocs" size="sm" />
                      <span className="text-sm font-medium">{item.loan}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-muted-foreground">{item.time}</span>
                      <StatusBadge variant={item.status} size="sm">
                        {item.status === "success" && "Done"}
                        {item.status === "processing" && "Running"}
                        {item.status === "warning" && "Warning"}
                      </StatusBadge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

