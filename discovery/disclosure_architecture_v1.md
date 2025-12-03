# Disclosure Agent Architecture (Refined)

## Document Info
- **Created**: November 28, 2025
- **Based On**: SOP Analysis, MVP Boilerplate, Gap Analysis
- **Owner**: Naomi

---

## 1. Overview

The Disclosure Agent handles the preparation and distribution of Closing Disclosures (Initial CD, COC CD) **before** the loan reaches the Draw Docs stage. This is a **simpler workflow** compared to Draw Docs, focused on field validation rather than document verification.

### Key Characteristics
- **No document verification** - just checks if fields exist in Encompass
- **Simpler process** - fewer steps, less state-specific complexity
- **Key calculation**: Mortgage Insurance
- **Key monitoring**: Fee tolerance and APR impact
- **Output**: CD ready for borrower acknowledgment

### Relationship to Draw Docs
```
┌─────────────────────────────────────────────────────────────────────────┐
│                          LOAN TIMELINE                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DISCLOSURE WORKFLOW                    DRAW DOCS WORKFLOW               │
│  ────────────────────                   ────────────────────             │
│  [Processor completes file]             [CTC + CD Approved + ACK'd]     │
│           ↓                                       ↓                      │
│  [Disclosure Agent]                     [Draw Docs Agent]                │
│           ↓                                       ↓                      │
│  [Initial CD created]                   [Verify against docs]            │
│           ↓                                       ↓                      │
│  [Borrower signs/ACKs CD]               [Order closing package]          │
│           ↓                                       ↓                      │
│  [3-day waiting period]                 [Send to title/escrow]           │
│           ↓                                                              │
│  [CD Approved] ──────────────────────────▶ HANDOFF TO DRAW DOCS         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Entry Conditions (Prerequisites)

Before Disclosure processing begins:

| Condition | Check Method | Blocking |
|-----------|--------------|----------|
| File in CD Request queue | Pipeline/Milestone | ✅ Yes |
| Required fields populated | Field existence check | ⚠️ Flag missing |
| Loan terms locked | Rate Lock status | ⚠️ Warn if unlocked |
| Processor marked ready | Task/Status field | ✅ Yes |

**Note**: Unlike Draw Docs, we don't verify documents - we trust that the processor has populated fields correctly. We just check that fields EXIST.

---

## 3. Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         DISCLOSURE ORCHESTRATOR                                  │
│                                                                                  │
│  Coordinates agents, manages state, routes for review                           │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────────┐   ┌───────────────────────┐   ┌────────────────────────┐
│ VERIFICATION      │──▶│ PREPARATION AGENT     │──▶│ REQUEST REVIEWS        │
│ AGENT             │   │                       │   │ AGENT                  │
│                   │   │ • Field cleanup       │   │                        │
│ • Field existence │   │ • Normalize values    │   │ • Route to LO          │
│ • Required checks │   │ • MI calculation      │   │ • Send email + attach  │
│ • Flag missing    │   │ • Populate CD fields  │   │ • Track ACK status     │
│                   │   │ • Fee tolerance       │   │                        │
│                   │   │ • APR calculation     │   │                        │
└───────────────────┘   └───────────────────────┘   └────────────────────────┘
```

---

## 4. Agent Specifications

### 4.1 Verification Agent

**Purpose**: Check that all required fields exist and are populated before disclosure preparation.

#### Key Difference from Draw Docs
| Draw Docs Verification | Disclosure Verification |
|------------------------|------------------------|
| Verifies fields AGAINST documents | Checks fields EXIST only |
| Cross-references multiple sources | Trusts processor input |
| Complex document extraction | Simple field presence check |
| 35+ documents to review | No document review |

#### Responsibilities

1. **Field Existence Checks**
   - Check all required Encompass fields are populated
   - NO verification against documents
   - Just: "Is this field filled in? Yes/No"

2. **Required Field Categories**

