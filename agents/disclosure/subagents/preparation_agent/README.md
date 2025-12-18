# Disclosure Preparation Agent (v2)

**Version**: 2.0 (LE-focused with 8 GAPS implementations)  
**Last Updated**: December 18, 2025  
**Status**: ✅ Implemented and tested with GAPS tools

[🔙 Back to Main Disclosure README](../../README.md)

---

## Overview

The **Preparation Agent** is the second agent in the Disclosure v2 workflow. It prepares the **Loan Estimate (LE)** for disclosure by updating RegZ-LE form fields per SOP, calculating Mortgage Insurance, matching Cash to Close, and populating missing LE fields using AI-based derivation.

**Purpose**: Ensure LE form is complete, accurate, and compliant before sending.

**Position in Workflow**: Verification Agent (v2) → **Preparation Agent (v2)** → Send Agent (v2)

---

## v2 Key Features

### 1. RegZ-LE Form Updates (NEW) ✅
Updates RegZ-LE form fields per Disclosure Desk SOP:
- **LE Date Issued**: Current date
- **Interest Accrual**: 360/360 (days per year)
- **Late Charge**: Days and percent based on loan type
- **Assumption Clause**: Text based on loan type
- **Buydown Fields**: If buydown is marked
- **Prepayment Penalty**: If applicable

### 2. Cash to Close Matching (NEW) ✅
Sets checkboxes for CTC calculation:
- **Purchase Loans**: `use_actual_down_payment`, `closing_costs_financed`, `include_payoffs_in_adjustments`
- **Refinance Loans**: `alternative_form_checkbox`
- **Verification**: Compares calculated vs displayed CTC

### 3. Mortgage Insurance Calculation ✅
Calculates MI for Conventional loans (LTV > 80%):
- **Monthly MI Amount**: Based on LTV and loan amount
- **Cancel at LTV**: 78% (standard)
- **Source**: MI Certificate or calculated estimate

**MVP**: Conventional only. FHA/VA/USDA in Phase 2.

