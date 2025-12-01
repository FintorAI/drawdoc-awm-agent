# Disclosure Preparation Agent

## Overview

The **Preparation Agent** is the second agent in the Disclosure workflow. It prepares the Closing Disclosure (CD) by calculating Mortgage Insurance, checking fee tolerance violations, and populating missing fields using AI-based field derivation.

**Position in Workflow**: Verification Agent → **Preparation Agent** → Request Agent

**MVP Scope**: Conventional loans only, fee tolerance flagging (no auto-cure), basic CD fields (pages 1-3)

---

## What It Does

The Preparation Agent has **3 core responsibilities**:

### 1. 💰 Calculate Mortgage Insurance (MI)

```
- Checks if MI is required (LTV > 80%)
- Calculates monthly MI amounts
- Determines cancellation date
- Populates MI fields on CD

MVP: Conventional loans only
Phase 2: FHA, VA, USDA
```

### 2. 📊 Check Fee Tolerance

```
- Compares Last LE vs Current CD fees
- Identifies 0% tolerance violations (Section A)
- Identifies 10% tolerance violations (Section B)
- Flags violations for manual review

MVP: Flag violations only
Phase 2: Auto-cure violations
```

### 3. 📝 Populate Missing CD Fields

```
- AI-based field derivation
- Searches related Encompass fields
- Intelligently selects best values
- Normalizes field formats

MVP: Basic CD fields (pages 1-3)
Phase 2: All CD pages
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Preparation Agent (AI - Claude)                             │
│                                                              │
│ System Prompt:                                               │
│ - Calculate MI for Conventional loans                       │
│ - Check fee tolerance (flag only)                           │
│ - Populate missing CD fields using AI derivation            │
│ - Normalize field values                                    │
└────────────┬────────────────────────────────────────────────┘
             │
             │ Has 13 tools in 4 categories:
             │
             ├── MI Tools (3)
             │   ├── calculate_loan_mi()
             │   ├── check_mi_required()
             │   └── populate_mi_fields()
             │
             ├── Fee Tolerance Tools (2)
             │   ├── check_loan_fee_tolerance()
             │   └── get_cd_field_status()
             │
             ├── Field Derivation Tools (4)
             │   ├── get_loan_field_value()
             │   ├── get_multiple_field_values()
             │   ├── search_loan_fields()
             │   └── write_field_value()
             │
             └── Normalization Tools (6)
                 ├── clean_field_value()
                 ├── normalize_phone_number()
                 ├── normalize_date()
                 ├── normalize_ssn()
                 ├── normalize_currency()
                 └── normalize_address()
```

---

## Tools Reference

### MI Calculation Tools

Located in `tools/mi_tools.py`

#### `calculate_loan_mi(loan_id: str)`
Calculates Mortgage Insurance based on loan type, LTV, and loan amount.

**Returns:**
```python
{
    "requires_mi": True/False,
    "loan_type": "Conventional",
    "ltv": 98.865,
    "monthly_amount": 450.25,
    "upfront_amount": 0.0,
    "annual_rate": 0.0055,
    "cancel_at_ltv": 78.0,
    "source": "mi_cert" or "calculated"
}
```

**MVP:** Conventional only (LTV > 80%)  
**Phase 2:** FHA (UFMIP + monthly MIP), VA (funding fee), USDA

---

#### `check_mi_required(loan_id: str)`
Quick check if MI is required (LTV > 80%).

**Returns:**
```python
{
    "requires_mi": True,
    "ltv": 98.865,
    "loan_type": "Conventional"
}
```

---

#### `populate_mi_fields(loan_id: str, mi_data: dict, dry_run: bool)`
Writes MI values to CD fields.

**Fields populated:**
- Monthly MI amount
- Upfront MI (if applicable)
- MI cancellation date
- MI renewal terms

**MVP:** `dry_run=True` (safety mode)

---

### Fee Tolerance Tools

Built into `preparation_agent.py`

#### `check_loan_fee_tolerance(loan_id: str)`
Compares LE vs CD fees to identify tolerance violations.