```python
DISCLOSURE_REQUIRED_FIELDS = {
    "borrower_info": [
        "borrower_name",
        "borrower_ssn",
        "borrower_address",
        "coborrower_name",  # If applicable
        "coborrower_ssn",   # If applicable
    ],
    "property_info": [
        "property_address",
        "property_type",
        "occupancy_type",
        "appraised_value",
        "sales_price",  # Purchase only
    ],
    "loan_info": [
        "loan_amount",
        "interest_rate",
        "loan_term",
        "loan_type",  # Conv/FHA/VA/USDA
        "loan_purpose",
        "amortization_type",
    ],
    "contact_info": [
        "settlement_agent",
        "title_company",
        "escrow_company",
    ],
    "fee_info": [
        "origination_fees",
        "third_party_fees",
        "title_fees",
        "prepaids",
        "escrow_reserves",
    ]
}
```

3. **Output**

```python
class VerificationResult:
    all_required_present: bool
    missing_fields: List[str]
    warnings: List[str]  # Fields that exist but may be incorrect format
    
# Example output
{
    "all_required_present": False,
    "missing_fields": [
        "escrow_company.phone",
        "flood_insurance.premium"  # If in flood zone
    ],
    "warnings": [
        "property_address format may be inconsistent"
    ]
}
```

4. **Decision Logic**
   ```python
   if critical_fields_missing:
       return HALT, request_processor_update(missing_fields)
   elif optional_fields_missing:
       return CONTINUE_WITH_WARNINGS, log_warnings(missing_fields)
   else:
       return PROCEED
   ```

#### Tools Used
```python
check_field_existence(loan_id, field_ids[])
get_loan_type(loan_id)  # To determine which fields are required
log_missing_fields(loan_id, fields[])
request_field_update(loan_id, fields[], assign_to="processor")
```

---

### 4.2 Preparation Agent

**Purpose**: Clean up fields, calculate MI, populate CD, handle fee tolerance.

This is the **core agent** for disclosure - handles the main work.

#### Responsibilities

1. **Field Cleanup & Normalization**
   - Standardize formats (addresses, phone numbers, names)
   - Remove extra whitespace
   - Fix common formatting issues

2. **Mortgage Insurance Calculation** ⭐ (Key Disclosure Task)

```python
class MICalculator:
    """
    Calculate Mortgage Insurance based on loan type
    """
    
    def calculate(self, loan_context):
        loan_type = loan_context.loan_type
        ltv = loan_context.ltv
        
        if loan_type == "Conventional":
            return self.calculate_conventional_mi(loan_context)
        elif loan_type == "FHA":
            return self.calculate_fha_mip(loan_context)
        elif loan_type == "VA":
            return self.calculate_va_funding_fee(loan_context)
        elif loan_type == "USDA":
            return self.calculate_usda_guarantee(loan_context)
    
    def calculate_conventional_mi(self, ctx):
        """
        Conventional MI (when LTV > 80%)
        
        From MI Certificate:
        - Upfront PMI: Single Premium only
        - 1st Renewal: % and months (usually 120)
        - 2nd Renewal: Usually 0.20%, remaining term
        - Renewal Calc: Declining Renewals UNCHECKED
        - Cancel at: 78% LTV (except 2+ units → no cutoff)
        """
        if ctx.ltv <= 80:
            return None
        
        return {
            "upfront": ctx.mi_cert.single_premium,
            "monthly": ctx.mi_cert.monthly_rate * ctx.loan_amount / 12,
            "first_renewal_months": ctx.mi_cert.renewal_months or 120,
            "first_renewal_rate": ctx.mi_cert.renewal_rate,
            "second_renewal_rate": 0.20,
            "cancel_at_ltv": None if ctx.units >= 2 else 78.0
        }
    
    def calculate_fha_mip(self, ctx):
        """
        FHA MIP
        
        - UFMIP: Always 1.75%
        - Annual MIP: Per FHA chart (verify with Approval Final)
        - Renewal Calc: "Calculate based on remaining balance"
        
        Action: Click "GET MI" button (in Draw Docs, but calc here)
        """
        ufmip = ctx.loan_amount * 0.0175
        
        # Annual MIP rate from FHA chart
        annual_mip_rate = self.get_fha_mip_rate(
            ctx.loan_term, 
            ctx.ltv, 
            ctx.loan_amount
        )
        
        return {
            "upfront": ufmip,
            "annual_rate": annual_mip_rate,
            "monthly": ctx.loan_amount * annual_mip_rate / 12,
            "renewal_calc": "remaining_balance",
            "financed": ctx.ufmip_financed  # Usually yes
        }
    
    def calculate_va_funding_fee(self, ctx):
        """
        VA Funding Fee (after April 7, 2023)
        
        First Use:
        - Purchase <5% down: 2.15%
        - Purchase 5-10% down: 1.50%
        - Purchase >=10% down: 1.25%
        - Cash-Out: 2.15%
        - IRRRL: 0.50%
        
        Subsequent Use:
        - Purchase <5% down: 3.30%
        - Purchase 5-10% down: 1.50%
        - Purchase >=10% down: 1.25%
        - Cash-Out: 3.30%
        - IRRRL: 0.50%
        """
        if ctx.va_funding_fee_exempt:
            return {"exempt": True, "fee": 0}
        
        rate = self.get_va_funding_rate(
            ctx.purpose,
            ctx.down_payment_percent,
            ctx.va_subsequent_use
        )
        
        return {
            "rate": rate,
            "fee": ctx.loan_amount * rate,
            "financed": ctx.va_fee_financed
        }
    
    def calculate_usda_guarantee(self, ctx):
        """
        USDA Guarantee Fee
        
        - Upfront: Per USDA factor
        - Annual: Per USDA factor
        - Technology Fee: $25 (commitments on/after 1/1/2020)
        """
        return {
            "upfront": ctx.loan_amount * ctx.usda_upfront_factor,
            "annual": ctx.loan_amount * ctx.usda_annual_factor,
            "technology_fee": 25 if ctx.commitment_date >= "2020-01-01" else 0
        }
```