### 4. LE Field Population ✅
AI-based field derivation for missing LE fields:
- Searches related Encompass fields
- Intelligently selects best values
- Normalizes field formats
- Writes to LE fields (dry_run mode for safety)

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│              PREPARATION AGENT (v2)                         │
│                                                             │
│  Step 1: RegZ-LE Form Updates (NEW in v2)                  │
│  ├── update_regz_le_fields()    → LE Date, Interest, etc  │
│  ├── get_late_charge_values()   → Per loan type           │
│  └── get_assumption_clause()    → Per loan type           │
│                                                             │
│  Step 2: Mortgage Insurance                                 │
│  ├── check_mi_required()        → LTV > 80%?              │
│  ├── calculate_loan_mi()        → Monthly amount          │
│  └── populate_mi_fields()       → Write to LE             │
│                                                             │
│  Step 3: Cash to Close (NEW in v2)                         │
│  ├── match_ctc()                → Set checkboxes           │
│  ├── get_ctc_checkbox_settings()→ Purchase vs Refi        │
│  └── verify_ctc_match()         → Calc vs Displayed       │
│                                                             │
│  Step 4: LE Field Population                                │
│  ├── get_le_field_status()      → Check what's missing    │
│  ├── search_loan_fields()       → Find related fields     │
│  ├── get_loan_field_value()     → Read candidates         │
│  └── write_field_value()        → Populate (dry_run)      │
│                                                             │
│  Output: Updated LE ready for compliance checks            │
└────────────────────────────────────────────────────────────┘
```

---

## GAPS Implementations

This agent implements 8 GAPS from the Disclosure Desk SOP:

| Gap | Name | Status | Tool Module |
|-----|------|--------|-------------|
| G3 | Home Counseling | 🚧 API Pending | `counseling_tools.py` |
| G4 | Transcript Forms | ✅ Full API | `transcript_tools.py` |
| G5 | 2015 Itemization | 🚧 Partial | `itemization_tools.py` |
| G6 | SSPL Management | 🚧 Partial | `sspl_tools.py` |
| G7 | ABA Template | 🚧 Manual | `template_tools.py` |
| G18 | RegZ-LE Fields | 🚧 Partial | `regz_le_tools.py` |
| G19 | Blend ORGID | ✅ Read-only | `blend_tools.py` |
| G20 | eFolder Products | 🚧 Partial | `efolder_tools.py` |

**Legend**: ✅ Full = Complete implementation | 🚧 Partial = Some fields UNKNOWN or manual steps required

**G4 Highlight**: Transcript Forms API fully eliminates need for ~20 field ID mappings

See [`GAPS.md`](../../GAPS.md) for detailed implementation notes.

---

## Tools Reference

### RegZ-LE Tools (NEW in v2)

#### `update_regz_le_fields(loan_id: str, dry_run: bool)`
Updates RegZ-LE form fields per SOP.

**Updates Made**:
- `LE1.X1`: LE Date Issued = Current Date
- Interest Accrual Options = 360/360
- Late Charge Days (15 for Conventional/FHA/VA, varies by state)
- Late Charge Percent (5% Conventional, 4% FHA/VA, 4% NC)
- Assumption: "may not" (Conv) or "may, subject to conditions" (FHA/VA)
- Buydown fields (if marked)
- Prepayment penalty fields (if applicable)

**Returns**:
```python
{
    "success": True/False,
    "updates_made": {
        "LE1.X1": "2025-12-03",
        "672": 15,  # Late Charge Days
        "674": 5.0  # Late Charge Percent
    },
    "errors": []
}
```

#### `get_late_charge_values(loan_id: str)`
Gets late charge days and percent for loan type.

**Returns**:
```python
{
    "days": 15,
    "percent": 5.0,
    "loan_type": "Conventional"
}
```

#### `get_assumption_clause(loan_id: str)`
Gets assumption clause text for loan type.

**Returns**:
```python
{
    "assumption_text": "may not",
    "loan_type": "Conventional"
}
```

### Cash to Close Tools (NEW in v2)

#### `match_ctc(loan_id: str, dry_run: bool)`
Sets CTC checkboxes based on loan purpose.

**Returns**:
```python
{
    "matched": True/False,
    "loan_purpose": "Purchase",
    "checkboxes_set": [
        "use_actual_down_payment",
        "closing_costs_financed",
        "include_payoffs_in_adjustments"
    ],
    "calculated_ctc": 50000.00,
    "displayed_ctc": 50000.00,
    "difference": 0.00
}
```

#### `get_ctc_checkbox_settings(loan_purpose: str)`
Gets which checkboxes to set for Purchase vs Refinance.

**Returns**:
```python
{
    "checkboxes": ["use_actual_down_payment", ...],
    "loan_purpose": "Purchase"
}
```

#### `verify_ctc_match(loan_id: str)`
Verifies calculated CTC matches displayed CTC.

**Returns**:
```python
{
    "matched": True/False,
    "calculated_ctc": 50000.00,
    "displayed_ctc": 50000.00,
    "difference": 0.00,
    "tolerance": 0.01
}
```

### MI Calculation Tools

#### `calculate_loan_mi(loan_id: str)`
Calculates Mortgage Insurance based on loan type and LTV.

**MVP**: Conventional only (LTV > 80%)

**Returns**:
```python
{
    "requires_mi": True/False,
    "loan_type": "Conventional",
    "ltv": 85.0,
    "monthly_amount": 125.50,
    "upfront_amount": 0.0,
    "annual_rate": 0.0055,
    "cancel_at_ltv": 78.0,
    "source": "mi_cert" or "calculated"
}
```

#### `check_mi_required(loan_id: str)`
Quick check if MI is required (LTV > 80%).

**Returns**:
```python
{
    "requires_mi": True/False,
    "ltv": 85.0,
    "loan_type": "Conventional"
}
```

#### `populate_mi_fields(loan_id: str, mi_data: dict, dry_run: bool)`
Writes MI values to LE fields.

**Returns**:
```python
{
    "success": True/False,
    "fields_written": ["232", "MI.X1", ...],
    "dry_run": True/False
}
```

### LE Field Tools

#### `get_le_field_status(loan_id: str)`
Checks which LE fields are populated vs missing.

**Returns**:
```python
{
    "fields_checked": 13,
    "populated_count": 11,
    "missing_count": 2,
    "populated_fields": ["1109", "3", "4", ...],
    "missing_fields": ["LE1.X1", "LE1.X77"],
    "field_status": {...}
}
```

### Field Derivation Tools

#### `search_loan_fields(loan_id: str, search_term: str)`
Searches all Encompass fields for a term, returns matching fields with values.

**Example**:
```python
result = search_loan_fields(loan_id, "email")
# Returns: {"1240": "john@email.com", "1402": "john@email.com"}
```

#### `get_loan_field_value(loan_id: str, field_id: str)`
Reads a single field value.

**Returns**:
```python
{
    "field_id": "1240",
    "value": "john@email.com",
    "has_value": True
}
```

#### `get_multiple_field_values(loan_id: str, field_ids: list)`
Batch reads multiple fields (efficient).

**Returns**:
```python
{
    "field_values": {
        "1109": 250000.00,
        "3": 6.5,
        "4": 360
    }
}
```

#### `write_field_value(loan_id: str, field_id: str, value: any, dry_run: bool)`
Writes a value to an LE field.

**MVP**: Always use `dry_run=True` for safety.

**Returns**:
```python
{
    "field_id": "LE1.X1",
    "value": "2025-12-03",
    "success": True,
    "dry_run": True,
    "message": "Would write: LE1.X1 = 2025-12-03"
}
```

### Normalization Tools

#### `normalize_phone_number(phone: str)`
Standardizes phone numbers to `(XXX) XXX-XXXX` or `XXXXXXXXXX`.

#### `normalize_date(date: str)`
Converts dates to ISO format `YYYY-MM-DD`.

#### `normalize_ssn(ssn: str)`
Removes SSN formatting to `XXXXXXXXX`.

#### `normalize_currency(amount: str)`
Converts currency strings to floats: `"$1,234.56"` → `1234.56`.

#### `normalize_address(address: str)`
Standardizes street addresses.

#### `clean_field_value(value: str)`
General cleanup (trim whitespace, remove nulls).

---

## Workflow

```
INPUT: loan_id, missing_fields, demo_mode
  ↓
