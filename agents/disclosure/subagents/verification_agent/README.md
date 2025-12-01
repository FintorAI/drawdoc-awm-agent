# Disclosure Verification Agent

## Overview

The Verification Agent is the first step in the Disclosure workflow. It checks if critical disclosure fields have values in Encompass and validates whether the loan is eligible for automated MVP processing.

**MVP Scope**: Conventional loans in NV/CA only  
**Current Status**: ✅ Implemented and tested

---

## What It Does

### 1. MVP Eligibility Check
- ✅ Checks if loan type is **Conventional**
- ✅ Checks if property state is **NV or CA**
- ⚠️ Flags non-MVP loans for manual processing

### 2. Critical Field Verification
- ✅ Checks **~20 critical fields** (not all CSV fields)
- ✅ Categorizes by: borrower, property, loan, contacts, dates
- ✅ Returns detailed status for each field

### 3. Output
- List of missing fields
- MVP warnings (if FHA/VA/USDA or non-NV/CA state)
- Field details for downstream agents

---

## Architecture

```
┌─────────────────────────────────────────┐
│ Verification Agent (LLM)                │
│                                          │
│ System Prompt:                           │
│ - Check MVP eligibility first            │
│ - Check critical fields                  │
│ - Report missing fields                  │
└────────────┬────────────────────────────┘
             │
             │ Uses 3 tools:
             │
             ├── check_mvp_eligibility()
             │   └── Reads loan type + state
             │       Validates against MVP criteria
             │
             ├── check_critical_fields()
             │   └── Batch reads ~20 fields
             │       Returns missing/present status
             │
             └── check_field_value()
                 └── Reads individual fields
                     For spot checking
```

---

## Critical Fields Checked (~20)

From `packages/shared/constants.py`:

**Borrower** (4 fields)
- 4000: Borrower First Name
- 4002: Borrower Last Name
- 65: Borrower SSN
- 1402: Borrower Email

**Property** (4 fields)
- 11: Property Street Address
- 12: Property City
- 14: Property State
- 15: Property Zip

**Loan** (6 fields)
- 1109: Loan Amount
- 3: Interest Rate
- 4: Loan Term
- 1172: Loan Type
- 19: Loan Purpose
- 353: LTV

**Property Value** (2 fields)
- 356: Appraised Value
- 136: Purchase Price

**Contacts** (2 fields)
- VEND.X263: Settlement Agent
- 411: Title Company

**Dates** (2 fields)
- CD1.X1: CD Date Issued
- 748: Estimated Closing Date

---

## Usage

### Command Line

```bash
# Run verification for a loan
python agents/disclosure/subagents/verification_agent/verification_agent.py \
  --loan-id "387596ee-7090-47ca-8385-206e22c9c9da"
```

### Python API

```python
from agents.disclosure.subagents.verification_agent.verification_agent import (
    run_disclosure_verification
)

result = run_disclosure_verification("387596ee-7090-47ca-8385-206e22c9c9da")

print(f"MVP Supported: {result['is_mvp_supported']}")
print(f"Loan Type: {result['loan_type']}")
print(f"State: {result['property_state']}")
print(f"Missing Fields: {len(result['fields_missing'])}")
```

### Output Structure

```python
{
    "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
    "status": "success",
    "is_mvp_supported": False,  # FHA loan
    "loan_type": "FHA",
    "property_state": "UT",
    "mvp_warnings": [
        "Non-MVP loan type: FHA. Only Conventional is fully supported.",
        "Non-MVP state: UT. Only NV and CA are fully supported."
    ],
    "fields_checked": 20,
    "fields_with_values": ["1109", "3", "4", "11", "12", ...],
    "fields_missing": ["CD1.X1", "VEND.X263"],
    "field_details": {...},
    "summary": "..."
}
```

---

## Testing

### Test All Fields Script

```bash
# Test reading all 12 loan summary fields
python agents/disclosure/subagents/verification_agent/test_all_fields.py
```

**What it does:**
- ✅ Checks Encompass credentials
- ✅ Tests batch read of all 12 fields
- ✅ Shows raw values from Encompass
- ✅ Diagnoses connection issues