3. **CD Field Population**

```python
CD_FIELDS = {
    "page_1": {
        "closing_info": [
            "cd_date_issued",
            "settlement_agent_name",
            "file_number"
        ],
        "loan_info": [
            "loan_term_years",
            "purpose",
            "product_type"
        ],
        "property": [
            "address",
            "appraised_value",
            "sales_price"
        ],
        "loan_type": [
            "loan_id",
            "mic_number"  # FHA/VA Case# or MI Cert#
        ],
        "transaction_info": [
            "borrower_info",
            "seller_info",
            "lender_info"
        ],
        "loan_terms": [
            "loan_amount",
            "interest_rate",
            "monthly_pi"
        ],
        "projected_payments": [
            "monthly_mi",
            "estimated_escrow",
            "estimated_taxes_insurance"
        ]
    },
    "page_2": {
        "section_a": "origination_charges",
        "section_b": "services_not_shopped",
        "section_c": "services_shopped",
        "section_d": "total_loan_costs",
        "section_e": "taxes_govt_fees",
        "section_f": "prepaids",
        "section_g": "escrow_reserves",
        "section_h": "other",
        "section_i": "total_other_costs",
        "section_j": "total_closing_costs"
    },
    "page_3": {
        "section_k_m": "due_from_to_borrower_seller",
        "section_l_n": "paid_by_borrower_seller",
        "cash_to_close": "calculated"
    },
    "page_4": {
        "loan_disclosures": [
            "assumption",
            "demand_feature",
            "negative_amortization",
            "partial_payments"
        ],
        "escrow_section": "from_aggregate_setup"
    },
    "page_5": {
        "apr": "calculated",
        "contact_info": "from_file_contacts"
    }
}
```

4. **Fee Tolerance Calculation**