STEP 1: RegZ-LE Form Updates
  ├── Set LE Date Issued = Today
  ├── Set Interest Accrual = 360/360
  ├── Set Late Charge per loan type
  └── Set Assumption clause per loan type
  ↓
STEP 2: Mortgage Insurance
  ├── Check if LTV > 80%
  ├── Calculate monthly MI (if needed)
  └── Populate MI fields (dry_run)
  ↓
STEP 3: Cash to Close
  ├── Determine Purchase vs Refinance
  ├── Set appropriate checkboxes
  └── Verify calculated vs displayed CTC
  ↓
STEP 4: LE Field Population
  ├── Get missing field list
  ├── For each missing field:
  │   ├── Search related fields
  │   ├── Select best value
  │   ├── Normalize format
  │   └── Write to LE (dry_run)
  ↓
OUTPUT: {regz_le_result, mi_result, ctc_result, fields_populated}
```

---

## Usage

### Command Line

```bash
# Basic usage (demo mode - safe)
python agents/disclosure/subagents/preparation_agent/preparation_agent.py \
  --loan-id "your-loan-guid" \
  --demo

# With specific missing fields
python agents/disclosure/subagents/preparation_agent/preparation_agent.py \
  --loan-id "your-loan-guid" \
  --missing-fields "LE1.X1,LE1.X77,232" \
  --demo
```

### Python API

```python
from agents.disclosure.subagents.preparation_agent import run_disclosure_preparation

result = run_disclosure_preparation(
    loan_id="your-loan-guid",
    missing_fields=["LE1.X1", "LE1.X77"],
    fields_to_clean=[],
    demo_mode=True  # Safe mode - no actual writes
)

# Check RegZ-LE updates
regz = result["regz_le_result"]
print(f"RegZ-LE updates: {len(regz['updates_made'])} fields")

# Check MI calculation
mi = result["mi_result"]
if mi["requires_mi"]:
    print(f"Monthly MI: ${mi['monthly_amount']:.2f}")

# Check CTC match
ctc = result["ctc_result"]
print(f"CTC Matched: {ctc['matched']}")

