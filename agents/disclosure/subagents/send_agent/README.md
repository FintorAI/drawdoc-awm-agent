# Send Agent (v2) 🆕

**Version**: 2.0 (NEW in v2 with 2 GAPS implementations)  
**Last Updated**: December 18, 2025  

[🔙 Back to Main Disclosure README](../../README.md)

---

## Overview

The **Send Agent** is the third and final agent in the Disclosure v2 workflow. It runs mandatory compliance checks (Mavent, ATR/QM) and orders Initial Loan Estimate (LE) disclosures via the Encompass eDisclosures API.

**Purpose**: Ensure compliance and deliver LE to borrower electronically.

**Position in Workflow**: Verification Agent (v2) → Preparation Agent (v2) → **Send Agent (v2)**

**Replaces**: Request Agent from v1 (which sent emails to LOs)

---

## v2 Key Features

### 1. Mavent Compliance Check (MANDATORY) ✅
- Runs automated compliance check
- **Blocking**: ANY Fail, Alert, or Warning blocks disclosure
- Reports all issues categorized by severity
- Must be cleared before ordering

### 2. ATR/QM Flag Check (MANDATORY) ✅
- Checks: Loan Features, Points and Fees, Price Limit flags
- **Blocking**: ANY RED flag blocks disclosure
- YELLOW flags are warnings (do not block)
- Must be GREEN to proceed

### 3. eDisclosures Ordering ✅
- 3-step API workflow:
  1. **Audit Loan**: Run mandatory audit
  2. **Create Order**: Order Initial Disclosure package
  3. **Deliver Package**: Send to borrower (without fulfillment)