```python
class FeeToleranceCalculator:
    """
    Compare LE fees vs CD fees to determine tolerance violations
    """
    
    ZERO_TOLERANCE = [
        # Section A - Cannot increase at all
        "origination_fee",
        "discount_points",
        "any_fee_not_on_le"
    ]
    
    TEN_PERCENT_TOLERANCE = [
        # Section B - Can increase up to 10% in aggregate
        # (When borrower uses provider from SPL)
        "appraisal_fee",
        "credit_report_fee",
        "flood_cert_fee",
        "tax_service_fee",
        "title_services"  # If on SPL and borrower used SPL provider
    ]
    
    NO_TOLERANCE = [
        # Section C - Borrower shopped, no protection
        "title_services"  # If borrower chose own provider
    ]
    
    def calculate(self, loan_id, le_fees, cd_fees):
        """
        Returns cure amount needed (if any)
        """
        zero_tol_increase = self.check_zero_tolerance(le_fees, cd_fees)
        ten_tol_increase = self.check_ten_tolerance(le_fees, cd_fees)
        
        cure_needed = zero_tol_increase + max(0, ten_tol_increase - (le_total_b * 0.10))
        
        return {
            "zero_tolerance_violation": zero_tol_increase,
            "ten_percent_violation": ten_tol_increase,
            "cure_amount": cure_needed,
            "apply_to": "lender_credit" if cure_needed > 0 else None
        }
```

5. **APR Impact Assessment**

```python
class APRCalculator:
    """
    Calculate APR and assess impact of changes
    """
    
    APR_FEES = {
        "include": [
            "origination_fee",
            "discount_points",
            "ufmip",
            "monthly_mi",
            "appraisal_fee_r3_amc"  # Only R3 AMC
        ],
        "exclude": [
            "credit_report",
            "title_fees",  # Some excluded per CFPB
            "recording",
            "section_f",  # Except prepaid interest
            "section_g",  # Except monthly MI
            "section_h"
        ]
    }
    
    THREE_DAY_WAIT_TRIGGERS = [
        {"type": "apr_increase", "threshold": 0.00125},  # >0.125%
        {"type": "product_change", "examples": [
            "Jumbo ↔ Conforming",
            "Conventional ↔ Government",
            "FHA ↔ VA",
            "Fixed ↔ ARM"
        ]},
        {"type": "prepayment_penalty_added"}
    ]
    
    def calculate_apr(self, loan_context):
        """Calculate APR based on APR-includable fees"""
        pass
    
    def check_apr_impact(self, initial_cd_apr, current_apr):
        """
        Check if APR change triggers 3-day wait
        """
        increase = current_apr - initial_cd_apr
        
        if increase > 0.00125:  # 0.125%
            return {
                "requires_3_day_wait": True,
                "reason": f"APR increased by {increase:.4%}",
                "initial_apr": initial_cd_apr,
                "current_apr": current_apr
            }
        
        return {"requires_3_day_wait": False}
```

6. **COC CD Detection** (Change of Circumstances)

```python
class COCDetector:
    """
    Detect when Change of Circumstances CD is needed
    """
    
    COC_TRIGGERS = [
        "rate_change",
        "loan_amount_change",
        "fee_increase_above_tolerance",
        "settlement_date_change",
        "product_change"
    ]
    
    def detect_changes(self, initial_cd, current_values):
        """
        Compare initial CD to current loan state
        Returns list of changes that require COC CD
        """
        changes = []
        
        for field, initial_value in initial_cd.items():
            current_value = current_values.get(field)
            if self.is_material_change(field, initial_value, current_value):
                changes.append({
                    "field": field,
                    "initial": initial_value,
                    "current": current_value,
                    "requires_coc": True
                })
        
        return changes
```

#### Tools Used
```python
# Field IO
read_fields(loan_id, field_ids[])
write_fields(loan_id, updates[])
normalize_field_value(field_id, value)

# MI Calculation
calculate_conventional_mi(loan_context)
calculate_fha_mip(loan_context)
calculate_va_funding_fee(loan_context)
calculate_usda_guarantee(loan_context)

# Fee/APR
calculate_fee_tolerance(loan_id, le_fees, cd_fees)
apply_tolerance_cure(loan_id, cure_amount)
calculate_apr(loan_context)
check_apr_impact(initial_apr, current_apr)

# COC
detect_coc_triggers(loan_id, initial_cd, current_values)
generate_coc_cd(loan_id, changes)

# CD Generation
populate_cd_page_1(loan_id, data)
populate_cd_page_2(loan_id, data)
populate_cd_page_3(loan_id, data)
populate_cd_page_4(loan_id, data)
populate_cd_page_5(loan_id, data)
generate_initial_cd(loan_id)

# Logging
log_issue(loan_id, severity, message)
```

