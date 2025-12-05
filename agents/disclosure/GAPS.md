# Disclosure Agent v2 - Implementation Gaps

**Last Updated**: December 5, 2025  
**Version**: 2.1 (Updated Video Notes Analysis)  
**Related Documents**: [Main README](./README.md) | [Architecture v2](../../discovery/disclosure_architecture_v2.md)

This document tracks gaps between the **Updated Disclosure Desk SOP Video Notes** (`context/Disclosure Desk SOP Video Notes.txt`) and the current v2 implementation.

---

## Status Key

| Status | Meaning |
|--------|---------|
| ✅ IMPLEMENTED | Fully implemented in codebase |
| 🚧 IN PROGRESS | Partially implemented |
| ⏳ PLANNED | Not implemented, on roadmap |
| ❌ NOT PLANNED | Out of MVP scope |

---

## Currently Implemented

### G1: Phone/Email Hard Stop ✅
**Implemented in:** `packages/shared/form_validator.py`, `verification_agent.py`

**Video Notes Reference:** Lines 58-61
> "Home Phone - Hard stop" / "Email - If not present, will not be able to send disclosures"

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

**Video Notes Reference:** Lines 103-106
> "Est closing date will be any date up until application date + 15 days"

```python
MINIMUM_CLOSING_DAYS = 15
CLOSING_DATE_FIELD = "748"
```

- Added `check_closing_date()` method to TRIDChecker
- Added `check_closing_date_rule` tool to verification_agent
- Returns `is_valid: false` if closing date < 15 days

### TRID Compliance (3-Day Rule) ✅
**Implemented in:** `packages/shared/trid_checker.py`

**Video Notes Reference:** Lines 6-7
> "Application Date and LE Due Date should be within 3 days of compliance"

- Validates LE due date is within 3 business days
- Checks if LE due date has passed (escalate to supervisor)

### Late Charge Rules ✅
**Implemented in:** `packages/shared/regz_le_updater.py`

**Video Notes Reference:** Lines 148-151
> "Click Get Late Fee - 15 days late - Charge is 5% - Of the principal and interest overdue"

- Conventional: 15 days, 5%
- FHA/VA: 15 days, 4%
- NC state override: 4% for all loan types

### Assumption Text ✅
**Implemented in:** `packages/shared/regz_le_updater.py`

**Video Notes Reference:** Lines 152-155
> "Assumption - Conventional = may not" / "FHA = may, subject to conditions"

- Sets appropriate assumption text based on loan type

### Cash to Close Matching ✅
**Implemented in:** `packages/shared/ctc_matcher.py`

**Video Notes Reference:** Lines 195, 646-654 (SOP)
> "Confirm with Estimated Cash to Close in Loan Estimate Page 2"

- Purchase: Checks specific boxes
- Refinance: Checks Alternative form checkbox

---

## CRITICAL GAPS (Tier 1 - Must Have)

### G2: FACT Act Disclosure Checkboxes ⏳
**Priority:** CRITICAL  
**Effort:** Medium

**Video Notes Reference:** Lines 111-117
> "Material Terms of Credit Set by Credit Score and Credit Score for Disclosure Notice must both be marked (for co borrower as well) - Only Credit Score Disclosure will be printed for borrower and co borrower"

**What's Missing:**
- Two checkbox field IDs not identified
- No validation that boxes are marked
- Credit score disclosure **will NOT print** without these boxes checked

**Implementation Needed:**
```python
# packages/shared/fact_act_updater.py
FACT_ACT_CHECKBOX_FIELDS = {
    "material_terms_credit": "XXXXX",  # Need to identify
    "credit_score_disclosure": "XXXXX",  # Need to identify
}

def ensure_fact_act_boxes_checked(loan_id: str) -> Dict:
    """Ensure both FACT Act boxes are checked for credit disclosure to print."""
    pass
```

**Related Video Notes:**
- Line 109-128: Full FACT Act Disclosure process
- Line 21 (dd_video_summary): "Mark the two boxes..."

---

### G3: Home Counseling Providers ⏳
**Priority:** HIGH  
**Effort:** High

**Video Notes Reference:** Lines 129-136
> "Click on 'Get Agencies' - Service Name first three rows have to be checked - First 3 rows start with F - 3 rows that start with P - 10 are minimum checked in Home Counselor list; If more are checked, increase distance (>= 500)"

**What's Missing:**
- API endpoint to fetch HUD housing counseling agencies
- Selection algorithm:
  - First 3 services starting with "F" (Fair Housing, Financial Management, Financing)
  - First 3 services starting with "P" (Budgeting and Credit Repair Workshops)