**Returns:**
```python
{
    "has_violations": True,
    "total_cure_needed": 150.00,
    "violations": [
        {
            "section": "A",
            "fee_name": "Origination Fee",
            "le_amount": 1500.00,
            "cd_amount": 1600.00,
            "increase": 100.00,
            "tolerance": "0%",
            "violation_amount": 100.00
        }
    ],
    "summary": "Found 1 violation(s): Section A +$100"
}
```

**Tolerance Rules:**
- **0% tolerance** (Section A): Origination, discount points → Cannot increase
- **10% tolerance** (Section B): Appraisal, credit report, etc. → Aggregate 10% max
- **No tolerance** (Section C): Borrower-shopped services → Can change freely

**MVP:** Flags only (no auto-cure)  
**Phase 2:** Auto-apply lender credits to cure violations

---

#### `get_cd_field_status(loan_id: str)`
Checks which CD fields are populated vs missing.

**Returns:**
```python
{
    "total_fields": 50,
    "populated": 45,
    "missing": ["CD.BORROWER_EMAIL", "CD.SETTLEMENT_AGENT", ...]
}
```

---

### Field Derivation Tools

Located in `tools/field_derivation_tools.py`

These tools enable AI-based field population by searching and reading related Encompass fields.

#### `search_loan_fields(loan_id: str, search_term: str)`
Searches all Encompass fields for a term, returns matching fields with values.

**Example:**
```python
# Agent needs email, searches for "email"
result = search_loan_fields(loan_id, "email")

# Returns:
{
    "search_term": "email",
    "matches": {
        "4002": "john.doe@email.com",      # Borrower Email
        "1402": "john.doe@email.com",      # Contact Email
        "LENDER.X15": ""                   # Empty
    },
    "match_count": 2
}

# AI reasons: "Both have same email, I'll use this value"
```

**Use case:** Finding related fields when target field is missing

---

#### `get_loan_field_value(loan_id: str, field_id: str)`
Reads a single field value from Encompass.

**Returns:**
```python
{
    "field_id": "4002",
    "value": "john.doe@email.com",
    "has_value": True,
    "success": True
}
```

---

#### `get_multiple_field_values(loan_id: str, field_ids: list)`
Batch reads multiple fields in one call (efficient).

**Returns:**
```python
{
    "field_values": {
        "4000": "John",
        "4001": "Doe",
        "65": "555-1234"
    },
    "success": True
}
```

---

#### `write_field_value(loan_id: str, field_id: str, value: any, dry_run: bool)`
Writes a value to an Encompass field.

**MVP:** Always use `dry_run=True` for safety

**Returns:**
```python
{
    "field_id": "CD.EMAIL",
    "value": "john.doe@email.com",
    "success": True,
    "dry_run": True,
    "message": "Would write: CD.EMAIL = john.doe@email.com"
}
```

---

### Field Normalization Tools

Located in `tools/field_normalization_tools.py`

#### `clean_field_value(value: str)`
General cleanup (trim whitespace, remove nulls, etc.)

```python
clean_field_value("  John Doe  ") → "John Doe"
```

---

#### `normalize_phone_number(phone: str)`
Standardizes phone numbers.

```python
normalize_phone_number("(702) 123-4567") → "7021234567"
normalize_phone_number("702-123-4567")   → "7021234567"
```

---

#### `normalize_date(date: str)`
Converts dates to ISO format.

```python
normalize_date("12/25/2024")    → "2024-12-25"
normalize_date("Dec 25, 2024")  → "2024-12-25"
```

---

#### `normalize_ssn(ssn: str)`
Removes SSN formatting.

```python
normalize_ssn("123-45-6789") → "123456789"
```

---

#### `normalize_currency(amount: str)`
Converts currency strings to floats.

```python
normalize_currency("$968,877.00") → 968877.0
normalize_currency("$1,234.56")   → 1234.56
```

---

#### `normalize_address(address: str)`
Standardizes street addresses.

```python
normalize_address("123 Main Street") → "123 Main St"
normalize_address("Apt. 5")          → "Apt 5"
```

---