---

### 4.3 Request Reviews Agent

**Purpose**: Route CD for review, send to stakeholders, track acknowledgment.

#### Responsibilities

1. **Route to LO for Review**
   ```python
   def route_to_lo(loan_id, cd_document):
       """
       Route disclosure to LO for review before sending to borrower
       """
       lo_email = get_lo_email(loan_id)
       
       return {
           "action": "review_request",
           "to": lo_email,
           "document": cd_document,
           "task_type": "disclosure_review"
       }
   ```

2. **Send Email with Attachment**
   ```python
   def send_disclosure_email(loan_id, recipients, cd_document):
       """
       Send CD to LO and other stakeholders
       
       Recipients may include:
       - LO
       - Processor
       - Other stakeholders per branch rules
       """
       subject = f"Disclosure Review: {loan_id} - {borrower_name}"
       
       # Attach CD PDF
       attachments = [cd_document]
       
       send_email(to=recipients, subject=subject, attachments=attachments)
   ```

3. **Send to Borrower for ACK**
   ```python
   def send_for_borrower_ack(loan_id, cd_document):
       """
       Send CD to borrower for acknowledgment via disclosure system
       (Blend, Encompass Consumer Connect, etc.)
       """
       borrower_email = get_borrower_email(loan_id)
       coborrower_email = get_coborrower_email(loan_id)  # If applicable
       
       disclosure_system.send_for_signature(
           loan_id=loan_id,
           document=cd_document,
           recipients=[borrower_email, coborrower_email],
           type="closing_disclosure"
       )
   ```

4. **Track ACK Status**
   ```python
   def track_ack_status(loan_id):
       """
       Track CD acknowledgment and 3-day waiting period
       """
       ack_status = get_ack_status(loan_id)
       
       if ack_status.acknowledged:
           waiting_period_end = calculate_3_day_wait(ack_status.ack_date)
           
           return {
               "acknowledged": True,
               "ack_date": ack_status.ack_date,
               "ack_by": ack_status.signed_by,
               "waiting_period_ends": waiting_period_end,
               "ready_for_draw_docs": datetime.now() >= waiting_period_end
           }
       
       return {"acknowledged": False}
   ```

5. **3-Day Wait Calculation**
   ```python
   def calculate_3_day_wait(ack_date):
       """
       Calculate when 3-day TRID waiting period ends
       
       Rules:
       - Count 3 business days from ACK
       - Exclude Sundays
       - Exclude Federal holidays
       - Day 1 is day AFTER acknowledgment
       """
       federal_holidays = get_federal_holidays(ack_date.year)
       
       days_counted = 0
       current_date = ack_date + timedelta(days=1)
       
       while days_counted < 3:
           if current_date.weekday() != 6:  # Not Sunday
               if current_date not in federal_holidays:
                   days_counted += 1
           current_date += timedelta(days=1)
       
       return current_date
   ```

#### Tools Used
```python
# Routing
get_lo_email(loan_id)
get_processor_email(loan_id)
create_review_task(loan_id, task_type, assign_to)

# Email
send_email(to, subject, body, attachments)
get_borrower_email(loan_id)
get_coborrower_email(loan_id)

# Disclosure System
send_for_signature(loan_id, document, recipients, type)
get_ack_status(loan_id)
calculate_3_day_wait(ack_date)

# Status Updates
update_cd_status(loan_id, status)
update_milestone(loan_id, milestone, comment)
```

---

## 5. Disclosure vs Draw Docs: What You DON'T Need

