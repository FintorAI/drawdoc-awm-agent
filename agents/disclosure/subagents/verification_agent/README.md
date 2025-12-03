# Disclosure Verification Agent (v2)

**Version**: 2.0 (LE-focused)  
**Last Updated**: December 3, 2025  

[🔙 Back to Main Disclosure README](../../README.md)

---

## Overview

The Verification Agent is the first step in the Disclosure v2 workflow. It validates prerequisites for **Initial Loan Estimate (LE)** disclosure, ensuring TRID compliance, form completeness, and MVP eligibility before proceeding to preparation.

**Purpose**: Gate-check to ensure loan is ready for LE disclosure preparation.

---

## v2 Key Features

### 1. TRID Compliance (NEW) ✅
- **3-Business-Day Rule**: LE must be sent within 3 business days of application
- **Application Date Check**: Validates app date is set
- **LE Due Date Calculation**: Excludes Sundays and federal holidays
- **Days Remaining**: Reports how many days until LE due
- **Past Due Escalation**: Flags loans past LE due date for supervisor

**Blocking**: LE due date passed → Escalate to Supervisor

### 2. Hard Stops - G1 (NEW) ✅
- **Phone Number**: Field FE0117 must have value
- **Email Address**: Field 1240 must have value
- **Impact**: Missing either field BLOCKS disclosure entirely

**Blocking**: Missing phone or email → HARD STOP

### 3. Closing Date 15-Day Rule - G8 (NEW) ✅
- **Non-Locked Loans**: Closing date ≥ 15 days from application date
- **Locked Loans**: Closing date ≥ 15 days from last rate set date
- **Field**: 748 (Estimated Closing Date)

**Blocking**: Closing date < 15 days → Cannot proceed

### 4. Lock Status Check (NEW) ✅
- **Locked Flow**: Requires all TRID info updated (property address, DTI, appraised value)
- **Non-Locked Flow**: Monitors app date & LE due date
- **Impact**: Determines which validation rules apply

### 5. Form Field Validation (EXPANDED) ✅
Validates SOP-required forms:
- 1003 URLA Lender Form (all 4 parts)
- Borrower Summary Origination
- FACT Act Disclosure (credit scores)
- RegZ-LE fields
- Affiliated Business Arrangements
- LO Info (NMLS verification)

### 6. MVP Eligibility Check ✅
- **Loan Type**: Conventional only (FHA/VA/USDA require manual)
- **State**: NOT Texas (TX has special rules)
- **Preferred States**: NV, CA (others may work but not tested)