## Workflow

### Input
```python
{
    "loan_id": "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6",
    "missing_fields": ["CD.EMAIL", "CD.PHONE"],
    "fields_to_clean": [{"id": "CD.DATE", "value": "12/25/2024"}],
    "demo_mode": True
}
```

### Process

```
┌──────────────────────────────────────────┐
│ STEP 1: MORTGAGE INSURANCE               │
├──────────────────────────────────────────┤
│ 1. check_mi_required(loan_id)            │
│    ✓ LTV: 98.865% → MI Required          │
│                                           │
│ 2. calculate_loan_mi(loan_id)            │
│    ✓ Monthly: $450.25                    │
│    ✓ Cancel at: 78% LTV                  │
│    ✓ Source: mi_cert                     │
│                                           │
│ 3. populate_mi_fields(dry_run=True)      │
│    ✓ Would write 5 MI fields             │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│ STEP 2: FEE TOLERANCE                    │
├──────────────────────────────────────────┤
│ 1. check_loan_fee_tolerance(loan_id)     │
│    ✓ Section A: No violations            │
│    ⚠️ Section B: $75 over 10% limit      │
│                                           │
│ 2. Flag violations (no auto-cure)        │
│    → Will be reported to LO in email     │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│ STEP 3: CD FIELD POPULATION              │
├──────────────────────────────────────────┤
│ 1. get_cd_field_status(loan_id)          │
│    → Missing: ["CD.EMAIL", "CD.PHONE"]   │
│                                           │
│ 2. For "CD.EMAIL":                       │
│    a. search_loan_fields("email")        │
│       → Found: 4002, 1402                │
│    b. get_loan_field_value("4002")       │
│       → "john.doe@email.com"             │
│    c. write_field_value(dry_run=True)    │
│       → Would write to CD.EMAIL          │
│                                           │
│ 3. For "CD.PHONE":                       │
│    a. search_loan_fields("phone")        │
│       → Found: 65, 66, 67                │
│    b. get_loan_field_value("65")         │
│       → "7021234567"                     │
│    c. normalize_phone_number()           │
│       → "7021234567" (already clean)     │
│    d. write_field_value(dry_run=True)    │
│       → Would write to CD.PHONE          │
│                                           │
│ 4. For fields_to_clean:                  │
│    a. normalize_date("12/25/2024")       │
│       → "2024-12-25"                     │
│    b. write_field_value(dry_run=True)    │
│       → Would update CD.DATE             │
└──────────────────────────────────────────┘
```

### Output
```python
{
    "loan_id": "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6",
    "status": "success",
    "mi_result": {
        "requires_mi": True,
        "monthly_amount": 450.25,
        "cancel_at_ltv": 78.0
    },
    "tolerance_result": {
        "has_violations": True,
        "total_cure_needed": 75.00,
        "summary": "Section B: $75 over 10% tolerance"
    },
    "fields_populated": ["CD.EMAIL", "CD.PHONE"],
    "fields_cleaned": ["CD.DATE"],
    "fields_failed": [],
    "actions": [
        {"action": "mi_calculation", "result": {...}},
        {"action": "tolerance_check", "result": {...}},
        {"action": "populate", "field_id": "CD.EMAIL", "dry_run": True},
        {"action": "populate", "field_id": "CD.PHONE", "dry_run": True},
        {"action": "clean", "field_id": "CD.DATE"}
    ],
    "summary": "MI: $450.25/mo, Fee tolerance: 1 violation, 2 fields populated, 1 cleaned",
    "demo_mode": True
}
```

---

## Usage

### Command Line

```bash
# Basic usage (demo mode - safe)
python agents/disclosure/subagents/preparation_agent/preparation_agent.py \
  --loan-id "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6" \
  --demo

# With specific missing fields
python agents/disclosure/subagents/preparation_agent/preparation_agent.py \
  --loan-id "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6" \
  --missing-fields "CD.EMAIL,CD.PHONE,CD.ADDRESS" \
  --demo

# Production mode (actual writes - use with caution!)
python agents/disclosure/subagents/preparation_agent/preparation_agent.py \
  --loan-id "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6" \
  --missing-fields "CD.EMAIL,CD.PHONE"
  # (no --demo flag)
```