| Component | In Draw Docs | In Disclosure | Why |
|-----------|--------------|---------------|-----|
| Document Download | ✅ 35+ docs | ❌ None | Disclosure trusts processor input |
| Document Verification | ✅ Complex | ❌ None | Just field existence checks |
| PTF Conditions | ✅ Add/manage | ❌ None | Not applicable at disclosure stage |
| State Rules Engine | ✅ Complex | ⚠️ Minimal | Only basic rules (no endorsements, trustees) |
| Trust Handling | ✅ Full module | ❌ None | Handled in Draw Docs |
| MIN/MERS Verification | ✅ Yes | ❌ None | Done in Draw Docs |
| Branch/Investor Rules | ✅ Extensive | ⚠️ Minimal | Only fee caps apply |
| Mavent Compliance | ✅ Yes | ❌ None | Run after docs drawn |
| Order & Package | ✅ Complex | ❌ None | No package to order |

---

## 6. Shared Components (Reuse from Draw Docs)

| Component | Usage in Disclosure | Notes |
|-----------|---------------------|-------|
| MI Calculation | ✅ Core feature | Same logic, may click "GET MI" in Draw Docs |
| Fee Tolerance | ✅ Calculate & cure | Same calculation logic |
| APR Calculation | ✅ Calculate & check | Same APR rules |
| CD Page Population | ✅ All 5 pages | Same fields |
| 3-Day Wait Tracking | ✅ Own + inform Draw Docs | Shared utility |

**Recommendation**: Build these as shared utilities that both agents can use.

---

## 7. Complete Tool Inventory

### Verification Tools
```python
check_field_existence(loan_id: str, field_ids: List[str]) -> Dict[str, bool]
get_required_fields(loan_type: str, purpose: str) -> List[str]
log_missing_fields(loan_id: str, fields: List[str]) -> None
request_field_update(loan_id: str, fields: List[str], assign_to: str) -> None
```

### Preparation Tools
```python
# Field IO
read_fields(loan_id: str, field_ids: List[str]) -> Dict[str, Any]
write_fields(loan_id: str, updates: Dict[str, Any]) -> None
normalize_field_value(field_id: str, value: Any) -> Any

# MI Calculation
calculate_mi(loan_context: LoanContext) -> MIResult
get_fha_mip_rate(term: int, ltv: float, loan_amount: float) -> float
get_va_funding_rate(purpose: str, down_pct: float, subsequent: bool) -> float

# Fee Tolerance
calculate_fee_tolerance(loan_id: str, le_fees: Dict, cd_fees: Dict) -> ToleranceResult
apply_tolerance_cure(loan_id: str, cure_amount: float) -> None

# APR
calculate_apr(loan_context: LoanContext) -> float
check_apr_impact(initial_apr: float, current_apr: float) -> APRImpactResult

# COC
detect_coc_triggers(loan_id: str, initial_cd: Dict, current: Dict) -> List[Change]
generate_coc_cd(loan_id: str, changes: List[Change]) -> Document

# CD Generation
populate_cd_fields(loan_id: str, page: int, data: Dict) -> None
generate_cd(loan_id: str, type: str) -> Document  # type = "initial" or "coc"
```

### Request Reviews Tools
```python
# Routing
get_lo_info(loan_id: str) -> LOInfo
create_review_task(loan_id: str, task_type: str, assign_to: str) -> Task

# Communication
send_email(to: List[str], subject: str, body: str, attachments: List[Doc]) -> None
send_for_signature(loan_id: str, doc: Document, recipients: List[str]) -> None

# Tracking
get_ack_status(loan_id: str) -> ACKStatus
calculate_3_day_wait(ack_date: date) -> date
update_cd_status(loan_id: str, status: str) -> None
update_milestone(loan_id: str, milestone: str, comment: str) -> None
```

---

## 8. Error Handling

| Issue | Severity | Action | Auto-Continue |
|-------|----------|--------|---------------|
| Missing required field | Medium | Request processor update | ❌ No |
| Missing optional field | Low | Log warning, continue | ✅ Yes |
| Fee tolerance exceeded | Medium | Calculate cure, apply | ✅ Yes |
| APR triggers 3-day wait | Info | Flag, not an error | ✅ Yes |
| Product change detected | High | Require LO confirmation | ❌ No |
| Borrower email invalid | Medium | Request update | ❌ No |
| Signature system error | High | Retry, then escalate | ❌ No |