- Returns tracking ID for monitoring

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                  SEND AGENT (v2)                            │
│                                                             │
│  Step 1: Mavent Compliance (MANDATORY)                      │
│  ├── check_mavent()             → Pass/Fail/Alert/Warning │
│  └── get_mavent_issues()        → Detailed issue list     │
│      ❌ BLOCKING if any issues                             │
│                                                             │
│  Step 2: ATR/QM Flags (MANDATORY)                          │
│  ├── check_atr_qm()             → Check all flags         │
│  └── get_points_and_fees_test() → P&F details             │
│      ❌ BLOCKING if RED flags                              │
│                                                             │
│  Step 3: Order eDisclosures (if checks pass)               │
│  ├── get_application_id()       → Get borrower app ID     │
│  ├── audit_loan()               → Run mandatory audit     │
│  ├── order_disclosure_package() → Create order            │
│  └── Returns tracking_id        → For monitoring          │
│                                                             │
│  Output: Tracking ID (if ordered) or blocking issues       │
└────────────────────────────────────────────────────────────┘
```

---

## GAPS Implementations

This agent implements 2 GAPS from the Disclosure Desk SOP:

| Gap | Name | Status | Tool Module |
|-----|------|--------|-------------|
| G16 | Audit Exception Filter | ✅ Full | `audit_tools.py` |
| G21 | LO Review Workflow | 🚧 Manual | `review_tools.py` |

**G16 Details**: 
- Filters out acceptable audit exceptions (Error 26.4, HMDA Alerts)
- Blocks only on critical/unresolved issues
- Integrated into `audit_loan()` flow

**G21 Details**:
- Manual workflow for LO review and approval
- Logs review status and comments
- Phase 2: Full automation with approval API

See [`GAPS.md`](../../GAPS.md) for implementation details.

---

## Tools Reference

### Mavent Tools

#### `check_mavent(loan_id: str)`
Runs Mavent compliance check.

**Returns**:
```python
{
    "passed": True/False,
    "has_fails": False,
    "has_alerts": False,
    "has_warnings": False,
    "total_issues": 0,
    "fails": [],
    "alerts": [],
    "warnings": [],
    "blocking": False  # True if any issues
}
```

#### `get_mavent_issues(loan_id: str)`
Gets detailed categorized issues.

**Returns**:
```python
{
    "fails": [
        {"code": "F-001", "description": "Missing DTI", "severity": "fail"}
    ],
    "alerts": [...],
    "warnings": [...]
}
```

### ATR/QM Tools

#### `check_atr_qm(loan_id: str)`
Checks all ATR/QM flags.

**Returns**:
```python
{
    "passed": True/False,
    "loan_features_flag": "GREEN",
    "points_and_fees_flag": "GREEN",
    "price_limit_flag": "GREEN",
    "red_flags": [],  # List of RED flags
    "yellow_flags": [],  # List of YELLOW flags
    "blocking": False  # True if red_flags
}
```

#### `get_points_and_fees_test(loan_id: str)`
Gets detailed Points & Fees test information.

**Returns**:
```python
{
    "test_result": "PASS",
    "total_points_and_fees": 5250.00,
    "loan_amount": 250000.00,
    "percentage": 2.1,
    "threshold": 3.0,
    "details": {...}
}
```

### Order Tools

#### `get_application_id(loan_id: str)`
Gets application ID from loan (required for eDisclosures).

**Returns**:
```python
{
    "application_id": "app-guid-123",
    "success": True
}
```

#### `audit_loan(loan_id: str)`
Runs mandatory audit before ordering.

**Returns**:
```python
{
    "success": True/False,
    "audit_snapshot_id": "audit-123",
    "issues": [],  # Any audit issues found
    "blocking": False  # True if unresolved issues
}
```

#### `order_disclosure_package(loan_id: str, dry_run: bool)`
Orders Initial Disclosure package via eDisclosures API.

**3-Step Process**:
1. Audit loan (get audit_snapshot_id)
2. Create document order (get doc_set_id)
3. Deliver to borrower (get tracking_id)

**Returns**:
```python
{
    "success": True/False,
    "tracking_id": "track-abc-123",
    "doc_set_id": "doc-xyz-456",
    "audit_snapshot_id": "audit-123",
    "delivery_status": "sent",
    "dry_run": True/False
}
```

---

## API Flow

The eDisclosures ordering follows this 3-step process:

### Step 1: Audit Loan
```
POST /encompassdocs/v1/documentAudits/opening
Body: {
    "entity": {"entityId": "{loanId}", "entityType": "urn:elli:encompass:loan"},
    "scope": {"entityId": "{applicationId}", "entityType": "urn:elli:encompass:loan:borrower"},
    "packageTypes": ["AtApp"]
}
Response: Location header → auditSnapshotId
```

### Step 2: Create Order
```
POST /encompassdocs/v1/documentOrders/opening
Body: {
    "auditId": "{auditSnapshotId}",
    "printMode": "LoanData"
}
Response: Location header → docSetId
```

### Step 3: Deliver Package
```
POST /encompassdocs/v1/documentOrders/opening/{docSetId}/delivery
Body: {
    "documents": [{"id": "{documentId}"}],
    "package": {
        "from": {"fullName": "...", "emailAddress": "...", "entityId": "{userName}", ...},
        "to": [{"id": "Borrower-{name}", "fullName": "...", "emailAddress": "...", ...}]
    }
}
Response: trackingId
```

---

## Blocking Conditions

The agent will set `status="blocked"` and NOT order disclosures if:

| Condition | Severity | Action |
|-----------|----------|--------|
| Mavent has ANY Fail | 🔴 Critical | Clear Mavent fails before sending |
| Mavent has ANY Alert | 🔴 Critical | Clear Mavent alerts before sending |
| Mavent has ANY Warning | 🔴 Critical | Clear Mavent warnings before sending |
| ATR/QM has RED flag | 🔴 Critical | Fix flag before sending |
| Audit has unresolved issues | 🔴 Critical | Resolve audit issues first |

---

## Usage

### Command Line

```bash
# Dry run (checks only, no ordering)
python agents/disclosure/subagents/send_agent/send_agent.py \
  --loan-id "your-loan-guid" \
  --dry-run

# Actually order disclosures
python agents/disclosure/subagents/send_agent/send_agent.py \
  --loan-id "your-loan-guid" \
  --order
```

### Python API

```python
from agents.disclosure.subagents.send_agent import run_disclosure_send

result = run_disclosure_send(
    loan_id="your-loan-guid",
    dry_run=True  # Set False to actually order
)

# Check status
print(result["status"])  # "success", "blocked", or "failed"

# Check Mavent
mavent = result["mavent_result"]
if not mavent["passed"]:
    print(f"Mavent issues: {mavent['total_issues']}")
    print(f"Fails: {mavent['fails']}")

# Check ATR/QM
atr_qm = result["atr_qm_result"]
if not atr_qm["passed"]:
    print(f"RED flags: {atr_qm['red_flags']}")

# Get tracking ID (if ordered)
if result["tracking_id"]:
    print(f"Tracking ID: {result['tracking_id']}")

# Check blocking issues
if result["blocking_issues"]:
    print("Disclosure blocked:")
    for issue in result["blocking_issues"]:
        print(f"  - {issue}")