---

### Python API

```python
from agents.disclosure.subagents.preparation_agent import run_disclosure_preparation

# Demo mode (recommended for testing)
result = run_disclosure_preparation(
    loan_id="b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6",
    missing_fields=["CD.EMAIL", "CD.PHONE", "CD.ADDRESS"],
    fields_to_clean=[
        {"id": "CD.DATE", "value": "12/25/2024", "type": "date"},
        {"id": "CD.PHONE2", "value": "(702) 123-4567", "type": "phone"}
    ],
    demo_mode=True  # Safe mode - no actual writes
)

# Check results
if result["status"] == "success":
    print(f"MI Required: {result['mi_result']['requires_mi']}")
    print(f"Fields Populated: {len(result['fields_populated'])}")
    print(f"Tolerance Violations: {result['tolerance_result']['has_violations']}")
    print(result["summary"])
```

---

## Example Scenarios

### Scenario 1: Conventional Loan with MI

```python
# Loan: Conventional, 98.865% LTV, CA

result = run_disclosure_preparation(
    loan_id="b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6",
    missing_fields=[],
    demo_mode=True
)

# Output:
# ✓ MI Calculated: $450.25/month
# ✓ Cancel at 78% LTV
# ✓ Fee Tolerance: No violations
# - Fields populated: 0
# - Fields cleaned: 0
# [DRY RUN - No actual writes performed]
```

---

### Scenario 2: Fee Tolerance Violation

```python
# Last LE had $1,500 origination
# Current CD has $1,600 origination (0% tolerance violation!)

result = run_disclosure_preparation(
    loan_id="loan-with-violation",
    missing_fields=[],
    demo_mode=True
)

# Output:
# ✓ MI: Not required (LTV ≤ 80%)
# ⚠️ Fee Tolerance: Found 1 violation(s): Section A +$100
#    Required cure: $100 lender credit
# - Fields populated: 0
```

---

### Scenario 3: AI Field Derivation

```python
# CD.BORROWER_EMAIL is missing
# Agent searches, finds 4002 and 1402 both have "john.doe@email.com"

result = run_disclosure_preparation(
    loan_id="b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6",
    missing_fields=["CD.BORROWER_EMAIL"],
    demo_mode=True
)

# Agent actions:
# 1. search_loan_fields("email")
#    → Found: 4002, 1402, LENDER.X15
# 2. get_loan_field_value("4002")
#    → "john.doe@email.com"
# 3. get_loan_field_value("1402")
#    → "john.doe@email.com"
# 4. AI reasons: "Both match, I'll use this value"
# 5. write_field_value("CD.BORROWER_EMAIL", "john.doe@email.com", dry_run=True)

# Output:
# - Fields populated: 1 (CD.BORROWER_EMAIL)
# [DRY RUN - Would write: CD.BORROWER_EMAIL = john.doe@email.com]
```

---

## Integration with Other Agents

### Called By
- **Orchestrator Agent** - After Verification Agent completes

### Receives From Verification
```python
{
    "loan_id": "...",
    "fields_checked": 20,
    "fields_missing": ["CD.EMAIL", "CD.PHONE", ...],
    "is_mvp_supported": True
}
```

### Passes To Request Agent
```python
{
    "loan_id": "...",
    "mi_result": {
        "requires_mi": True,
        "monthly_amount": 450.25
    },
    "tolerance_result": {
        "has_violations": False
    },
    "fields_populated": ["CD.EMAIL", "CD.PHONE"],
    "summary": "MI calculated, no violations, 2 fields populated"
}
```

---

## MVP Scope & Limitations

### ✅ MVP Features (Included)

- **MI Calculation**: Conventional loans only (LTV > 80%)
- **Fee Tolerance**: Flag violations (0% and 10% tolerance)
- **Field Population**: AI-based derivation for CD pages 1-3
- **Field Normalization**: Phone, date, SSN, currency, address
- **Safety**: Dry-run mode by default

