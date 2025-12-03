# Disclosure Agent v2 - Implementation Gaps

This document tracks gaps between the Disclosure Desk SOP (video summary) and the current implementation.

## Status Key

| Status | Meaning |
|--------|---------|
| ✅ IMPLEMENTED | Fully implemented in codebase |
| 🚧 IN PROGRESS | Partially implemented |
| ⏳ PLANNED | Not implemented, on roadmap |
| ❌ NOT PLANNED | Out of MVP scope |

---

## Implemented Gaps

### G1: Phone/Email Hard Stop ✅
**Implemented in:** `packages/shared/form_validator.py`, `verification_agent.py`

Per SOP: Missing phone number or email is a **HARD STOP**.

```python
HARD_STOP_FIELDS = {
    "borrower_phone": "FE0117",   # Home Phone Number
    "borrower_email": "1240",     # Email Address
}
```

- Added `check_hard_stops()` method to FormValidator
- Added `check_hard_stops` tool to verification_agent
- Forms validation now includes hard stop check
- Returns `has_hard_stops: true` if blocking

### G8: Closing Date 15-Day Rule ✅
**Implemented in:** `packages/shared/trid_checker.py`, `verification_agent.py`

Per SOP: Closing date must be at least 15 days after:
- Application date (if NOT locked)
- Last rate set date (if locked)

```python
MINIMUM_CLOSING_DAYS = 15
CLOSING_DATE_FIELD = "748"
```

- Added `check_closing_date()` method to TRIDChecker
- Added `check_closing_date_rule` tool to verification_agent
- Returns `is_valid: false` if closing date < 15 days

---

## Remaining Gaps

### G2: FACT Act Disclosure ⏳
**Priority:** HIGH  
**Effort:** Medium

Per SOP (Step 23):
> "Mark the two boxes: 'Material terms for credit by select' and 'Credit score for the disclosure notice' to ensure the credit score disclosure document prints"

**What's Missing:**
- Checkbox field IDs not identified
- Validation that boxes are marked
- Auto-population of credit score from credit report

**Implementation Needed:**
```python
# packages/shared/fact_act_updater.py
FACT_ACT_CHECKBOX_FIELDS = {
    "material_terms_credit": "XXXXX",  # Need to identify
    "credit_score_disclosure": "XXXXX",  # Need to identify
}
```

---

### G3: Home Counseling Providers ⏳
**Priority:** MEDIUM  
**Effort:** High

Per SOP (Step 24):
> "Click 'get agencies'. Mark first 3 services starting with 'F' and first 3 starting with 'P'. Ensure at least 10 agencies."

**What's Missing:**
- API endpoint to fetch housing counseling agencies
- Selection algorithm (F-services, P-services)
- Validation for minimum 10 agencies

**Implementation Needed:**
```python
# packages/shared/home_counseling.py
def get_housing_agencies(zip_code: str) -> List[Agency]:
    """Fetch HUD-approved agencies near property."""
    pass

def select_required_agencies(agencies: List[Agency]) -> List[Agency]:
    """Select first 3 F-services and first 3 P-services."""
    f_agencies = [a for a in agencies if a.service.startswith("F")][:3]
    p_agencies = [a for a in agencies if a.service.startswith("P")][:3]
    return f_agencies + p_agencies
```

---

### G4: Transcript Forms ❌
**Priority:** LOW (May be manual)  
**Effort:** Medium

Per SOP (Step 26):
> "Update transcript forms: 8821, 4506, Request for Copy"

**What's Missing:**
- Form field mappings for 4506/8821
- Copy from borrower summary logic

**Notes:**
- May remain manual process
- Consider for future automation

---

### G5: Mandatory Fee Validation ⏳
**Priority:** MEDIUM  
**Effort:** Medium

Per SOP (Step 29):
> "Ensure appraisal fee and credit report fee are present"

**What's Missing:**
- Validation that mandatory fees exist (not just tolerance check)
- List of mandatory fees by loan type

**Implementation Needed:**
```python
# packages/shared/fee_validator.py
MANDATORY_FEES = {
    "all": ["appraisal", "credit_report"],
    "purchase": ["title_settlement", "lender_title_insurance", "owner_title_insurance"],
    "refinance": ["title_settlement", "lender_title_insurance", "recording_fee"],
}
```

---

### G6: Settlement Service Provider Form ⏳
**Priority:** MEDIUM  
**Effort:** Medium

Per SOP (Step 29):
> "Apply 'default template settlement service provider template'. Delete inapplicable services."

**What's Missing:**
- Template application logic
- Service deletion logic
- Fee copy from LE

**Notes:**
- May require form-level API access

---

### G7: Affiliate Business Arrangement ⏳
**Priority:** LOW  
**Effort:** Low

Per SOP (Step 18):
> "If blank, click 'supply templates' and 'AWM affiliates'"

**What's Missing:**
- Template detection logic
- Template application API

