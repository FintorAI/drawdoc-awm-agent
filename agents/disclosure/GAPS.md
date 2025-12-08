# Disclosure Agent v2 - Implementation Gaps

**Last Updated**: December 8, 2025  
**Version**: 2.2 (Field ID Cross-Reference with Master List)  
**Related Documents**: [Main README](./README.md) | [Architecture v2](../../discovery/disclosure_architecture_v2.md)

> **Note**: Field IDs have been cross-referenced with `master_field_data.csv`. Fields marked `UNKNOWN` require manual mapping in Encompass.

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

### G2: FACT Act Disclosure Checkboxes 🚧
**Priority:** CRITICAL  
**Status:** IMPLEMENTED (partial - manual verification required)  
**Effort:** Medium  
**Implementation:** `agents/disclosure/subagents/verification_agent/tools/form_validation_tools.py`

**Video Notes Reference:** Lines 111-117
> "Material Terms of Credit Set by Credit Score and Credit Score for Disclosure Notice must both be marked (for co borrower as well) - Only Credit Score Disclosure will be printed for borrower and co borrower"

**What's Missing:**
- Two checkbox field IDs not identified
- No validation that boxes are marked
- Credit score disclosure **will NOT print** without these boxes checked

**Related Fields Found (partial):**
- Credit Score for Decision Making: `4174` / `HMDA.X116`
- Credit Score Disclosure fields: `DISCLOSURE.X637` (Credit Score Used From The Credit Report to Set the Terms of Credit)

**Implementation Needed:**
```python
# packages/shared/fact_act_updater.py
FACT_ACT_CHECKBOX_FIELDS = {
    "material_terms_credit": "UNKNOWN",  # ❌ NOT IN MASTER LIST - requires manual mapping
    "credit_score_disclosure": "UNKNOWN",  # ❌ NOT IN MASTER LIST - requires manual mapping
    # Related fields that may help:
    "credit_score_decision_making": "4174",
    "credit_score_disclosure_info": "DISCLOSURE.X637",
}

def ensure_fact_act_boxes_checked(loan_id: str) -> Dict:
    """Ensure both FACT Act boxes are checked for credit disclosure to print."""
    pass
```

**Related Video Notes:**
- Line 109-128: Full FACT Act Disclosure process
- Line 21 (dd_video_summary): "Mark the two boxes..."

---

### G3: Home Counseling Providers 🚧
**Priority:** HIGH  
**Status:** IMPLEMENTED (HUD API endpoint pending)  
**Effort:** High  
**Implementation:** `packages/shared/home_counseling.py`, `agents/disclosure/subagents/preparation_agent/tools/counseling_tools.py`

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

**Related Fields Found:**
- Borrower Homeownership Counseling Completion Date: `URLA.X233`

**Implementation Needed:**
```python
# packages/shared/home_counseling.py
HOME_COUNSELING_FIELDS = {
    "counseling_completion_date": "URLA.X233",  # ✅ Found in master list
    "agency_list_fields": "UNKNOWN",  # ❌ NOT IN MASTER LIST - requires manual mapping
    "service_selection_fields": "UNKNOWN",  # ❌ NOT IN MASTER LIST - requires manual mapping
}

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

### G4: Transcript Forms (4506-C, 8821) ✅
**Priority:** HIGH  
**Effort:** Medium  
**Status:** IMPLEMENTED (full API integration)  
**Implementation:** `packages/shared/transcript_forms.py`, `agents/disclosure/subagents/preparation_agent/tools/transcript_tools.py`

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

**🎯 API SOLUTION AVAILABLE - Encompass Developer Connect**

The Transcript of Tax forms (4506-C, 4506-T, 8821) can be managed via the **Request for Transcript of Tax APIs** instead of direct field mapping:

| API Endpoint | Purpose | Documentation |
|--------------|---------|---------------|
| `GET /v3/settings/templates/transcriptRequests` | List available templates | [V3 Get List of Transcript of Tax Templates](https://developer.icemortgagetechnology.com/developer-connect/reference/v3-get-transcript-of-tax-template) |
| `GET /v3/settings/templates/transcriptRequests/{templateId}` | Get template settings (IVES Participants, Third Party Designees, tax years) | [V3 Get Transcript of Tax Template](https://developer.icemortgagetechnology.com/developer-connect/reference/v3-get-transcript-of-tax-template) |
| `PATCH /v3/loans/{loanId}/applications/{applicationId}/transcriptRequests` | Add/Update/Delete transcript records | [V3 Update Request for Transcript of Tax](https://developer.icemortgagetechnology.com/developer-connect/reference/v3-patch-request-for-transcript-of-tax) |
| `PATCH /v3/loans/{loanId}?templateType=transcriptRequest&templatePath={path}` | Apply template to loan | [V3 Update Loan](https://developer.icemortgagetechnology.com/developer-connect/reference/update-loan-1) |

**API Actions Available:**
- `add` - Add new transcript request (ID auto-generated)
- `update` - Update existing record (requires ID)
- `delete` - Delete record (requires ID only)
- `reorder` - Reorder collection
- `replace` - Replace all records

**Related Fields Found (for direct field access if needed):**
- IRS 4506-C Print Version: `IRS4506.X92`
- Use IRS 4506-C: `IRS4506.X67`
- IRS - Send Return to First Name: `IRS4506.X8`

---

#### API Workflow for Transcript Forms

**Step 1: List Available Templates**
```python
# GET /v3/settings/templates/transcriptRequests
# Returns available pre-configured templates in Encompass Settings