### 🔴 Phase 2 Features (Not Included)

- **FHA/VA/USDA MI**: Complex calculations with upfront + monthly
- **Auto-Cure Tolerance**: Automatically apply lender credits
- **Full CD Population**: All 5 pages (currently pages 1-3 only)
- **APR Calculation**: Complex APR impact assessment
- **Advanced Validations**: Cross-field consistency checks

### ⚠️ Important Notes

1. **Always use demo_mode=True** for testing
2. **Non-MVP loans** (FHA/VA/USDA) are processed with warnings
3. **Fee tolerance** violations are flagged but NOT auto-cured
4. **Field writes** are simulated in dry-run mode
5. **AI derivation** may not find all missing fields

---

## Testing

### Test with Demo Loan

```bash
# Test MI calculation
python preparation_agent.py \
  --loan-id "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6" \
  --demo

# Expected:
# ✓ Loan Type: Conventional
# ✓ LTV: 98.865% → MI Required
# ✓ Monthly MI: ~$450
# ✓ Fee Tolerance: Check complete
```

### Test Field Derivation

```python
# Test the AI's ability to find and populate missing email
result = run_disclosure_preparation(
    loan_id="b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6",
    missing_fields=["CD.BORROWER_EMAIL"],
    demo_mode=True
)

assert result["status"] == "success"
assert "CD.BORROWER_EMAIL" in result["fields_populated"]
```

---

## Error Handling

### Common Errors

**1. Missing Encompass Credentials**
```
RuntimeError: Missing ENCOMPASS_CLIENT_ID/SECRET/INSTANCE_ID
```
**Fix:** Add credentials to `.env` file

---

**2. Loan Not Found**
```
Field read failed (status 404): Loan not found
```
**Fix:** Verify loan ID is correct and accessible

---

**3. Non-MVP Loan Type**
```
Warning: Non-MVP loan type: FHA
```
**Impact:** MI calculation returns estimate, not exact value

---

**4. AI Derivation Failed**
```
fields_failed: ["CD.SOME_FIELD"]
```
**Cause:** No related fields found with values  
**Fix:** Manually populate the field

---

## File Structure

```
preparation_agent/
├── README.md                          # This file
├── preparation_agent.py               # Main agent
├── __init__.py                        # Package init
└── tools/
    ├── mi_tools.py                    # MI calculation tools
    ├── field_derivation_tools.py      # AI field derivation
    ├── field_normalization_tools.py   # Value normalization
    └── __init__.py
```

---

## Performance

- **Execution Time**: 5-15 seconds (depends on number of missing fields)
- **API Calls**: ~3-10 to Encompass (batch reads where possible)
- **AI Model**: Claude 3.5 Sonnet (via LangChain + Anthropic)
- **Token Usage**: ~500-2000 tokens per loan

---

## Next Steps

After Preparation Agent completes:

1. **Review Results** - Check MI calculation, tolerance flags
2. **Verify Field Population** - Ensure AI derived correct values
3. **Request Agent** - Sends email to LO with preparation results
4. **Draw Docs** - After CD signed + 3-day wait

---

## FAQ

**Q: Why is demo_mode=True by default?**  
A: Safety! We want to review what the agent will do before making actual writes to Encompass.

**Q: Can I use this for FHA loans?**  
A: Yes, but MI calculation will be an estimate. Full FHA support is Phase 2.

**Q: What if AI can't find a field value?**  
A: It will be in `fields_failed` list. Manual population needed.

**Q: How does fee tolerance work?**  
A: Compares Last LE vs Current CD. Section A fees (0% tolerance) can't increase. Section B fees (10% tolerance) can increase up to 10% in aggregate.

**Q: Can I run without AI field derivation?**  
A: Not currently. The agent uses AI reasoning to intelligently populate fields.

---

## Support

For issues or questions:
1. Check this README
2. Review `discovery/disclosure_architecture.md` for detailed specs
3. Test with `demo_mode=True` first
4. Check logs for detailed error messages

---

*Last updated: December 2024 - MVP Implementation*

