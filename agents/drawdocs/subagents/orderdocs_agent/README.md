# Order Docs Agent

The Order Docs Agent implements the complete workflow for running Mavent compliance checks and ordering closing documents in Encompass.

## Overview

Based on the Docs Draw SOP and Encompass API documentation, this agent executes:

1. **Mavent Check (Loan Audit)** - Validates loan data for regulatory compliance
2. **Document Ordering** - Generates closing documents through Encompass
3. **Document Delivery** - Delivers documents to eFolder or other destinations

## Workflow

### Step 1: Mavent Compliance Check

Runs a compliance audit to validate loan data before document generation:

```python
POST /encompassdocs/v1/documentAudits/closing
```

**Process:**
- Creates audit snapshot for the loan
- Polls until audit completes
- Reviews compliance issues (if any)
- Returns `audit_id` for document ordering

**Output:**
```json
{
  "audit_id": "abc123",
  "status": "Completed",
  "issues": [],
  "location": "/encompassdocs/v1/documentAudits/closing/abc123"
}
```

### Step 2: Order Documents

Orders closing documents using the audit snapshot:

```python
POST /encompassdocs/v1/documentOrders/closing
```

**Request:**
```json
{
  "auditId": "abc123",
  "printMode": "LoanData"
}
```

**Process:**
- Creates document order with audit ID
- Polls until documents are generated
- Returns `doc_set_id` and document list

**Output:**
```json
{
  "doc_set_id": "xyz789",
  "status": "Completed",
  "documents": [
    {"name": "Promissory Note", "id": "..."},
    {"name": "Deed of Trust", "id": "..."}
  ]
}
```

### Step 3: Request Delivery

Delivers documents to eFolder or other recipients:

```python
POST /encompassdocs/v1/documentOrders/closing/{docSetId}/delivery
```

**Request:**
```json
{
  "deliveryMethod": "eFolder",
  "recipients": ["borrower@example.com"]
}
```

## Usage

### Python API

```python
from agents.drawdocs.subagents.orderdocs_agent.orderdocs_agent import run_orderdocs_agent

# Run complete workflow
result = run_orderdocs_agent(
    loan_id="your-loan-guid",
    application_id="borrower-id",  # Optional
    audit_type="closing",
    order_type="closing",
    delivery_method="eFolder",
    dry_run=False  # Set to True for testing
)

print(f"Status: {result['status']}")
print(f"Audit ID: {result['summary']['audit_id']}")
print(f"Doc Set ID: {result['summary']['doc_set_id']}")
print(f"Documents: {result['summary']['documents_ordered']}")
```

### Command Line

```bash
# Run for a specific loan
python orderdocs_agent.py \
  --loan-id "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6" \
  --type closing \
  --delivery eFolder \
  --output results.json

# Dry run (no actual API calls)
python orderdocs_agent.py \
  --loan-id "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6" \
  --dry-run \
  --output dry_run_results.json
```

### Individual Steps

You can also run individual steps:

```python
from agents.drawdocs.subagents.orderdocs_agent.orderdocs_agent import (
    run_mavent_check,
    order_documents,
    deliver_documents
)

# Step 1: Mavent check
mavent_result = run_mavent_check(
    loan_id="your-loan-guid",
    audit_type="closing"
)

# Step 2: Order documents
order_result = order_documents(
    loan_id="your-loan-guid",
    audit_id=mavent_result["audit_id"],
    order_type="closing"
)

# Step 3: Deliver documents
delivery_result = deliver_documents(
    doc_set_id=order_result["doc_set_id"],
    order_type="closing",
    delivery_method="eFolder"
)
```

## API Endpoints