```

---

## Output Structure

```python
{
    "loan_id": "...",
    "status": "success" | "blocked" | "failed",
    "dry_run": True/False,
    
    # Mavent compliance
    "mavent_result": {
        "passed": True/False,
        "has_fails": False,
        "has_alerts": False,
        "has_warnings": False,
        "total_issues": 0,
        "fails": [],
        "alerts": [],
        "warnings": []
    },
    
    # ATR/QM flags
    "atr_qm_result": {
        "passed": True/False,
        "loan_features_flag": "GREEN",
        "points_and_fees_flag": "GREEN",
        "price_limit_flag": "GREEN",
        "red_flags": [],
        "yellow_flags": []
    },
    
    # Order result (if ordered)
    "order_result": {
        "success": True/False,
        "tracking_id": "track-abc-123",
        "doc_set_id": "doc-xyz-456",
        "audit_snapshot_id": "audit-123"
    },
    
    # Tracking ID (convenience)
    "tracking_id": "track-abc-123",  # or None
    
    # Blocking issues
    "blocking_issues": [],  # or ["Mavent: 3 compliance issues", ...]
    
    "summary": "Send Complete (v2): ..."
}
```

---

## Safety Features

1. **Dry-Run Mode**: Default prevents actual ordering
2. **Mandatory Checks**: Mavent + ATR/QM must pass
3. **Blocking Logic**: Stops at first failure
4. **Audit Validation**: Pre-flight check before ordering
5. **Error Handling**: Graceful failures with detailed messages

---

## Configuration

Set in `.env`:

```env
ENCOMPASS_API_BASE_URL=https://concept.api.elliemae.com
ENCOMPASS_CLIENT_ID=your_client_id
ENCOMPASS_CLIENT_SECRET=your_secret
ENCOMPASS_INSTANCE_ID=your_instance_id
```

---

## Testing

```bash
# Run full orchestrator (includes send)
python agents/disclosure/test_orchestrator.py
```

---

## Performance

- **Execution Time**: 5-10 seconds
- **API Calls**: 4-6 (Mavent, ATR/QM, Audit, Order, Deliver)
- **Dry-Run**: ~3 seconds (checks only, no ordering)

---

## Integration

### Called By
- `orchestrator_agent.py` - Step 3 after preparation

### Receives From Preparation
- LE fully prepared with all fields populated
- RegZ-LE form updated
- MI calculated
- CTC matched

### Output
- `tracking_id`: For disclosure monitoring
- `blocking_issues`: List of issues that prevented sending
- Status: "success", "blocked", or "failed"

---

## Error Handling

### Mavent Failure
```
Mavent has 3 compliance issues
→ Review and clear all Fails/Alerts/Warnings in Encompass
→ Re-run disclosure agent after clearing
```

### ATR/QM Red Flag
```
ATR/QM has RED flag: Points and Fees
→ Review Points & Fees calculation in Encompass
→ Correct issue and re-run
```

### Audit Issues
```
Audit found unresolved issues
→ Resolve issues in Encompass
→ Re-run disclosure agent
```

### API Failure
```
eDisclosures API error
→ Check Encompass API status
→ Verify credentials and permissions
→ Retry if transient error
```

---

## File Structure

```
send_agent/
├── send_agent.py              # Main v2 agent
├── README.md                  # This file
├── __init__.py
└── tools/
    ├── mavent_tools.py        # Mavent compliance checks
    ├── atr_qm_tools.py        # ATR/QM flag checks
    ├── order_tools.py         # eDisclosures ordering + G16 audit filtering
    ├── audit_tools.py         # G16: Audit exception filtering
    └── review_tools.py        # G21: LO review workflow
```

---

## Next Steps for Phase 2

- Enhanced Mavent issue categorization
- Auto-remediation for common issues
- Advanced ATR/QM analysis
- Support for Revised LE (COC)
- Batch disclosure ordering
- Enhanced tracking and monitoring

---

## Audit Exception Filtering (G16)

The Send Agent includes intelligent audit exception filtering:

**Acceptable Exceptions** (do not block):
- Error 26.4 (Missing 1003 Signature - handled separately)
- HMDA-related alerts (informational only)
- Non-critical formatting warnings

**Blocking Exceptions**:
- Critical data errors
- Required field missing errors
- Compliance violations

This filter is automatically applied during the `audit_loan()` step to prevent false positives from blocking legitimate disclosures.

---

*Last updated: December 18, 2025 - v2 LE-focused with GAPS compliance tools*