**Blocking**: Texas property or Non-Conventional → Manual processing required

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│              VERIFICATION AGENT (v2)                        │
│                                                             │
│  Step 1: TRID Compliance                                    │
│  ├── check_trid_dates()          → 3-day rule             │
│  ├── check_rate_lock_status()    → Locked/non-locked      │
│  └── check_closing_date_rule()   → 15-day rule (G8)       │
│                                                             │
│  Step 2: Hard Stops                                         │
│  └── check_hard_stops()          → Phone/Email (G1)       │
│                                                             │
│  Step 3: MVP Eligibility                                    │
│  └── check_mvp_eligibility()     → Conventional, not TX   │
│                                                             │
│  Step 4: Form Validation                                    │
│  └── validate_disclosure_form_fields() → 15+ forms        │
│                                                             │
│  Step 5: Critical Fields                                    │
│  └── check_critical_fields()     → ~20 key fields         │
│                                                             │
│  Output: Blocking issues (if any) + field status           │
└────────────────────────────────────────────────────────────┘
```

---

## Tools

### TRID Tools

#### `check_trid_dates(loan_id: str)`
Validates TRID compliance for Initial LE.

**Returns**:
```python
{
    "compliant": True/False,
    "application_date": "2025-12-01",
    "le_due_date": "2025-12-04",
    "days_remaining": 1,
    "is_past_due": False,
    "action": "Proceed" or "Escalate to Supervisor",
    "blocking": True if past due
}
```

#### `check_rate_lock_status(loan_id: str)`
Determines locked vs non-locked flow.

**Returns**:
```python
{
    "is_locked": True/False,
    "lock_date": "2025-11-28",
    "lock_expiration": "2025-12-28",
    "flow": "locked" or "non_locked"
}
```

#### `check_closing_date_rule(loan_id: str)`
Validates 15-day closing date rule (G8).

**Returns**:
```python
{
    "is_valid": True/False,
    "closing_date": "2025-12-20",
    "reference_date": "2025-12-01",  # App date or rate set date
    "days_until_closing": 19,
    "minimum_days": 15,
    "blocking": True if < 15 days,
    "action": "Proceed" or "Adjust closing date"
}
```

### Hard Stop Tools

#### `check_hard_stops(loan_id: str)`
Validates critical phone and email fields (G1).

**Returns**:
```python
{
    "has_hard_stops": True/False,
    "missing_fields": ["borrower_phone"],  # or []
    "blocking": True if has_hard_stops,
    "blocking_message": "HARD STOP: Missing phone number"
}
```

### Form Validation Tools

#### `validate_disclosure_form_fields(loan_id: str)`
Validates all required disclosure forms.

**Returns**:
```python
{
    "all_valid": True/False,
    "forms_checked": 8,
    "forms_passed": 7,
    "missing_critical": ["FACT_Act_credit_score"],
    "missing_fields": [...],
    "blocking": True if missing_critical
}
```

### MVP Eligibility Tools

#### `check_mvp_eligibility(loan_id: str)`
Checks if loan qualifies for MVP processing.

**Returns**:
```python
{
    "is_eligible": True/False,
    "loan_type": "Conventional",
    "is_mvp_loan_type": True,
    "property_state": "CA",
    "is_mvp_state": True,
    "ineligibility_reasons": [],  # or ["Non-Conventional", "Texas property"]
    "action": "proceed" or "manual_processing_required"
}
```

### Field Check Tools

#### `check_critical_fields(loan_id: str)`
Batch checks ~20 critical LE fields.

**Returns**:
```python
{
    "fields_checked": 20,
    "fields_with_values": ["1109", "3", "4", ...],
    "fields_missing": ["LE1.X1"],
    "field_details": {
        "1109": {"name": "Loan Amount", "has_value": True, "value": 250000.00}
    }
}
```

---

## Blocking Conditions

The agent will set `status="blocked"` and stop the workflow if:

| Condition | Severity | Action |
|-----------|----------|--------|
| LE due date passed | 🔴 Critical | Escalate to Supervisor |
| Application date not set | 🔴 Critical | Cannot proceed |
| Missing phone number | 🔴 Critical | HARD STOP - cannot proceed |
| Missing email address | 🔴 Critical | HARD STOP - cannot proceed |
| Closing date < 15 days | 🔴 Critical | Adjust closing date |
| Texas property | 🟡 Medium | Manual processing required |
| Non-Conventional loan | 🟡 Medium | Manual processing required |
| Critical form fields missing | 🟡 Medium | Flag for review |

---

## Usage

### Command Line

```bash
# Run verification agent
python agents/disclosure/subagents/verification_agent/verification_agent.py \
  --loan-id "your-loan-guid"
```

### Python API

```python
from agents.disclosure.subagents.verification_agent import run_disclosure_verification

result = run_disclosure_verification("your-loan-guid")

# Check status
print(result["status"])  # "success", "blocked", or "failed"

# Check TRID compliance
trid = result["trid_compliance"]
print(f"Days until LE due: {trid['days_remaining']}")
print(f"Past due: {trid['is_past_due']}")

# Check hard stops
hard_stops = result["hard_stop_check"]
if hard_stops["has_hard_stops"]:
    print(f"HARD STOP: Missing {hard_stops['missing_fields']}")

# Check closing date
closing = result["closing_date_check"]
if not closing["is_valid"]:
    print(f"Closing date too soon: {closing['days_until_closing']} days")

