"use client";

import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { Upload, FileText, Search } from "lucide-react";

// Mock document data
const mockDocuments = [
  {
    id: "doc-001",
    name: "Promissory Note",
    type: "Legal",
    uploadedAt: "2024-01-15T09:00:00Z",
    status: "verified" as const,
    loanNumber: "LN-2024-001234",
  },
  {
    id: "doc-002",
    name: "Deed of Trust",
    type: "Legal",
    uploadedAt: "2024-01-15T09:00:00Z",
    status: "verified" as const,
    loanNumber: "LN-2024-001234",
  },
  {
    id: "doc-003",
    name: "Closing Disclosure",
    type: "Disclosure",
    uploadedAt: "2024-01-15T09:00:00Z",
    status: "pending" as const,
    loanNumber: "LN-2024-001235",
  },
  {
    id: "doc-004",
    name: "Title Insurance",
    type: "Insurance",
    uploadedAt: "2024-01-14T14:30:00Z",
    status: "verified" as const,
    loanNumber: "LN-2024-001234",
  },
  {
    id: "doc-005",
    name: "Appraisal Report",
    type: "Valuation",
    uploadedAt: "2024-01-14T11:00:00Z",
    status: "warning" as const,
    loanNumber: "LN-2024-001236",
  },
];

export default function DocumentsPage() {
  return (
    <div className="flex flex-col">
      <Header 
        title="Documents" 
        subtitle="View and manage uploaded documents"
        actions={
          <Button>
            <Upload className="h-4 w-4 mr-2" />
            Upload Documents
          </Button>
        }
      />
      
      <div className="px-8 pb-8">
        {/* Search and filters placeholder */}
        <Card className="mb-6">
          <CardContent className="p-4">
            <div className="flex items-center gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search documents..."
                  className="w-full pl-10 pr-4 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>
              <Button variant="outline">Filter</Button>
            </div>
          </CardContent>
        </Card>

        {/* Documents List */}
        <Card>
          <CardHeader>
            <CardTitle>All Documents</CardTitle>
            <CardDescription>Documents uploaded across all loan files</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockDocuments.map((doc) => (
                <div 
                  key={doc.id} 
                  className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-muted/50 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-lg bg-slate-100 flex items-center justify-center">
                      <FileText className="h-5 w-5 text-slate-600" />
                    </div>
                    <div>
                      <p className="font-medium text-foreground">{doc.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {doc.type} • {doc.loanNumber}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-sm text-muted-foreground">
                        {new Date(doc.uploadedAt).toLocaleDateString()}
                      </p>
                    </div>
                    <StatusBadge 
                      variant={doc.status === "verified" ? "success" : doc.status === "pending" ? "pending" : "warning"} 
                      size="md"
                    >
                      {doc.status === "verified" && "Verified"}
                      {doc.status === "pending" && "Pending"}
                      {doc.status === "warning" && "Needs Review"}
                    </StatusBadge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