templates = await api_client.get("/v3/settings/templates/transcriptRequests")
# Returns list of template IDs like:
# - "4506-C Request for Transcript"  
# - "8821 – Halcyon consent form"
# - "4506-T Legacy"
```

**Step 2: Get Template Settings (Optional - for verification)**
```python
# GET /v3/settings/templates/transcriptRequests/{templateId}
# Returns pre-configured IVES participants, third party designees, tax years

template = await api_client.get(
    f"/v3/settings/templates/transcriptRequests/{template_id}"
)
# Returns settings like:
# {
#     "ivesParticipants": [
#         {"name": "Xactus, LLC", "participantId": "0000304771", ...}
#     ],
#     "thirdPartyDesignees": [
#         {"name": "All Western Mortgage, Inc.", ...}
#     ],
#     "taxYears": ["12/31/2024", "12/31/2023", "12/31/2022"],
#     ...
# }
```

**Step 3: Apply Template to Loan (Recommended - Single API Call)**
```python
# PATCH /v3/loans/{loanId}?templateType=transcriptRequest&templatePath={path}
# This populates ALL fields from the template automatically

result = await api_client.patch(
    f"/v3/loans/{loan_id}",
    params={
        "templateType": "transcriptRequest",
        "templatePath": "Public\\Loan Templates\\4506-C Request for Transcript"
    }
)
# Auto-populates:
# - Section 5a: Xactus IVES info (name, ID, phone, address)
# - Section 5d: AWM Third Party Designee info
# - Tax years: 12/31/2024, 12/31/2023, 12/31/2022
# - Form type: 1040, W2, etc.
```

**Step 4: Manage Individual Records (Fine-grained control if needed)**
```python
# PATCH /v3/loans/{loanId}/applications/{applicationId}/transcriptRequests?action=add

# Add a new transcript request record
await api_client.patch(
    f"/v3/loans/{loan_id}/applications/{app_id}/transcriptRequests",
    params={"action": "add"},
    json=[{
        "taxFormNumber": "1040",
        "transcriptType": "ReturnTranscript",
        "taxYears": ["12/31/2024", "12/31/2023", "12/31/2022"],
        "ivesParticipant": {
            "name": "Xactus, LLC",
            "participantId": "0000304771",
            "phone": "888-212-4200",
            "address": "370 Reed Road Suite 100",
            "cityStateZip": "Broomall, PA 19008"
        },
        "thirdPartyDesignee": {
            "name": "All Western Mortgage, Inc.",
            "phone": "702-369-0905",
            "address": "8345 W. Sunset Road #380",
            "cityStateZip": "Las Vegas, NV 89113"
        }
    }]
)
```

---

#### Benefits: API vs Field Mapping

| Manual Field Mapping | API Template Approach |
|---------------------|----------------------|
| Need to map ~20+ field IDs for 4506-C | Apply template = 1 API call |
| Hard-code IVES participant data | Settings managed centrally in Encompass |
| Update code when tax years change | Update template in Encompass Settings |
| Different code paths for 4506-C/T/8821 | Same API, different template paths |

---

**Implementation Needed:**
```python
# packages/shared/transcript_forms.py
from typing import Dict, List, Optional

# API Endpoints
TRANSCRIPT_API_ENDPOINTS = {
    "list_templates": "/v3/settings/templates/transcriptRequests",
    "get_template": "/v3/settings/templates/transcriptRequests/{templateId}",
    "manage_transcripts": "/v3/loans/{loanId}/applications/{applicationId}/transcriptRequests",
    "apply_template": "/v3/loans/{loanId}",  # with query params
}

# Template Query Params for V3 Update Loan
TEMPLATE_PARAMS = {
    "templateType": "transcriptRequest",
    "templatePath": "{templatePath}",  # Path to transcript template in Encompass Settings
}

# Pre-configured IVES Participant Info (Section 5a)
TRANSCRIPT_5A_INFO = {
    "ives_participant_name": "Xactus, LLC",
    "ives_participant_id": "0000304771",
    "ives_participant_phone": "888-212-4200",
    "ives_participant_address": "370 Reed Road Suite 100",
    "ives_participant_city_state_zip": "Broomall, PA 19008",
}

# Pre-configured Third Party Designee Info (Section 5d / AWM Info)
TRANSCRIPT_5D_INFO = {
    "third_party_name": "All Western Mortgage, Inc.",
    "third_party_phone": "702-369-0905",
    "third_party_address": "8345 W. Sunset Road #380",
    "third_party_city_state_zip": "Las Vegas, NV 89113",
}

# Tax Years to Request
TAX_YEARS = ["12/31/2024", "12/31/2023", "12/31/2022"]

# Tax Form Types
TAX_FORMS = {
    "4506-C": "Request for Transcript of Tax Return",
    "4506-T": "Request for Transcript of Tax Return (Legacy)",
    "8821": "Tax Information Authorization (Halcyon consent)",
}

# Direct field IDs (fallback)
IRS_FIELD_IDS = {
    "print_version": "IRS4506.X92",
    "use_4506c": "IRS4506.X67",
    "send_return_first_name": "IRS4506.X8",
}

async def get_transcript_templates(api_client) -> List[Dict]:
    """Fetch available Transcript of Tax templates from Encompass Settings."""
    return await api_client.get(TRANSCRIPT_API_ENDPOINTS["list_templates"])

async def get_template_settings(api_client, template_id: str) -> Dict:
    """Get configured settings for a specific template (IVES info, tax years, etc.)."""
    endpoint = TRANSCRIPT_API_ENDPOINTS["get_template"].format(templateId=template_id)
    return await api_client.get(endpoint)

async def apply_transcript_template(api_client, loan_id: str, template_path: str) -> Dict:
    """Apply transcript template to loan using V3 Update Loan API."""
    endpoint = TRANSCRIPT_API_ENDPOINTS["apply_template"].format(loanId=loan_id)
    params = {
        "templateType": "transcriptRequest",
        "templatePath": template_path
    }
    return await api_client.patch(endpoint, params=params)