- Minimum 10 agencies validation
- Distance adjustment logic (≥ 500 if fewer than 10)
- Language = English validation

**Implementation Needed:**
```python
# packages/shared/home_counseling.py
def get_housing_agencies(zip_code: str, distance: int = 50) -> List[Agency]:
    """Fetch HUD-approved agencies near property."""
    pass

def select_required_agencies(agencies: List[Agency]) -> List[Agency]:
    """Select first 3 F-services and first 3 P-services."""
    f_agencies = [a for a in agencies if a.service.startswith("F")][:3]
    p_agencies = [a for a in agencies if a.service.startswith("P")][:3]
    return f_agencies + p_agencies

def validate_minimum_agencies(agencies: List[Agency], min_count: int = 10) -> bool:
    """Ensure at least 10 agencies are selected."""
    pass
```

---

### G4: Transcript Forms (4506-C, 8821) ⏳
**Priority:** HIGH  
**Effort:** Medium

**Video Notes Reference:** Lines 158-179
> "Request for Transcript of Tax (Classic) - IVES participant name, participant ID, phone, address, city should be there - Enter only one tax form number per request: 1040 - Check a Return Transcript - Year or period requested: 12/31/2024, 12/31/2023, 12/31/2022"

**What's Missing:**
- 4506-C form population with:
  - 5a: Xactus info (0000304771, 888-212-4200, 370 Reed Road Suite 100, Broomall, PA 19008)
  - 5d: AWM info (702-369-0905, 8345 W. Sunset Road #380, Las Vegas, NV 89113)
- 8821 form population (Add from Template → 8821 – Halcyon consent form)
- Year updates (12/31/2024, 12/31/2023, 12/31/2022)
- "Copy from Borrower Summary" automation
- Tax form numbers: 1040, W2
- Request for Copy of Tax Return form

**Implementation Needed:**
```python
# packages/shared/transcript_forms.py
TRANSCRIPT_5A_INFO = {
    "participant_name": "Xactus, LLC",
    "participant_id": "0000304771",
    "phone": "888-212-4200",
    "address": "370 Reed Road Suite 100",
    "city_state_zip": "Broomall, PA 19008",
}

TRANSCRIPT_5D_INFO = {
    "client_name": "All Western Mortgage, Inc.",
    "client_phone": "702-369-0905",
    "client_address": "8345 W. Sunset Road #380",
    "client_city_state_zip": "Las Vegas, NV 89113",
}

def populate_transcript_forms(loan_id: str, borrower_type: str = "Borrower") -> Dict:
    """Populate 4506-C, 8821, and Request for Copy forms."""
    pass
```

---

### G5: 2015 Itemization Validations ⏳
**Priority:** HIGH  
**Effort:** Medium

**Video Notes Reference:** Lines 180-195
> "Itemize fees when printing box should always be marked - Bona Fide box should be marked for all loans - Appraisal Fee check - Recording Fees has to be there"

**What's Missing:**
- "Itemize fees when printing" checkbox validation (must be marked)
- "Bona Fide" checkbox validation (must be marked for all loans)
- Mandatory fee presence checks:
  - All loans: Appraisal Fee, Credit Report Fee
  - Purchase: Title Settlement, Lender Title Insurance, Owner Title Insurance
  - Refinance: Title Settlement, Lender Title Insurance, Recording Fee
- Section-specific validations:
  - Section 800: Origination charges paid to "L", APR marked
  - Section 802: Credits & Points reflection
  - Section 1000: Impounds/Escrow settings (HOI, Property Taxes, Flood Insurance)
  - Section 1100: Title charges per transaction type
  - Section 1200: Recording Fee mandatory

**Implementation Needed:**
```python
# packages/shared/itemization_validator.py
MANDATORY_CHECKBOXES = {
    "itemize_fees_when_printing": "NEWHUD.X100",  # Need to identify
    "bona_fide": "NEWHUD.X101",  # Need to identify
}

MANDATORY_FEES = {
    "all": ["appraisal_fee", "credit_report_fee"],
    "purchase": ["title_settlement", "lender_title_insurance", "owner_title_insurance"],
    "refinance": ["title_settlement", "lender_title_insurance", "recording_fee"],
}

def validate_itemization(loan_id: str) -> Dict:
    """Validate all 2015 Itemization requirements."""
    pass
```

---

### G6: Settlement Service Provider List (SSPL) ⏳
**Priority:** HIGH  
**Effort:** Medium

**Video Notes Reference:** Lines 198-201
> "If templates not applied, click Apply Template -> select Settlement Service Provider template - Delete Pest Inspection, Home Inspection Services, Engineering Inspection, Land Survey - Populate fee boxes in Settlement Service Provider with LE Page 2 title fees"

**What's Missing:**
- Template detection logic (is template applied?)
- Template application automation
- Service deletion logic:
  - Delete: Pest Inspection, Home Inspection Services, Engineering Inspection, Land Survey
- Fee copy from LE Page 2 Section C (in CAPITAL letters)

**Implementation Needed:**
```python
# packages/shared/sspl_updater.py
SERVICES_TO_DELETE = [
    "Pest Inspection",
    "Home Inspection Services", 
    "Engineering Inspection",
    "Land Survey",
]

def apply_sspl_template(loan_id: str) -> Dict:
    """Apply Settlement Service Provider template if not already applied."""
    pass

def copy_fees_from_le(loan_id: str) -> Dict:
    """Copy title fees from LE Page 2 Section C to SSPL."""
    pass
```

---

## MEDIUM-PRIORITY GAPS (Tier 2)

### G7: Affiliate Business Arrangement Form ⏳
**Priority:** MEDIUM  
**Effort:** Low

**Video Notes Reference:** Lines 85-86
> "If blank -> click on 'Apply Template' -> AWM Affiliate -> OK -> Mark Settlement and Purchase/Sale/Refinance boxes. All info will be auto populated"

**What's Missing:**
- Template detection (is form blank?)
- AWM Affiliate template application
- Settlement box marking
- Purchase/Sale/Refinance box marking

---

### G9: 1003 URLA - Lender Form (Denoter Form) Validations ⏳
**Priority:** MEDIUM  
**Effort:** Medium

**Video Notes Reference:** Lines 19-48
> "Include lender information pages in borrower package - Subject property address - Verify in USPS - Estimated value - Appraisal value - Project type - Purpose of Loan - Occupancy"

**What's Missing:**
- "Include lender info page in borrower package" checkbox
- USPS address verification integration
- Field validations for:
  - Estimated Value
  - Appraised Value  
  - Project Type
  - Refinance Type (for refinance loans)
  - Mortgage Lien Type
  - Amortization Type
  - Qual Rate
  - TOTAL CREDITS
  - Homeownership Education (L5 - for Conventional)

**Implementation Needed:**
```python
# packages/shared/usps_validator.py
def verify_address_usps(address: str, city: str, state: str, zip_code: str) -> Dict:
    """Verify address with USPS API."""
    pass
```

---

### G10: 1003 URLA Part 1 Validations ⏳
**Priority:** MEDIUM  
**Effort:** Low

**Video Notes Reference:** Lines 49-67
> "Citizenship - Marital Status - Mailing address: same as current - Military Service - Language Preference"

**What's Missing:**
- Citizenship validation
- Marital Status validation
- "Same as Current" checkbox for mailing address validation
- Former Address (if applicable)
- Military Service field (always "yes" for VA loans)
- Language Preference field

---

### G11: 1003 URLA Part 4 & LO Info Validations ⏳
**Priority:** MEDIUM  
**Effort:** Medium

**Video Notes Reference:** Lines 73-84
> "Section 5. Declarations - Borrower/Co-Borrower questions must have answers - Loan Originator NMLSR ID# Must be 14210 - Go to NMLS Consumer Access - Check for Branch Location - Verify if Loan Originator Name is same"

**What's Missing:**
- Section 5 Declarations: All questions answered validation
- Section 8 Demographic Information: Check if provided
- LO NMLS ID must be 14210 validation
- External NMLS Consumer Access API verification
- LO branch location verification
- LO name match with NMLS

---

### G12: Borrower Summary - Origination Validations ⏳
**Priority:** MEDIUM  
**Effort:** Medium

**Video Notes Reference:** Lines 87-106
> "Channel - Current Status has to be Active Loan - Vesting Type - Individual - Consent valid days and reason for authorizing consent should not be blank - Company's Information - Company's Agent Information Should be CoreLogic Inc."

**What's Missing:**
- Channel = "Bank" validation
- Current Status = "Active Loan" validation
- Vesting Type = "Individual" validation
- SSN Verification Statement validation
- Consent validity (60 days) and reason not blank
- Company's Information (Lender/Broker Data button)
- Company's Agent Information = "CoreLogic Inc." validation
- CoreLogic address: "40 Pacifica Suite 900"

---

### G13: Disclosure Summary Review ⏳
**Priority:** MEDIUM  
**Effort:** Low

**Video Notes Reference:** Line 107-108
> "Look out for Comments/Notes, usually instructions, more info about fees, lender, etc."

**What's Missing:**
- Automated reading of Comments/Notes section
- Flagging of special instructions
- Detection of fee or lender credit mentions

---

### G14: Credit/Lender Credit Validation ⏳
**Priority:** MEDIUM  
**Effort:** Medium

**Video Notes Reference:** Lines 45-48 (SOP)
> "For refinance, check for 'other lender credit'. For purchase, check for seller credit and lender credit."

**What's Missing:**
- Credit type validation by loan purpose:
  - Refinance: "Other Lender Credit" check
  - Purchase: Seller Credit + Lender Credit check
- Field IDs for various credit types

---

### G15: Consent Validity 60 Days ⏳
**Priority:** MEDIUM  
**Effort:** Low

**Video Notes Reference:** Lines 95 (related SOP context)
> "Consent valid days should not be blank... should be within 60 days"

**What's Missing:**
- Consent date field ID
- 60-day calculation from consent date
- Validation that reason for consent is not blank

**Implementation Needed:**
```python
CONSENT_VALIDITY_DAYS = 60
CONSENT_DATE_FIELD = "XXXXX"  # Need to identify

def check_consent_validity(loan_id: str) -> Dict:
    """Check if consent is within 60 days and reason is provided."""
    pass
```

---

### G16: Audit Exception 26.4 ⏳
**Priority:** MEDIUM  
**Effort:** Low

**Video Notes Reference:** Line 203-205 (related SOP)
> "Click on Preview - All fields should PASS - IF HMDA is ALERT, still proceed"

**What's Missing:**
- Filter audit results to allow 26.4 exception
- Document what 26.4 audit represents
- HMDA alert handling (proceed anyway)

**Implementation Needed:**
```python
ACCEPTABLE_AUDIT_EXCEPTIONS = ["26.4"]
ACCEPTABLE_ALERTS = ["HMDA"]

def filter_audit_issues(issues: List[str]) -> List[str]:
    """Filter out acceptable audit exceptions."""
    return [i for i in issues if i not in ACCEPTABLE_AUDIT_EXCEPTIONS]
```

---

### G17: Company License #204 ⏳
**Priority:** MEDIUM  
**Effort:** Low

**SOP Reference:** Page 6
> "For all state Initial Disclosures, ensure that Company License #204 is updated in ENC by navigating to: Tools tab → File Contact → Category/Role → Lender"

**What's Missing:**
- Validation that Company License #204 is present
- Field location identification

---

## LOW-PRIORITY GAPS (Tier 3)

### G18: RegZ-LE Additional Fields ⏳
**Priority:** LOW  
**Effort:** Low

**Video Notes Reference:** Lines 137-157
> "1st payment date is automatically updated - If loan has buydown, populate Buydown Mortgage - 0% payment option blank - Interest Days/Days in a Year 360/360 - Number of Days... is 365"

**What's Missing:**
- 1st Payment Date auto-update validation
- Buydown fields when marked:
  - Buydown box marked
  - Contributor
  - Rate and Term
  - Disbursement
- 0% Payment Option = blank validation
- Prepayment Penalty tab fields (Type, Period, %)
- "Number of Days (Biweekly, Interim Interest, Classic HELOC)" = 365 (different from 360/360)

---

### G19: Blend Integration ORGID ❌
**Priority:** LOW  
**Effort:** Low

**Video Notes Reference:** Lines 213-215
> "ORGID has to be updated - Depends on LO"

**Notes:**
- Blend-specific, may be auto-populated
- Low priority for MVP

---

### G20: eFolder Product Selection ⏳
**Priority:** LOW  
**Effort:** Medium

**Video Notes Reference:** Lines 216-226
> "If loan is conventional -> Generic All Fixed Rate Conventional 1st Lien Loans -> Order eDisclosures - In eDisclosure package (initial disclosure), if LTV < 80%, uncheck Fixed Rate Conventional PMI Disclosure"

**What's Missing:**
- Appropriate loan product template selection
- LTV-based exclusions:
  - If LTV < 80%: Uncheck "Fixed Rate Conventional PMI Disclosure"

---

### G21: Post-Disclosure LO Review Workflow ❌
**Priority:** LOW  
**Effort:** High

**Video Notes Reference:** Lines 228-241
> "Click LO to Review - Have to save generated document and manually email to LO - Get email from File Contacts form - Click Corrections Needed as needed"

**Notes:**
- May remain manual process
- Would require:
  - Setting status to "LO to Review"
  - Email generation to LO/Processor/LOA
  - Tracking approval workflow
  - "Corrections Needed" handling
  - "Approved to Send" → "Sent to Borrower" flow

---

### G22: Texas State Special Rules ❌
**Priority:** LOW (TX excluded from MVP)  
**Effort:** High

**SOP Reference:** Pages 62-65
> "Line #810: Attorney Review Fee $325.00 to Cain & Kiel, P.C. - TX Notice Concerning Extensions of Credit (12-day letter/Texas A6 form)"

**Notes:**
- Texas excluded from MVP
- Would require:
  - Attorney Review Fee ($325.00) in Line 810
  - Texas State Specific Information form
  - Texas Banker Mortgage Disclosure
  - TX Notice (12-day letter/A6 form) for refinance

---

## FORM FIELD VALIDATION GAPS

### Missing 1003 URLA - Lender Form Fields

| Field | Video Line | Field ID | Status |
|-------|------------|----------|--------|
| Estimated Value | 26 | 356 | ⏳ Not validated |
| Appraised Value | 26 | 1821 | ⏳ Not validated |
| Project Type | 27 | 1041 | ⏳ Not validated |
| Refinance Type | 30 | 299 | ⏳ Not validated |
| Mortgage Lien Type | 31 | 420 | ⏳ Not validated |
| Amortization Type | 32 | 608 | ⏳ Not validated |
| Qual Rate | 37 | 1825 | ⏳ Not validated |
| TOTAL CREDITS | 45 | TBD | ⏳ Not validated |
| Homeownership Ed (L5) | 46 | TBD | ⏳ Not validated |

### Missing 1003 URLA Part 1 Fields

| Field | Video Line | Field ID | Status |
|-------|------------|----------|--------|
| Citizenship | 55 | 126 | ⏳ Not validated |
| Marital Status | 56 | 52 | ⏳ Not validated |
| Mailing Same as Current | 64 | FR0108 | ⏳ Not validated |
| Military Service | 65-66 | 264 | ⏳ Not validated |
| Language Preference | 67 | TBD | ⏳ Not validated |

### Missing Borrower Summary - Origination Fields

| Field | Video Line | Field ID | Status |
|-------|------------|----------|--------|
| Channel = Bank | 89 | 2626 | ⏳ Not validated |
| Current Status = Active | 90 | 1393 | ⏳ Not validated |
| Vesting Type | 91 | TBD | ⏳ Not validated |
| SSN Verification | 95 | TBD | ⏳ Not validated |
| Consent Valid Days | 95 | TBD | ⏳ Not validated |
| Company's Agent = CoreLogic | 99 | TBD | ⏳ Not validated |

---

## Recommended Implementation Order

| Priority | Gap | Effort | Impact | Notes |
|----------|-----|--------|--------|-------|
| 1 | G2: FACT Act Boxes | Medium | CRITICAL | Credit disclosure won't print without |
| 2 | G5: 2015 Itemization | Medium | HIGH | Prevents audit failures |
| 3 | G4: Transcript Forms | Medium | HIGH | Required tax forms |
| 4 | G3: Home Counseling | High | HIGH | Required form automation |
| 5 | G6: SSPL Form | Medium | HIGH | Required for proper fees |
| 6 | G16: Audit 26.4 Exception | Low | MEDIUM | Allows acceptable audits |
| 7 | G11: LO NMLS Validation | Medium | MEDIUM | Compliance requirement |
| 8 | G12: Borrower Summary | Medium | MEDIUM | Multiple field validations |
| 9 | G15: Consent 60-Day | Low | MEDIUM | Compliance |
| 10 | G7: ABA Template | Low | LOW | Template automation |

---

## Notes

### Video Notes vs SOP Consistency

| Item | Video Notes | SOP | Implementation |
|------|-------------|-----|----------------|
| Late Charge Days | 15 days | 15 days | ✅ Consistent |
| Late Charge % (Conv) | 5% | 5% | ✅ Implemented |
| Late Charge % (FHA/VA) | 4% | 4% | ✅ Implemented |
| Late Charge NC | Not mentioned | 4% all types | ✅ Implemented |
| Interest Accrual | 360/360 | 360/360 | ✅ Implemented |
| Number of Days (HELOC) | 365 | Not specified | ⏳ Needs verification |
| Home Counseling Min | 10 agencies | 10 agencies | ⏳ Not implemented |
| Consent Validity | Not mentioned | 60 days | ⏳ Not implemented |

### Field ID Research Needed

The following field IDs need to be identified in Encompass:
- FACT Act checkbox fields (Material Terms, Credit Score Disclosure)
- Consent validity date field
- Vesting Type field
- SSN Verification Statement field
- Company's Agent Information fields
- Homeownership Education (L5) field
- TOTAL CREDITS field
- Language Preference field

---

*Last Updated: December 5, 2025*  
*Version: 2.1 (Updated Video Notes Analysis)*