# Check fields populated
print(f"Fields populated: {len(result['fields_populated'])}")
```

---

## Output Structure

```python
{
    "loan_id": "...",
    "status": "success" | "failed",
    "demo_mode": True/False,
    
    # v2: RegZ-LE updates
    "regz_le_result": {
        "success": True,
        "updates_made": {
            "LE1.X1": "2025-12-03",
            "672": 15,
            "674": 5.0
        }
    },
    
    # v2: Cash to Close
    "ctc_result": {
        "matched": True,
        "calculated_ctc": 50000.00,
        "displayed_ctc": 50000.00
    },
    
    # MI calculation
    "mi_result": {
        "requires_mi": True,
        "monthly_amount": 125.50,
        "cancel_at_ltv": 78.0
    },
    
    # Field population
    "fields_populated": ["LE1.X1", "232"],
    "fields_failed": [],
    
    "actions": [
        {"action": "regz_le_update", "result": {...}},
        {"action": "mi_calculation", "result": {...}},
        {"action": "ctc_match", "result": {...}},
        {"action": "populate", "field_id": "LE1.X1", "dry_run": True}
    ],
    
    "summary": "Preparation Complete (v2 - LE Focus): ..."
}
```

---

## MVP Scope

### ✅ Included
- RegZ-LE form updates (per SOP)
- Conventional MI calculation (LTV > 80%)
- Cash to Close matching (Purchase vs Refi)
- LE field population (AI-based)
- Field normalization (phone, date, SSN, currency)
- Safety: Dry-run mode by default

### 🔴 Phase 2
- FHA/VA/USDA MI calculations (complex upfront + monthly)
- Full 2015 Itemization updates (all sections)
- Auto-cure fee tolerance violations
- Advanced field validation
- Cross-field consistency checks

---

## Safety Features

1. **Dry-Run Mode**: Default `demo_mode=True` prevents actual writes
2. **Field Validation**: Checks field types before writing
3. **Value Normalization**: Ensures proper formatting
4. **Error Handling**: Graceful fallback if derivation fails
5. **Audit Trail**: Logs all actions taken

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
# Run full orchestrator (includes preparation)
python agents/disclosure/test_orchestrator.py
```

---

## Performance

- **Execution Time**: 5-15 seconds (depends on missing fields)
- **API Calls**: 3-10 to Encompass (batch reads where possible)
- **AI Token Usage**: ~500-2000 tokens per loan

---

## Integration

### Called By
- `orchestrator_agent.py` - Step 2 after verification

### Receives From Verification
- `fields_missing`: List of field IDs to populate
- `loan_type`: For RegZ-LE and MI calculations
- `is_mvp_supported`: For flow control

### Passes To Send Agent
- `regz_le_result`: Form updates made
- `mi_result`: MI calculation
- `ctc_result`: CTC match status
- `fields_populated`: Successfully populated fields

---

## File Structure

```
preparation_agent/
├── preparation_agent.py           # Main v2 agent
├── README.md                      # This file
├── __init__.py
└── tools/
    ├── regz_le_tools.py          # RegZ-LE updates (v2) + G18
    ├── ctc_tools.py              # CTC matching (v2)
    ├── mi_tools.py               # MI calculation
    ├── field_derivation_tools.py # AI field population
    ├── field_normalization_tools.py # Value formatting
    ├── transcript_tools.py       # G4: Transcript Forms API
    ├── counseling_tools.py       # G3: Home Counseling
    ├── itemization_tools.py      # G5: 2015 Itemization
    ├── sspl_tools.py             # G6: SSPL Management
    ├── template_tools.py         # G7: ABA Template
    ├── blend_tools.py            # G19: Blend ORGID
    └── efolder_tools.py          # G20: eFolder Products
```

---

## Next Steps for Phase 2

- FHA MIP calculation (upfront + monthly)
- VA funding fee calculation
- USDA guarantee fee calculation
- Full 2015 Itemization updates (all sections)
- Advanced CTC reconciliation
- Auto-cure tolerance violations

---

## API Integrations

### Encompass Transcript Forms API (G4) ✅
- **Endpoint**: Encompass Developer Connect v3 API
- **Methods**: 
  - `GET /v3/settings/templates/transcriptRequests` - List templates
  - `PATCH /v3/loans/{loanId}` - Apply template
  - `PATCH /v3/loans/{loanId}/applications/{applicationId}/transcriptRequests` - Manage records
- **Benefits**: Eliminates need for ~20+ field ID mappings
- **Status**: Ready for production use

### HUD Housing Counseling API (G3) ⏳
- **Status**: API endpoint TBD
- **Current**: Manual agency selection with logging
- **Future**: Auto-populate agencies via HUD API

---

*Last updated: December 18, 2025 - v2 LE-focused with complete GAPS implementations*