async def manage_transcript_records(
    api_client, 
    loan_id: str, 
    application_id: str, 
    action: str,  # add, update, delete, reorder, replace
    records: List[Dict]
) -> Dict:
    """Add/Update/Delete/Reorder transcript request records."""
    endpoint = TRANSCRIPT_API_ENDPOINTS["manage_transcripts"].format(
        loanId=loan_id, 
        applicationId=application_id
    )
    return await api_client.patch(endpoint, params={"action": action}, json=records)

async def populate_transcript_forms(
    api_client,
    loan_id: str, 
    application_id: str,
    borrower_type: str = "Borrower"
) -> Dict:
    """
    Populate 4506-C and 8821 forms for disclosure.
    
    Per SOP Video Notes Lines 158-179:
    - 4506-C: Tax transcript request with IVES participant (Xactus)
    - 8821: Halcyon consent form
    - Tax years: 12/31/2024, 12/31/2023, 12/31/2022
    """
    results = {"4506c": None, "8821": None}
    
    # Step 1: Apply 4506-C template 
    # This auto-populates 5a (Xactus) and 5d (AWM) info
    results["4506c"] = await apply_transcript_template(
        api_client, 
        loan_id, 
        "Public\\Templates\\4506-C Request for Transcript"
    )
    
    # Step 2: Apply 8821 Halcyon consent template
    results["8821"] = await apply_transcript_template(
        api_client, 
        loan_id, 
        "Public\\Templates\\8821 – Halcyon consent form"
    )
    
    return {
        "success": True,
        "forms_populated": ["4506-C", "8821"],
        "tax_years": TAX_YEARS,
        "ives_participant": "Xactus, LLC (0000304771)",
        "third_party_designee": "All Western Mortgage, Inc.",
        "details": results
    }
```

> **Note**: Using the API-based approach is preferred over direct field mapping as it:
> - Leverages pre-configured templates in Encompass Settings
> - Handles IVES Participant and Third Party Designee data automatically
> - Supports all form types (4506-C, 4506-T, 8821) consistently
> - Eliminates need for ~20+ field ID mappings

---

### G5: 2015 Itemization Validations 🚧
**Priority:** HIGH  
**Effort:** Medium  
**Status:** IMPLEMENTED (one UNKNOWN field - manual verification required)  
**Implementation:** `packages/shared/itemization_validator.py`, `agents/disclosure/subagents/preparation_agent/tools/itemization_tools.py`

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

**Related Fields Found:**
- Bona Fide Indicator: `NEWHUD.X1067`
- Itemize Fees on Line 802 Use LO Compensation Tool: `NEWHUD.X1139`
- Use Itemized Credits: `4796`
- Appraisal Fee Borr: `641`
- Appraisal Fee Seller: `581`
- Recording Fee Borr: `390`
- Recording Fee Seller: `587`
- Lender's Title Insurance Paid To: `NEWHUD.X805`
- Owner's Title Insurance Paid To: `NEWHUD.X804`
- Title Insurance Company Name: `411`

**Implementation Needed:**
```python
# packages/shared/itemization_validator.py
MANDATORY_CHECKBOXES = {
    "itemize_fees_when_printing": "UNKNOWN",  # ❌ NOT IN MASTER LIST - requires manual mapping
    "bona_fide": "NEWHUD.X1067",  # ✅ Found in master list
    "itemize_on_802": "NEWHUD.X1139",  # ✅ Found in master list
    "use_itemized_credits": "4796",  # ✅ Found in master list
}