**Example output:**
```
✓ 1172   (Loan Type)         = FHA
✓ 19     (Loan Purpose)      = Purchase
✓ 1109   (Loan Amount)       = 150,000.00
✓ 14     (Property State)    = UT
✓ 353    (LTV)               = 51.724
```

### Current Test Loan

**Loan ID**: `387596ee-7090-47ca-8385-206e22c9c9da`

**Details:**
- Loan Type: **FHA** (⚠️ Non-MVP)
- State: **UT** (⚠️ Non-MVP)
- Loan Amount: $150,000
- LTV: 51.724%
- Purpose: Purchase

**Expected Behavior:**
```python
is_mvp_supported = False
mvp_warnings = [
    "Non-MVP loan type: FHA",
    "Non-MVP state: UT"
]
```

The agent will process this loan but flag it for manual review since it's outside MVP scope.

---

## MVP Eligibility Rules

### Loan Types
```python
✓ Supported: Conventional
✗ Phase 2:   FHA, VA, USDA
```

### States
```python
✓ Supported: NV, CA
✗ Phase 2:   TX, FL, CO, IL, UT, AZ, WA, OR, ID, MI, etc.
```

### What Happens to Non-MVP Loans?

**Option 1: Continue with Warnings** (default)
- Agent processes the loan
- Flags warnings in email to LO
- Marks `requires_manual=True` in handoff

**Option 2: Skip Processing** (`skip_non_mvp=True`)
- Returns early with `status="manual_required"`
- No preparation or email sent
- Loan routed to manual processing queue

---

## Integration

### Called By
- `orchestrator_agent.py` - As first step in disclosure pipeline

### Calls
- `packages/shared/read_fields()` - Batch field reads
- `packages/shared/get_loan_summary()` - Loan metadata
- `packages/shared/LoanType.is_mvp_supported()` - MVP check
- `packages/shared/PropertyState.is_mvp_supported()` - State check

### Output Used By
- **Preparation Agent**: Uses `fields_missing` to know what to populate
- **Request Agent**: Includes MVP warnings in email to LO
- **Orchestrator**: Decides whether to continue or skip processing

---

## Error Handling

### 401 Authentication Error
```
⚠️ Invalid or expired Encompass credentials
Fix: Update .env with valid access token
```

### 404 Not Found Error
```
⚠️ Loan ID doesn't exist or not accessible
Fix: Verify loan ID is correct
```

### Missing Fields
```
ℹ️ Not an error - expected behavior
Action: Preparation agent will attempt to populate
```

### Non-MVP Loan
```
⚠️ Loan type or state not in MVP scope
Action: Flagged for manual processing or Phase 2
```

---

## File Structure

```
verification_agent/
├── verification_agent.py       # Main agent
├── test_all_fields.py         # Field testing script
├── README.md                  # This file
└── tools/
    └── field_check_tools.py   # Legacy tools (deprecated)
```

---

## Next Steps

1. **Get Conventional Test Loan** - Request from client for proper MVP testing
2. **Test with Real Data** - Once credentials are valid
3. **Integration Test** - Test with full orchestrator pipeline
4. **Phase 2** - Add FHA/VA/USDA support after MVP

---

## Configuration

Required environment variables (`.env` file):

```bash
ENCOMPASS_ACCESS_TOKEN=your_token
ENCOMPASS_CLIENT_ID=your_client_id
ENCOMPASS_CLIENT_SECRET=your_secret
ENCOMPASS_INSTANCE_ID=your_instance_id
```

---

## Performance

- **Fields checked**: 20 (vs 100+ in old version)
- **API calls**: 1 batch read (vs 20+ individual reads)
- **Execution time**: ~1-2 seconds (vs 5-10 seconds)
- **Cost**: Lower token usage, fewer API calls

---

## Notes

- MVP intentionally focuses on Conventional loans to ship faster
- FHA/VA/USDA support is Phase 2 (adds 1-2 weeks)
- Non-MVP loans are still processed but flagged for review
- State-specific rules (TX, FL, etc.) are Phase 2