---

## 9. Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  INPUTS (from Processor)                                                        │
│  ────────────────────────                                                        │
│  • Encompass fields (borrower, property, loan, fees, contacts)                  │
│  • Last LE (for tolerance comparison)                                           │
│  • Rate lock info                                                               │
│                                                                                  │
│                           ↓                                                      │
│                                                                                  │
│  VERIFICATION AGENT                                                              │
│  ──────────────────                                                              │
│  • Check field existence                                                        │
│  • Output: Verification result (pass/fail + missing fields)                     │
│                                                                                  │
│                           ↓                                                      │
│                                                                                  │
│  PREPARATION AGENT                                                               │
│  ─────────────────                                                               │
│  • Calculate MI                                                                 │
│  • Check fee tolerance                                                          │
│  • Calculate APR                                                                │
│  • Populate CD pages                                                            │
│  • Output: CD ready for review                                                  │
│                                                                                  │
│                           ↓                                                      │
│                                                                                  │
│  REQUEST REVIEWS AGENT                                                           │
│  ─────────────────────                                                           │
│  • Route to LO                                                                  │
│  • Send for borrower signature                                                  │
│  • Track acknowledgment                                                         │
│  • Output: ACK'd CD + 3-day wait info                                           │
│                                                                                  │
│                           ↓                                                      │
│                                                                                  │
│  OUTPUTS (to Draw Docs)                                                         │
│  ──────────────────────                                                          │
│  • CD Approved status                                                           │
│  • CD Acknowledged date                                                         │
│  • 3-day waiting period end date                                                │
│  • Any tolerance cures applied                                                  │
│  • APR impact flags                                                             │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Testing Scenarios

| Scenario | Loan Type | Key Validations |
|----------|-----------|-----------------|
| Standard Purchase | Conventional | Basic field checks, no MI |
| High LTV Purchase | Conventional 90% | MI calculation, cancel@78% |
| FHA Purchase | FHA | UFMIP 1.75%, annual MIP |
| VA Purchase First Use | VA | Funding fee 2.15% |
| VA IRRRL | VA Refi | Funding fee 0.50% |
| USDA Purchase | USDA | Tech fee $25, guarantee |
| Fee Tolerance Exceeded | Any | Cure calculation, apply to credit |
| APR Increase >0.125% | Any | 3-day wait flag |
| COC CD Required | Any | Change detection, new CD |
| Product Change | Conv → FHA | 3-day wait, major flag |

---

## 11. Implementation Priority

### Phase 1 (MVP)
1. Verification Agent (field existence only)
2. Preparation Agent:
   - Basic field population
   - Conventional MI calculation
   - Basic fee tolerance check
3. Request Reviews (email only, no signature tracking)

### Phase 2
1. Add FHA/VA/USDA MI calculations
2. Add APR calculation and impact check
3. Add COC CD detection
4. Add signature tracking

### Phase 3
1. Add full tolerance cure automation
2. Add 3-day wait calculation
3. Add LO review workflow
4. Integration with Draw Docs handoff

---

## 12. Integration Points with Draw Docs

When Disclosure is complete, the following info flows to Draw Docs:

```python
class DisclosureHandoff:
    """
    Data passed from Disclosure to Draw Docs
    """
    loan_id: str
    cd_status: str  # "CD Approved"
    cd_ack_date: date
    cd_ack_by: List[str]  # Names of signers
    waiting_period_ends: date
    tolerance_cures_applied: List[Cure]
    apr_at_disclosure: float
    initial_cd_document: Document
    coc_cd_documents: List[Document]  # If any
    
    def is_ready_for_draw_docs(self) -> bool:
        return (
            self.cd_status == "CD Approved" and
            self.cd_ack_date is not None and
            datetime.now().date() >= self.waiting_period_ends
        )
```

---

*Document generated November 28, 2025*