MANDATORY_FEE_FIELDS = {
    "appraisal_fee_borr": "641",  # ✅ Found in master list
    "appraisal_fee_seller": "581",  # ✅ Found in master list
    "recording_fee_borr": "390",  # ✅ Found in master list
    "recording_fee_seller": "587",  # ✅ Found in master list
    "lender_title_insurance_paid_to": "NEWHUD.X805",  # ✅ Found in master list
    "owner_title_insurance_paid_to": "NEWHUD.X804",  # ✅ Found in master list
    "title_insurance_company": "411",  # ✅ Found in master list
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

### G6: Settlement Service Provider List (SSPL) 🚧
**Priority:** HIGH  
**Effort:** Medium  
**Status:** IMPLEMENTED (template/service field IDs pending - manual verification required)  
**Implementation:** `packages/shared/sspl_updater.py`, `agents/disclosure/subagents/preparation_agent/tools/sspl_tools.py`

**Video Notes Reference:** Lines 198-201
> "If templates not applied, click Apply Template -> select Settlement Service Provider template - Delete Pest Inspection, Home Inspection Services, Engineering Inspection, Land Survey - Populate fee boxes in Settlement Service Provider with LE Page 2 title fees"

**What's Missing:**
- Template detection logic (is template applied?)
- Template application automation
- Service deletion logic:
  - Delete: Pest Inspection, Home Inspection Services, Engineering Inspection, Land Survey
- Fee copy from LE Page 2 Section C (in CAPITAL letters)

**Related Fields Found:**
- Settlement Services Provider List Sent Date: `4014`

**Implementation Needed:**
```python
# packages/shared/sspl_updater.py
SSPL_FIELDS = {
    "sspl_sent_date": "4014",  # ✅ Found in master list
    "template_applied": "UNKNOWN",  # ❌ NOT IN MASTER LIST - requires manual mapping
    "service_list": "UNKNOWN",  # ❌ NOT IN MASTER LIST - requires manual mapping
}

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

### G7: Affiliate Business Arrangement Form 🚧
**Priority:** MEDIUM  
**Effort:** Low  
**Status:** IMPLEMENTED (all field IDs UNKNOWN - manual verification required)  
**Implementation:** `agents/disclosure/subagents/preparation_agent/tools/template_tools.py`

**Video Notes Reference:** Lines 85-86
> "If blank -> click on 'Apply Template' -> AWM Affiliate -> OK -> Mark Settlement and Purchase/Sale/Refinance boxes. All info will be auto populated"

**What's Missing:**
- Template detection (is form blank?) → `UNKNOWN` ❌
- AWM Affiliate template application → `UNKNOWN` ❌
- Settlement box marking → `UNKNOWN` ❌
- Purchase/Sale/Refinance box marking → `UNKNOWN` ❌

> **Note**: ABA form fields not found in master list - requires manual Encompass mapping

---

### G9: 1003 URLA - Lender Form (Denoter Form) Validations ✅
**Priority:** MEDIUM  
**Effort:** Medium  
**Status:** IMPLEMENTED (full USPS API integration - credentials pending)  
**Implementation:** `packages/shared/usps_validator.py`, `agents/disclosure/subagents/verification_agent/tools/form_validation_tools.py`

**Video Notes Reference:** Lines 19-48
> "Include lender information pages in borrower package - Subject property address - Verify in USPS - Estimated value - Appraisal value - Project type - Purpose of Loan - Occupancy"

**Related Fields Found:**
- Estimated/Appraised Value: `356` ✅
- Project Type (Subject Property Type): `1041` ✅
- Refinance Type (Loan Info Refi Purpose): `299` ✅
- Mortgage Lien Type (Lien Position): `420` ✅
- Amortization Type: `608` ✅
- Qual Rate: `1014` ✅
- TOTAL CREDITS: `CD3.X1506` ✅
- Homeownership Education: `URLA.X233` ✅

**What's Missing:**
- "Include lender info page in borrower package" checkbox → `UNKNOWN` ❌
- USPS address verification integration → **API SOLUTION AVAILABLE** ✅

---

#### 🎯 USPS Address Verification API (v3)

The USPS Addresses API validates and standardizes addresses per SOP requirement "Verify in USPS".

| API Endpoint | Purpose | Documentation |
|--------------|---------|---------------|
| `GET /addresses/v3/address` | Standardize & validate address (returns ZIP+4) | [USPS Address API](https://developer.usps.com/api/92) |
| `GET /addresses/v3/city-state` | Get city/state for a ZIP Code | Lookup utility |
| `GET /addresses/v3/zipcode` | Get ZIP Code for address/city/state | Lookup utility |

**API Base URLs:**
- Production: `https://apis.usps.com/addresses/v3`
- Testing: `https://apis-tem.usps.com/addresses/v3`

**Authentication:** OAuth2 (Client Credentials or Authorization Code)
- Token URL: `/oauth2/v3/token`
- Scope: `addresses`

**Address Standardization Request Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `streetAddress` | ✅ Yes | Building number + street name |
| `secondaryAddress` | No | Apt/Suite number |
| `city` | Conditional | City name (required if no ZIP) |
| `state` | ✅ Yes | 2-letter state code |
| `ZIPCode` | Conditional | 5-digit ZIP (required if no city) |
| `ZIPPlus4` | No | 4-digit ZIP+4 extension |

**Response Includes:**
- Standardized address with abbreviations
- Full ZIP+4 code
- DPV Confirmation (`Y`/`D`/`S`/`N`) - Delivery Point Validation
- Carrier route code
- Business indicator (`Y`/`N`)
- Vacant indicator (`Y`/`N`)
- CMRA indicator (Commercial Mail Receiving Agency)
- Address corrections/warnings

**DPV Confirmation Codes:**
| Code | Meaning |
|------|---------|
| `Y` | Address confirmed for primary + secondary numbers |
| `D` | Primary confirmed, secondary missing |
| `S` | Primary confirmed, secondary present but not confirmed |
| `N` | Both primary and secondary failed confirmation |

---

**Implementation Needed:**
```python
# packages/shared/usps_validator.py
from typing import Dict, Optional
import httpx

# USPS API Configuration
USPS_API_CONFIG = {
    "base_url": "https://apis.usps.com/addresses/v3",
    "test_url": "https://apis-tem.usps.com/addresses/v3",
    "token_url": "/oauth2/v3/token",
    "scope": "addresses",
}

# Encompass Address Field IDs
ADDRESS_FIELD_IDS = {
    # Subject Property Address
    "subject_street": "11",      # Subject Property Street Address
    "subject_city": "12",        # Subject Property City
    "subject_state": "14",       # Subject Property State
    "subject_zip": "15",         # Subject Property Zip Code
    # Borrower Present Address
    "borr_street": "FR0104",     # Borrower Present Address
    "borr_city": "FR0106",       # Borrower Present City
    "borr_state": "FR0107",      # Borrower Present State
    "borr_zip": "FR0108",        # Borrower Present Zip
}

LENDER_FORM_FIELDS = {
    "estimated_value": "356",  # ✅ Found
    "appraised_value": "356",  # ✅ Found  
    "project_type": "1041",  # ✅ Found
    "refinance_type": "299",  # ✅ Found
    "lien_position": "420",  # ✅ Found
    "amortization_type": "608",  # ✅ Found
    "qual_rate": "1014",  # ✅ Found
    "total_credits": "CD3.X1506",  # ✅ Found
    "homeownership_ed": "URLA.X233",  # ✅ Found
    "include_lender_info_checkbox": "UNKNOWN",  # ❌ NOT IN MASTER LIST
}

class USPSAddressValidator:
    """USPS Address API v3 client for address validation."""
    
    def __init__(self, client_id: str, client_secret: str, use_test: bool = False):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = USPS_API_CONFIG["test_url"] if use_test else USPS_API_CONFIG["base_url"]
        self.access_token: Optional[str] = None
    
    async def get_access_token(self) -> str:
        """Get OAuth2 access token from USPS."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{USPS_API_CONFIG['token_url']}",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": USPS_API_CONFIG["scope"],
                }
            )
            data = response.json()
            self.access_token = data["access_token"]
            return self.access_token
    
    async def validate_address(
        self,
        street_address: str,
        city: Optional[str] = None,
        state: str = None,
        zip_code: Optional[str] = None,
        secondary_address: Optional[str] = None,
    ) -> Dict:
        """
        Validate and standardize address using USPS API.
        
        Per SOP: "Subject property address - Verify in USPS"
        
        Returns:
            {
                "is_valid": bool,
                "standardized_address": {...},
                "dpv_confirmation": "Y"|"D"|"S"|"N",
                "zip_plus_4": "12345-6789",
                "is_business": bool,
                "is_vacant": bool,
                "warnings": [...],
                "corrections": [...]
            }
        """
        if not self.access_token:
            await self.get_access_token()
        
        params = {
            "streetAddress": street_address,
            "state": state,
        }
        if city:
            params["city"] = city
        if zip_code:
            params["ZIPCode"] = zip_code
        if secondary_address:
            params["secondaryAddress"] = secondary_address
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/address",
                params=params,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                address = data.get("address", {})
                additional = data.get("additionalInfo", {})
                
                return {
                    "is_valid": True,
                    "standardized_address": {
                        "street": address.get("streetAddress"),
                        "secondary": address.get("secondaryAddress"),
                        "city": address.get("city"),
                        "state": address.get("state"),
                        "zip_code": address.get("ZIPCode"),
                        "zip_plus_4": address.get("ZIPPlus4"),
                    },
                    "dpv_confirmation": additional.get("DPVConfirmation"),
                    "zip_plus_4": f"{address.get('ZIPCode')}-{address.get('ZIPPlus4')}" if address.get("ZIPPlus4") else address.get("ZIPCode"),
                    "is_business": additional.get("business") == "Y",
                    "is_vacant": additional.get("vacant") == "Y",
                    "carrier_route": additional.get("carrierRoute"),
                    "warnings": data.get("warnings", []),
                    "corrections": data.get("corrections", []),
                }
            
            elif response.status_code == 404:
                error = response.json().get("error", {})
                return {
                    "is_valid": False,
                    "error": error.get("message", "Address not found"),
                    "standardized_address": None,
                }
            
            else:
                return {
                    "is_valid": False,
                    "error": f"USPS API error: {response.status_code}",
                    "standardized_address": None,
                }

async def verify_subject_property_address(
    usps_client: USPSAddressValidator,
    loan_data: Dict
) -> Dict:
    """
    Verify subject property address per SOP requirement.
    
    Video Notes Line 25: "Subject property address - Verify in USPS"
    """
    result = await usps_client.validate_address(
        street_address=loan_data.get("subject_street"),
        city=loan_data.get("subject_city"),
        state=loan_data.get("subject_state"),
        zip_code=loan_data.get("subject_zip"),
    )
    
    validation_result = {
        "field": "Subject Property Address",
        "original": f"{loan_data.get('subject_street')}, {loan_data.get('subject_city')}, {loan_data.get('subject_state')} {loan_data.get('subject_zip')}",
        "usps_verified": result["is_valid"],
        "dpv_status": result.get("dpv_confirmation"),
    }
    
    if result["is_valid"]:
        std = result["standardized_address"]
        validation_result["standardized"] = f"{std['street']}, {std['city']}, {std['state']} {result['zip_plus_4']}"
        validation_result["needs_update"] = validation_result["original"] != validation_result["standardized"]
    else:
        validation_result["error"] = result.get("error")
    
    return validation_result
```

> **Note**: USPS API requires registration at [USPS Developer Portal](https://developer.usps.com/) to obtain OAuth2 credentials.

---

### G10: 1003 URLA Part 1 Validations 🚧
**Priority:** MEDIUM  
**Effort:** Low  
**Status:** IMPLEMENTED (citizenship field ID UNKNOWN - manual verification required)  
**Implementation:** `agents/disclosure/subagents/verification_agent/tools/form_validation_tools.py`

**Video Notes Reference:** Lines 49-67
> "Citizenship - Marital Status - Mailing address: same as current - Military Service - Language Preference"

**Related Fields Found:**
- Marital Status: `52` (Borr Marital Status) ✅
- Co-Borr Marital Status: `84` ✅
- Mailing Same as Present: `1819` ✅
- Military Service: `URLA.X13` (Borr Military Service Indicator) ✅
- Co-Borr Military Service: `URLA.X14` ✅
- Language Preference: `URLA.X21` ✅
- Co-Borr Language Preference: `URLA.X22` ✅
- Borrower Mailing Addr: `1416`
- Borrower Mailing City: `1417`
- Borrower Mailing State: `1418`
- Borrower Mailing Zip: `1419`

**What's Missing:**
- Citizenship validation → `UNKNOWN` ❌ (not found in master list)
- Marital Status validation → Field: `52` ✅
- "Same as Current" checkbox → Field: `1819` ✅
- Former Address fields → `UNKNOWN` ❌
- Military Service field (always "yes" for VA loans) → Field: `URLA.X13` ✅
- Language Preference field → Field: `URLA.X21` ✅

---

### G11: 1003 URLA Part 4 & LO Info Validations ✅
**Priority:** MEDIUM  
**Effort:** Medium  
**Status:** IMPLEMENTED (NMLS Consumer Access API pending)  
**Implementation:** `agents/disclosure/subagents/verification_agent/tools/form_validation_tools.py`

**Video Notes Reference:** Lines 73-84
> "Section 5. Declarations - Borrower/Co-Borrower questions must have answers - Loan Originator NMLSR ID# Must be 14210 - Go to NMLS Consumer Access - Check for Branch Location - Verify if Loan Originator Name is same"

**Related Fields Found:**
- NMLS Loan Originator ID: `3238` / `HMDA.X86`
- Lender NMLS ID: `CD5.X12`
- Lender Contact NMLSID: `CD5.X15`
- NMLS Branch Location NMLS ID: `NMLS X9`
- NMLS Branch Manager NMLS ID: `NMLS X8`
- Loan Estimate - Lender Loan Officer NMLS ID: `LE3 X5`
- Loan Estimate - Mortgage Broker Loan Officer NMLS ID: `LE3.X10`

**What's Missing:**
- Section 5 Declarations: All questions answered validation
- Section 8 Demographic Information: Check if provided
- LO NMLS ID must be 14210 validation → Field: `3238`
- External NMLS Consumer Access API verification
- LO branch location verification → Field: `NMLS X9`
- LO name match with NMLS

---

### G12: Borrower Summary - Origination Validations 🚧
**Priority:** MEDIUM  
**Effort:** Medium  
**Status:** IMPLEMENTED (2 field IDs UNKNOWN - manual verification required)  
**Implementation:** `agents/disclosure/subagents/verification_agent/tools/form_validation_tools.py`

**Video Notes Reference:** Lines 87-106
> "Channel - Current Status has to be Active Loan - Vesting Type - Individual - Consent valid days and reason for authorizing consent should not be blank - Company's Information - Company's Agent Information Should be CoreLogic Inc."

**Related Fields Found:**
- Loan Info Channel: `2626` ✅
- Loan Status: `1393` ✅
- Borrower Vesting Type: `4008` ✅
- Co-Borrower Vesting Type: `4009` ✅
- SSN Verification Company Agent Name: `3297` / `3537` ✅
- eConsent Date: `3983` ✅
- Broker Lender Name: `315`
- Broker Lender Addr: `319`
- Broker Lender City: `313`

**What's Missing:**
- Channel = "Bank" validation → Field: `2626` ✅
- Current Status = "Active Loan" validation → Field: `1393` ✅
- Vesting Type = "Individual" validation → Field: `4008` ✅
- SSN Verification Statement validation → Field: `3297` / `3537` ✅
- Consent validity (60 days) and reason not blank → `UNKNOWN` ❌ (related: `3983`)
- Company's Information (Lender/Broker Data button) → Partial fields found
- Company's Agent Information = "CoreLogic Inc." validation → `UNKNOWN` ❌
- CoreLogic address: "40 Pacifica Suite 900" → `UNKNOWN` ❌

---

### G13: Disclosure Summary Review 🚧
**Priority:** MEDIUM  
**Effort:** Low  
**Status:** IMPLEMENTED (field ID UNKNOWN - manual review required)  
**Implementation:** `agents/disclosure/subagents/verification_agent/tools/form_validation_tools.py`

**Video Notes Reference:** Line 107-108
> "Look out for Comments/Notes, usually instructions, more info about fees, lender, etc."

**What's Missing:**
- Automated reading of Comments/Notes section
- Flagging of special instructions
- Detection of fee or lender credit mentions

---

### G14: Credit/Lender Credit Validation ✅
**Priority:** MEDIUM  
**Effort:** Medium  
**Status:** IMPLEMENTED (full field mapping)  
**Implementation:** `agents/disclosure/subagents/verification_agent/tools/form_validation_tools.py`

**Video Notes Reference:** Lines 45-48 (SOP)
> "For refinance, check for 'other lender credit'. For purchase, check for seller credit and lender credit."

**Related Fields Found:**
- Lender Credits: `HMDA.X80` / `CD2.XSTLC`
- CD Last Disclosed Lender Credits: `CD2.XLDLCR`
- Closing disclosure Lender Credits At closing: `CD2.X1`
- Disclose Lender Credits applied: `CD2.X2`
- Fee Details - Line 804 - Seller Credit: `NEWHUD2.X1119`
- Fee Details - Line 808 - Seller Credit: `NEWHUD2.X1251`
- Fees Line 802 Seller Credit/Points: `NEWHUD.X780`
- Loan Estimate Adjustments and Other Credits: `LE2.X4`

**What's Missing:**
- Credit type validation by loan purpose:
  - Refinance: "Other Lender Credit" check
  - Purchase: Seller Credit + Lender Credit check
- Field IDs for various credit types ✅ Most found above

---

### G15: Consent Validity 60 Days 🚧
**Priority:** MEDIUM  
**Effort:** Low  
**Status:** IMPLEMENTED (consent reason field ID UNKNOWN - manual verification required)  
**Implementation:** `agents/disclosure/subagents/verification_agent/tools/form_validation_tools.py`

**Video Notes Reference:** Lines 95 (related SOP context)
> "Consent valid days should not be blank... should be within 60 days"

**What's Missing:**
- Consent date field ID
- 60-day calculation from consent date
- Validation that reason for consent is not blank

**Related Fields Found:**
- eConsent Date: `3983`
- 2015 Borrower Consent when eDisclosure was sent - 1: `EDISCLOSED2015TRK.eDisclosureBorrowerConsent1`
- 2015 Borrower Consent when eDisclosure was sent - 2: `EDISCLOSED2015TRK.eDisclosureBorrowerConsent2`
- State Disc - Borrower Consent Type: `DISCLOSURE X199`
- eConsent Borrower IP Address Pair 1: `3986`
- eConsent Borrower Source Pair 1: `3987`

**Implementation Needed:**
```python
CONSENT_VALIDITY_DAYS = 60
CONSENT_FIELDS = {
    "econsent_date": "3983",  # ✅ Found in master list
    "disclosure_consent_1": "EDISCLOSED2015TRK.eDisclosureBorrowerConsent1",  # ✅ Found
    "disclosure_consent_2": "EDISCLOSED2015TRK.eDisclosureBorrowerConsent2",  # ✅ Found
    "borrower_consent_type": "DISCLOSURE X199",  # ✅ Found in master list
    "consent_validity_days_field": "UNKNOWN",  # ❌ NOT IN MASTER LIST - requires manual mapping
    "consent_reason_field": "UNKNOWN",  # ❌ NOT IN MASTER LIST - requires manual mapping
}

def check_consent_validity(loan_id: str) -> Dict:
    """Check if consent is within 60 days and reason is provided."""
    pass
```

---

### G16: Audit Exception 26.4 ✅
**Priority:** MEDIUM  
**Effort:** Low  
**Status:** IMPLEMENTED (integrated into order flow)  
**Implementation:** `packages/shared/audit_filter.py`, `agents/disclosure/subagents/send_agent/tools/order_tools.py`

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

### G17: Company License #204 🚧
**Priority:** MEDIUM  
**Effort:** Low  
**Status:** IMPLEMENTED (field ID UNKNOWN - manual verification required)  
**Implementation:** `agents/disclosure/subagents/verification_agent/tools/form_validation_tools.py`

**SOP Reference:** Page 6
> "For all state Initial Disclosures, ensure that Company License #204 is updated in ENC by navigating to: Tools tab → File Contact → Category/Role → Lender"

**What's Missing:**
- Validation that Company License #204 is present
- Field location identification

---

## LOW-PRIORITY GAPS (Tier 3)

### G18: RegZ-LE Additional Fields 🚧
**Priority:** LOW  
**Effort:** Low  
**Status:** IMPLEMENTED (2 field IDs UNKNOWN - manual verification required)  
**Implementation:** `packages/shared/regz_le_updater.py`

**Video Notes Reference:** Lines 137-157
> "1st payment date is automatically updated - If loan has buydown, populate Buydown Mortgage - 0% payment option blank - Interest Days/Days in a Year 360/360 - Number of Days... is 365"

**Related Fields Found:**
- First Payment Date: `682`
- Loan Info Buydown: `425`
- Loan Info Buydown Terms: `1557`
- Temporary Buydown: `4645`
- Freddie Mac Buydown Contributor: `CASASRN.X141`
- Prepay Penalty: `2216`
- Prepayment Penalty Period: `HMDA.X82`
- REGZ Prepay Penalty Mths Hard Prepayment Period: `3536`

**What's Missing:**
- 1st Payment Date auto-update validation
- Buydown fields when marked:
  - Buydown box marked: `425` ✅
  - Contributor: `CASASRN.X141` ✅
  - Rate and Term: `1557` ✅
  - Disbursement: `UNKNOWN` ❌
- 0% Payment Option = blank validation: `UNKNOWN` ❌
- Prepayment Penalty tab fields (Type, Period, %): Partial - `2216`, `HMDA.X82`, `3536` ✅
- "Number of Days (Biweekly, Interim Interest, Classic HELOC)" = 365 field: `UNKNOWN` ❌

---

### G19: Blend Integration ORGID ✅
**Priority:** LOW  
**Effort:** Low  
**Status:** IMPLEMENTED (read-only check - manual verification recommended)  
**Implementation:** `agents/disclosure/subagents/preparation_agent/tools/blend_tools.py`

**Video Notes Reference:** Lines 213-215
> "ORGID has to be updated - Depends on LO"

**Related Fields Found:**
- Company - Users Organization Code: `ORGID`

**Notes:**
- Blend-specific, may be auto-populated
- Field ID confirmed: `ORGID`
- Low priority for MVP

---

### G20: eFolder Product Selection 🚧
**Priority:** LOW  
**Effort:** Medium  
**Status:** IMPLEMENTED (PMI Disclosure checkbox field ID UNKNOWN - manual verification required)  
**Implementation:** `agents/disclosure/subagents/preparation_agent/tools/efolder_tools.py`

**Video Notes Reference:** Lines 216-226
> "If loan is conventional -> Generic All Fixed Rate Conventional 1st Lien Loans -> Order eDisclosures - In eDisclosure package (initial disclosure), if LTV < 80%, uncheck Fixed Rate Conventional PMI Disclosure"

**Related Fields Found:**
- LTV: `353`
- Combined LTV: `976`
- CLTV (HMDA): `HMDA.X37`
- Lien Position: `420`

**What's Missing:**
- Appropriate loan product template selection
- LTV-based exclusions:
  - If LTV < 80%: Uncheck "Fixed Rate Conventional PMI Disclosure"
  - PMI Disclosure checkbox field: `UNKNOWN` ❌ NOT IN MASTER LIST

---

### G21: Post-Disclosure LO Review Workflow 🚧
**Priority:** LOW  
**Effort:** High  
**Status:** IMPLEMENTED (manual workflow - email must be sent manually)  
**Implementation:** `agents/disclosure/subagents/send_agent/tools/review_tools.py`

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
**Status:** NOT IMPLEMENTED (Texas excluded from MVP)

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

| Field | Video Line | Field ID | Status | Notes |
|-------|------------|----------|--------|-------|
| Estimated Value | 26 | `356` | ✅ ID Found | Same as Appraised Value |
| Appraised Value | 26 | `356` | ✅ ID Found | Confirmed in master list |
| Project Type | 27 | `1041` | ✅ ID Found | Subject Property Type |
| Refinance Type | 30 | `299` | ✅ ID Found | Loan Info Refi Purpose |
| Mortgage Lien Type | 31 | `420` | ✅ ID Found | Lien Position |
| Amortization Type | 32 | `608` | ✅ ID Found | Confirmed |
| Qual Rate | 37 | `1014` | ✅ ID Found | **Corrected** (was 1825 - that's Print 2003 Appl) |
| TOTAL CREDITS | 45 | `CD3.X1506` | ✅ ID Found | Total Adjustments And Other Credits |
| Homeownership Ed (L5) | 46 | `URLA.X233` | ✅ ID Found | Borrower Homeownership Counseling Completion Date |

### Missing 1003 URLA Part 1 Fields

| Field | Video Line | Field ID | Status | Notes |
|-------|------------|----------|--------|-------|
| Citizenship | 55 | `UNKNOWN` | ❌ Not Found | Requires manual mapping |
| Marital Status | 56 | `52` | ✅ ID Found | Borr Marital Status |
| Mailing Same as Current | 64 | `1819` | ✅ ID Found | **Corrected** (FR0108 is Borr Present Zip) |
| Military Service | 65-66 | `URLA.X13` | ✅ ID Found | **Corrected** (264 not found - URLA.X13 is Borr Military Service Indicator) |
| Language Preference | 67 | `URLA.X21` | ✅ ID Found | Borr Language Preference |

### Missing Borrower Summary - Origination Fields

| Field | Video Line | Field ID | Status | Notes |
|-------|------------|----------|--------|-------|
| Channel = Bank | 89 | `2626` | ✅ ID Found | Loan Info Channel |
| Current Status = Active | 90 | `1393` | ✅ ID Found | Loan Status |
| Vesting Type | 91 | `4008` | ✅ ID Found | Borrower Vesting Type |
| SSN Verification | 95 | `3297` / `3537` | ✅ ID Found | Social Security Number Verification Company Agent Name |
| Consent Valid Days | 95 | `UNKNOWN` | ❌ Not Found | Requires manual mapping (related: eConsent Date `3983`) |
| Company's Agent = CoreLogic | 99 | `UNKNOWN` | ❌ Not Found | Requires manual mapping

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

**✅ RESOLVED - Found in Master List:**
- ~~Vesting Type field~~ → `4008` (Borrower Vesting Type)
- ~~SSN Verification Statement field~~ → `3297` / `3537` (SSN Verification Company Agent Name)
- ~~Homeownership Education (L5) field~~ → `URLA.X233` (Borrower Homeownership Counseling Completion Date)
- ~~TOTAL CREDITS field~~ → `CD3.X1506` (Total Adjustments And Other Credits)
- ~~Language Preference field~~ → `URLA.X21` (Borr Language Preference)

**❌ UNKNOWN - Requires Manual Mapping in Encompass:**
| Field | Gap Reference | Notes |
|-------|---------------|-------|
| FACT Act Material Terms Credit checkbox | G2 | Critical - Credit disclosure won't print |
| FACT Act Credit Score Disclosure checkbox | G2 | Critical - Credit disclosure won't print |
| Citizenship | G10 | 1003 URLA Part 1 validation |
| Consent Validity Days | G15 | Related to `3983` (eConsent Date) |
| Consent Reason | G15 | Must not be blank |
| Company's Agent = CoreLogic | G12 | Company's Agent Information fields |
| Itemize Fees When Printing checkbox | G5 | 2015 Itemization validation |
| SSPL Template Applied flag | G6 | Template detection logic |
| SSPL Service List fields | G6 | For service deletion automation |
| Home Counseling Agency List fields | G3 | For agency selection |
| PMI Disclosure checkbox | G20 | LTV-based exclusion |
| 0% Payment Option field | G18 | RegZ-LE validation |
| Buydown Disbursement field | G18 | RegZ-LE validation |
| Days in Year (HELOC) field | G18 | 365 days validation |

**✅ API SOLUTION AVAILABLE (No Field Mapping Needed):**
| Field | Gap Reference | API Solution |
|-------|---------------|--------------|
| 4506-C Section 5a fields (IVES participant) | G4 | [V3 Request for Transcript of Tax APIs](https://developer.icemortgagetechnology.com/developer-connect/reference/v3-patch-request-for-transcript-of-tax) |
| 4506-C Section 5d fields (Third Party Designee) | G4 | [V3 Request for Transcript of Tax APIs](https://developer.icemortgagetechnology.com/developer-connect/reference/v3-patch-request-for-transcript-of-tax) |
| 8821 Form fields (Halcyon consent) | G4 | [V3 Transcript of Tax Templates](https://developer.icemortgagetechnology.com/developer-connect/reference/v3-get-transcript-of-tax-template) |
| Tax Years (12/31/2024, etc.) | G4 | Configurable via transcript templates |

---

## Field ID Corrections Made

| Original Field ID | Corrected Field ID | Description |
|-------------------|-------------------|-------------|
| `1825` (Qual Rate) | `1014` | 1825 is "Print 2003 Appl", not Qual Rate |
| `FR0108` (Mailing Same) | `1819` | FR0108 is "Borr Present Zip", 1819 is "Borr Mailing Addr Same as Present" |
| `264` (Military Service) | `URLA.X13` | 264 not found in master list, URLA.X13 is "Borr Military Service Indicator" |
| `1821` (Appraised Value) | `356` | 356 is the correct field for Appraised Value |

---

*Last Updated: December 8, 2025*  
*Version: 2.2 (Field ID Cross-Reference with Master List)*