---

### G9: Denoter Form ⏳
**Priority:** MEDIUM  
**Effort:** Medium

Per SOP (Step 8):
> "Mark 'include lender info page'. Verify occupancy. USPS verify address."

**What's Missing:**
- Lender info page checkbox
- Occupancy validation
- USPS address verification integration

**Implementation Needed:**
```python
# packages/shared/usps_validator.py
def verify_address_usps(address: str) -> Dict:
    """Verify address with USPS API."""
    pass
```

---

### G10: Blend Integration Form ❌
**Priority:** LOW  
**Effort:** Low

Per SOP (Step 33):
> "Check organization ID is updated"

**Notes:**
- Blend-specific, may be auto-populated
- Low priority for MVP

---

### G11: Audit Exception 26.4 ⏳
**Priority:** MEDIUM  
**Effort:** Low

Per SOP (Step 32):
> "Audit clear, except for 26.4 audit which is acceptable"

**What's Missing:**
- Filter audit results to allow 26.4 exception
- Document what 26.4 audit represents

**Implementation Needed:**
```python
# packages/shared/disclosure_orderer.py
ACCEPTABLE_AUDIT_EXCEPTIONS = ["26.4"]

def filter_audit_issues(issues: List[str]) -> List[str]:
    """Filter out acceptable audit exceptions."""
    return [i for i in issues if i not in ACCEPTABLE_AUDIT_EXCEPTIONS]
```

---

### G12: Interest Days = 365 ❌
**Priority:** LOW  
**Effort:** Low

Per SOP (Step 25):
> "Check interest rate per days in year is 365"

**Current Implementation:** Sets 360/360 for interest accrual

**Notes:**
- Need to verify if this conflicts with current 360/360 setting
- May be product-specific

---

### G13: Credit/Lender Credit Check ⏳
**Priority:** MEDIUM  
**Effort:** Medium

Per SOP (Step 10):
> "For refinance, check for 'other lender credit'. For purchase, check for seller credit and lender credit."

**What's Missing:**
- Credit type validation by loan purpose
- Field IDs for credits

---

### G14: Consent Validity 60 Days ⏳
**Priority:** MEDIUM  
**Effort:** Low

Per SOP (Step 19):
> "SSN verification statement and consent validity must be within 60 days"

**What's Missing:**
- Consent date field ID
- 60-day calculation from consent date

**Implementation Needed:**
```python
# Add to packages/shared/form_validator.py
CONSENT_VALIDITY_DAYS = 60
CONSENT_DATE_FIELD = "XXXXX"  # Need to identify

def check_consent_validity(loan_id: str) -> bool:
    consent_date = read_field(loan_id, CONSENT_DATE_FIELD)
    if consent_date:
        days_old = (date.today() - consent_date).days
        return days_old <= CONSENT_VALIDITY_DAYS
    return False
```

---

## Pre-Check Functions ✅ INTEGRATED

The following utility functions are now **fully integrated** into the orchestrator flow:

| Function | Purpose | Location |
|----------|---------|----------|
| `get_loan_milestones()` | Fetch milestone status | `packages/shared/milestone_checker.py` |
| `get_disclosure_tracking_logs()` | Check if LE/CD already sent | `packages/shared/milestone_checker.py` |
| `run_pre_check()` | Full eligibility check | `packages/shared/milestone_checker.py` |
| `check_initial_le_eligibility()` | Convenience wrapper | `packages/shared/milestone_checker.py` |

**Integration:**
- Orchestrator calls `run_pre_check()` as Step 0 before verification
- Pre-check blocks if: LE already sent, loan in terminal status, etc.
- Results included in summary and JSON output

---

## Recommended Implementation Order

| Priority | Gap | Effort | Impact |
|----------|-----|--------|--------|
| 1 | G2: FACT Act Boxes | Medium | Critical - credit disclosure won't print |
| 2 | G5: Mandatory Fee Validation | Medium | High - prevents audit failures |
| 3 | G11: Audit 26.4 Exception | Low | Medium - allows acceptable audits |
| 4 | G14: Consent 60-Day | Low | Medium - compliance |
| 5 | G13: Credit/Lender Credit | Medium | Medium - validation |
| 6 | G3: Home Counseling | High | Medium - required form |
| 7 | G9: Denoter Form | Medium | Medium - required form |

---

## Notes

### Disclosure Tracking Pre-Check
The disclosure tracking check (`get_disclosure_tracking_logs`) returns empty `[]` when no disclosures have been sent - this is the expected state for Initial LE.

If the list contains items with `"contents": "LE"`, the Initial LE has already been sent and this would be a COC/Revised LE scenario (not MVP).

### Milestone vs Queue
The SOP mentions "DD Queue" but Encompass uses milestones. Current implementation checks milestones, but the actual queue assignment is handled separately in Encompass.

---

*Last Updated: December 2025*
*Version: 2.0*

