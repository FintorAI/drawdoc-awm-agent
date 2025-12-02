# Send Agent (v2)

The Send Agent is responsible for running mandatory compliance checks and ordering Initial Disclosures via the eDisclosures API.

## Overview

This agent replaces the Request Agent from v1 with expanded compliance responsibilities:

1. **Mavent Compliance Check** (MANDATORY)
   - All Fail/Alert/Warning must be cleared before sending
   - Blocks disclosure if any issues exist

2. **ATR/QM Flag Check** (MANDATORY)
   - Loan Features, Points and Fees, Price Limit flags
   - Must NOT be RED to proceed

3. **eDisclosures Ordering**
   - Audit loan before ordering
   - Order Initial Disclosure package
   - Deliver to borrower (without fulfillment)

## Tools

### Mavent Tools (`tools/mavent_tools.py`)

| Tool | Purpose |
|------|---------|
| `check_mavent` | Run compliance check, return pass/fail with issues |
| `get_mavent_issues` | Get detailed categorized issues |

### ATR/QM Tools (`tools/atr_qm_tools.py`)

| Tool | Purpose |
|------|---------|
| `check_atr_qm` | Check all flags, return red/yellow status |
| `get_points_and_fees_test` | Get Points & Fees test details |

### Order Tools (`tools/order_tools.py`)

| Tool | Purpose |
|------|---------|
| `audit_loan` | Run mandatory audit before ordering |
| `order_disclosure_package` | Order Initial Disclosure via API |
| `get_application_id` | Get application ID from loan |

## API Flow

```
Step 1: Audit Loan
POST /encompassdocs/v1/documentAudits/opening
→ Returns auditSnapshotId

Step 2: Create Order
POST /encompassdocs/v1/documentOrders/opening
→ Returns docSetId

Step 3: Deliver Package
POST /encompassdocs/v1/documentOrders/opening/{docSetId}/delivery
→ Returns trackingId
```

## Usage

```python
from agents.disclosure.subagents.send_agent import run_disclosure_send

result = run_disclosure_send(
    loan_id="your-loan-guid",
    dry_run=True  # Set False to actually order
)

print(result["status"])  # "success", "blocked", or "failed"
print(result["tracking_id"])  # If ordered successfully
print(result["blocking_issues"])  # List of issues that blocked
```

## Blocking Conditions

The agent will stop and report (not proceed to ordering) if:

- Mavent has any Fail, Alert, or Warning
- ATR/QM has any RED flag
- Audit has unresolved issues

## Result Structure

```python
{
    "loan_id": "...",
    "status": "success" | "blocked" | "failed",
    "mavent_result": {
        "passed": True/False,
        "has_fails": True/False,
        "total_issues": int,
        # ...
    },
    "atr_qm_result": {
        "passed": True/False,
        "red_flags": [],
        # ...
    },
    "order_result": {
        "success": True/False,
        "tracking_id": "...",
        "doc_set_id": "...",
        # ...
    },
    "tracking_id": "...",  # If ordered
    "blocking_issues": [],
    "summary": "...",
}
```

## Agent Instructions

```
You are the Disclosure Send Agent.
Your job is to run compliance checks and order disclosures.

WORKFLOW:
1. Check Mavent compliance - MANDATORY (must pass to proceed)
2. Check ATR/QM flags - MANDATORY (must be GREEN)
3. Run mandatory audits before ordering
4. Order Initial Disclosure package via eDisclosures
5. Return send results with tracking ID
```