This agent uses the Encompass Docs API (`/encompassdocs/v1/*`) through the MCP server:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/encompassdocs/v1/documentAudits/closing` | POST | Create loan audit (Mavent check) |
| `/encompassdocs/v1/documentAudits/closing/{auditId}` | GET | Get audit status |
| `/encompassdocs/v1/documentOrders/closing` | POST | Create document order |
| `/encompassdocs/v1/documentOrders/closing/{docSetId}` | GET | Get order status |
| `/encompassdocs/v1/documentOrders/closing/{docSetId}/delivery` | POST | Request document delivery |

## Configuration

### Environment Variables

The agent uses the MCP server for API calls, which requires:

```bash
# From encompass-mcp-server/.env
ENCOMPASS_API_SERVER=https://concept.api.elliemae.com
ENCOMPASS_CLIENT_ID=your_client_id
ENCOMPASS_CLIENT_SECRET=your_client_secret
ENCOMPASS_INSTANCE_ID=your_instance_id
```

### Polling Configuration

The agent polls for completion with configurable timeouts:

- **Mavent Check:** 60 attempts × 5s = 5 minutes max
- **Document Order:** 120 attempts × 5s = 10 minutes max

You can adjust these in the `_poll_until_complete` calls.

## Error Handling

The agent handles various error scenarios:

### Compliance Issues

If Mavent finds compliance issues, they are logged but the workflow continues:

```json
{
  "issues": [
    {
      "severity": "Warning",
      "message": "Missing borrower SSN"
    }
  ]
}
```

In production, you might want to halt on critical issues.

### Timeout

If polling times out, the agent returns a timeout status:

```json
{
  "status": "Timeout",
  "error": "Polling timeout"
}
```

### API Errors

API errors are caught and returned in the result:

```json
{
  "status": "Error",
  "error": "401 Unauthorized: Invalid credentials"
}
```

## Testing

### Dry Run Mode

Test the workflow without making actual API calls:

```python
result = run_orderdocs_agent(
    loan_id="test-loan-id",
    dry_run=True
)
```

This returns mock data for all steps.

### With Test Script

```bash
# Run test script
python test_orderdocs.py
```

## Output Format

The complete workflow returns:

```json
{
  "loan_id": "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6",
  "status": "Success",
  "start_time": "2025-12-01T10:00:00",
  "end_time": "2025-12-01T10:05:30",
  "duration_seconds": 330,
  "dry_run": false,
  "steps": {
    "mavent_check": {
      "audit_id": "abc123",
      "status": "Completed",
      "issues": []
    },
    "order_documents": {
      "doc_set_id": "xyz789",
      "status": "Completed",
      "documents": [...]
    },
    "deliver_documents": {
      "status": "Success",
      "delivery_method": "eFolder"
    }
  },
  "summary": {
    "audit_id": "abc123",
    "doc_set_id": "xyz789",
    "compliance_issues": 0,
    "documents_ordered": 25,
    "delivery_method": "eFolder"
  }
}
```

## Integration with Orchestrator

The orchestrator calls this agent after verification:

```python
# In orchestrator_agent.py
orderdocs_result = run_orderdocs_agent(
    loan_id=loan_id,
    audit_type="closing",
    order_type="closing",
    delivery_method="eFolder",
    dry_run=self.dry_run
)
```

## References

- **Guide:** `/Users/antonboquer/Documents/Fintor/encompass-mcp-server/MAVENT_AND_ORDER_DOCS_GUIDE.md`
- **MCP Server:** `/Users/antonboquer/Documents/Fintor/encompass-mcp-server/`
- **Encompass API:** Encompass Developer Portal → Docs API

## Troubleshooting

### "MCP server not found"

Ensure the MCP server is in the correct location:
```
/Users/antonboquer/Documents/Fintor/encompass-mcp-server/
```

### "Failed to initialize MCP client"

Check that the MCP server `.env` has correct credentials:
```bash
cat /Users/antonboquer/Documents/Fintor/encompass-mcp-server/.env
```

### "Audit failed" or "Order failed"

Check the loan meets requirements:
- Loan is in correct pipeline stage
- All required fields are populated
- User has permission to order docs

### Polling timeout

Increase timeout values or check Encompass API status.