# Check blocking issues
if result["blocking_issues"]:
    print("Blocking issues:")
    for issue in result["blocking_issues"]:
        print(f"  - {issue}")
```

---

## Output Structure

```python
{
    "loan_id": "...",
    "status": "success" | "blocked" | "failed",
    "is_mvp_supported": True/False,
    
    # v2: TRID compliance
    "trid_compliance": {
        "compliant": True,
        "application_date": "2025-12-01",
        "le_due_date": "2025-12-04",
        "days_remaining": 1,
        "is_past_due": False
    },
    
    # v2: Hard stops (G1)
    "hard_stop_check": {
        "has_hard_stops": False,
        "missing_fields": []
    },
    
    # v2: Closing date (G8)
    "closing_date_check": {
        "is_valid": True,
        "days_until_closing": 20
    },
    
    # v2: Lock status
    "lock_status": {
        "is_locked": False,
        "flow": "non_locked"
    },
    
    # v2: Form validation
    "form_validation": {
        "all_valid": True,
        "forms_checked": 8,
        "missing_critical": []
    },
    
    # Original field checks
    "fields_checked": 20,
    "fields_with_values": [...],
    "fields_missing": [...],
    "field_details": {...},
    
    # Loan info
    "loan_type": "Conventional",
    "property_state": "CA",
    
    # Blocking issues
    "blocking_issues": [],  # List of strings if blocked
    
    "summary": "Verification Complete (v2 - LE Focus): ..."
}
```

---

## Testing

### Test All Fields Script

```bash
# Test field reading and credential validation
python agents/disclosure/subagents/verification_agent/test_all_fields.py
```

This script:
- Validates Encompass credentials
- Tests batch field reading
- Shows raw field values
- Diagnoses connection issues

### Integration Test

```bash
# Run full orchestrator (includes verification)
python agents/disclosure/test_orchestrator.py
```

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

## Error Handling

### Authentication Error (401)
```
Invalid or expired Encompass credentials
→ Update .env with valid credentials
```

### Loan Not Found (404)
```
Loan ID doesn't exist or not accessible
→ Verify loan GUID is correct
```

### TRID Compliance Failure
```
LE Due Date passed
→ Escalate to Supervisor (cannot auto-process)
```

### Hard Stop
```
Missing phone or email
→ Request from borrower before proceeding
```

### Closing Date Invalid
```
Closing date < 15 days from app/lock date
→ Adjust closing date to meet 15-day requirement
```

### Non-MVP Loan
```
Loan type is FHA/VA/USDA or property is in Texas
→ Route to manual processing
```

---

## Performance

- **Execution Time**: ~3-5 seconds
- **API Calls**: 2-4 (batch reads where possible)
- **Fields Checked**: ~20 critical fields
- **TRID Calculation**: < 1 second

---

## Integration

### Called By
- `orchestrator_agent.py` - Step 1 after pre-check

### Calls
- `packages/shared/check_trid_compliance()`
- `packages/shared/check_lock_status()`
- `packages/shared/check_closing_date()`
- `packages/shared/check_hard_stop_fields()`
- `packages/shared/validate_disclosure_forms()`
- `packages/shared/read_fields()`

### Output Used By
- **Preparation Agent**: Uses `fields_missing` to populate
- **Orchestrator**: Uses `blocking_issues` to halt if needed
- **Send Agent**: Receives prepared loan data

---

## File Structure

```
verification_agent/
├── verification_agent.py       # Main v2 agent
├── test_all_fields.py         # Field testing utility
├── README.md                  # This file
├── __init__.py
└── tools/
    └── (tools are inline in verification_agent.py)
```

---

## Next Steps for Phase 2

- FHA/VA/USDA loan type support
- Texas state-specific rules
- Additional state validations
- Enhanced form field checks
- Automated credit report validation

---

*Last updated: December 3, 2025 - v2 LE-focused implementation*
