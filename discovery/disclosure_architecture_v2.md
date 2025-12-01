# Disclosure Agent Architecture v2 (SOP-Aligned)

## Document Info
- **Created**: December 1, 2025
- **Supersedes**: `disclosure_architecture.md` (Nov 28, 2025)
- **Based On**: Disclosure Desk SOP (Official), Gap Analysis
- **Owner**: Naomi

---

## 🚨 Key Corrections from v1

| Issue | v1 Assumption | v2 Reality (from SOP) |
|-------|---------------|----------------------|
| **Primary Document** | Closing Disclosure (CD) | **Loan Estimate (LE)** is primary |
| **Timing** | After CTC | **Within 3 business days** of application |
| **Mavent Check** | "Not needed" | **Mandatory** - must clear before send |
| **ATR/QM Check** | Missing | **Mandatory** - flags must be GREEN |
| **Form Validation** | Generic 20 fields | **15+ specific forms** per SOP |

---

## 1. Overview

The Disclosure Desk handles **ALL disclosures** in the loan lifecycle:

1. **Initial Disclosures (ID)** - Loan Estimate sent within 3 business days of application
2. **Revised Disclosures (COC/LE)** - Change of Circumstances Loan Estimates
3. **Closing Disclosure (CD)** - Sent before closing (handled similarly)

### Loan Timeline Position

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              LOAN TIMELINE                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ← 3 BUSINESS DAYS →                                                            │
│                                                                                  │
│  [Application]                                                                   │
│       ↓                                                                          │
│  [DISCLOSURE DESK: Initial LE] ←── THIS AGENT                                   │
│       ↓                                                                          │
│  [Rate Lock / Changes]                                                           │
│       ↓                                                                          │
│  [DISCLOSURE DESK: COC/LE] ←── THIS AGENT                                       │
│       ↓                                                                          │
│  [Underwriting / CTC]                                                            │
│       ↓                                                                          │
│  [DISCLOSURE DESK: CD] ←── THIS AGENT                                           │
│       ↓                                                                          │
│  [CD ACK + 3-day Wait]                                                           │
│       ↓                                                                          │
│  [DRAW DOCS AGENT] ←── Separate Agent                                           │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Disclosure Desk Queues (from SOP)

The Encompass system has these queues for disclosure work:

| Queue | Purpose | Agent Action |
|-------|---------|--------------|
| **DD Request** | New disclosure requests | Pick up and process |
| **DD Corrections** | Files needing fixes | Review, correct, reprocess |
| **DD Approved to Send** | Ready to send | Order eDisclosures |
| **DD LO To Review** | Awaiting LO review | Monitor, follow up |
| **DD Locked Loans** | Locked loan disclosures | Process with rate lock info |

---

## 3. Entry Conditions (Prerequisites)

### For Initial Disclosures (ID)

| Condition | Check Method | Blocking |
|-----------|--------------|----------|
| File in DD Request queue | Pipeline status | ✅ Yes |
| Application Date set | Disclosure Tracking | ✅ Yes |
| LE Due Date within 3 days | Calculated from App Date | ✅ Yes |
| "Send Initial Disclosures" alert exists | Alerts & Messages | ✅ Yes |
| Company License #204 set | File Contact → Lender | ✅ Yes |

### For Locked Loans
| Condition | Check Method | Blocking |
|-----------|--------------|----------|
| All TRID info updated | Field existence | ✅ Yes |
| Subject Property Address | Field check | ✅ Yes |
| DTI (Debt-to-Income) | Calculated | ✅ Yes |
| Appraised/Estimated Value | Field check | ✅ Yes |

### For Non-Locked Loans
| Condition | Check Method | Blocking |
|-----------|--------------|----------|
| If App Date + LE Due passed | Date check | 🚨 Escalate to Supervisor |
| New loan application needed | Manual action | ⛔ Cannot auto-process |

---

## 4. Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         DISCLOSURE ORCHESTRATOR                                  │
│                                                                                  │
│  Routes: Initial LE vs COC/LE vs CD Request                                     │
│  Manages: Queue assignment, error handling, escalation                          │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────────┐   ┌───────────────────────┐   ┌────────────────────────┐
│ VERIFICATION      │   │ PREPARATION AGENT     │   │ SEND AGENT             │
│ AGENT             │──▶│                       │──▶│                        │
│                   │   │ • Form field updates  │   │ • Mavent check         │
│ • TRID dates      │   │ • MI calculation      │   │ • ATR/QM check         │
│ • Form validation │   │ • 2015 Itemization    │   │ • Order eDisclosures   │
│ • Lock status     │   │ • Cash to Close       │   │ • Update queue/status  │
│ • Queue check     │   │ • RegZ-LE fields      │   │                        │
└───────────────────┘   └───────────────────────┘   └────────────────────────┘
```

---

## 5. Agent Specifications

### 5.1 Verification Agent

**Purpose**: Validate prerequisites and form field existence before processing.

#### 5.1.1 TRID Compliance Checks

```python
class TRIDChecker:
    """
    TRID = TILA-RESPA Integrated Disclosure rules
    """
    
    def check_initial_disclosure_timing(self, loan_id: str) -> TRIDResult:
        """
        LE must be sent within 3 BUSINESS DAYS of application
        """
        app_date = get_field("application_date")
        le_due_date = calculate_le_due_date(app_date)  # 3 business days
        today = date.today()
        
        if today > le_due_date:
            return TRIDResult(
                compliant=False,
                action="ESCALATE",
                message="LE due date passed - escalate to Supervisor"
            )
        
        days_remaining = (le_due_date - today).days
        return TRIDResult(
            compliant=True,
            le_due_date=le_due_date,
            days_remaining=days_remaining
        )
    
    def check_disclosure_alert(self, loan_id: str) -> bool:
        """
        For Initial Disclosures, "Send Initial Disclosures" alert 
        must exist under Alerts & Messages
        """
        alerts = get_alerts_and_messages(loan_id)
        return "Send Initial Disclosures" in alerts
```

#### 5.1.2 Form Field Validation (from SOP)

The SOP requires checking specific forms. Here are the **mandatory forms**:

```python
REQUIRED_FORMS = {
    "1003_URLA_Lender": {
        "fields": [
            "borrower_name", "borrower_ssn", "property_address",
            "loan_amount", "loan_purpose", "occupancy_type"
        ],
        "conditional": {
            "mip_required": "ltv > 80 AND loan_type == Conventional"
        }
    },
    "1003_URLA_Part1": {
        "fields": ["mailing_address_same_as_current"],
        "check": "ensure_not_blank"
    },
    "1003_URLA_Part2": {
        "fields": [
            "current_employment", "gross_monthly_income", "total_income"
        ]
    },
    "1003_URLA_Part3": {
        "fields": ["assets", "liabilities", "real_estate"]
    },
    "1003_URLA_Part4": {
        "fields": [
            "declarations", "demographics",
            "loan_originator_info", "lo_nmls_match"
        ],
        "verify_against": "NMLS Portal"
    },
    "Affiliated_Business_Arrangements": {
        "fields": ["settlement_box_marked", "transaction_type_marked"]
    },
    "Borrower_Summary_Origination": {
        "fields": [
            "channel", "current_status", "application_date", "lock_dates"
        ]
    },
    "FACT_Act_Disclosure": {
        "fields": [
            "credit_score_experian", "credit_score_transunion", 
            "credit_score_equifax", "key_factors", "date_ordered"
        ],
        "note": "If blank, notify LO & Processor to pull credit report"
    },
    "RegZ_LE": {
        "fields": [
            "le_date_issued", "interest_accrual_360_360",
            "late_charge_days", "late_charge_percent", "assumption"
        ],
        "conditional": {
            "buydown_fields": "if buydown_marked"
        }
    }
}
```

#### 5.1.3 Loan Originator License Check

```python
def verify_lo_license(loan_id: str) -> LOVerificationResult:
    """
    From SOP:
    - LO must be authorized in subject property state
    - LO license must be approved and renewed for current year
    - LO info must match NMLS Portal
    """
    lo_info = get_loan_originator_info(loan_id)
    property_state = get_field(loan_id, "property_state")
    
    # Check license status
    nmls_status = verify_nmls_license(
        lo_info.nmls_id, 
        property_state,
        current_year=date.today().year
    )
    
    return LOVerificationResult(
        authorized=nmls_status.active,
        state=property_state,
        license_expiry=nmls_status.expiry,
        issues=nmls_status.issues
    )
```

#### 5.1.4 Lock Status Check

```python
def check_lock_status(loan_id: str) -> LockStatus:
    """
    Locked vs Non-Locked loans have different processing paths
    """
    is_locked = get_field(loan_id, "rate_lock_status")
    
    if is_locked:
        # Verify all TRID info is updated
        trid_fields = ["property_address", "dti", "appraised_value"]
        missing = check_field_existence(loan_id, trid_fields)
        
        if missing:
            return LockStatus(
                locked=True,
                trid_complete=False,
                missing_fields=missing,
                action="Request update before processing"
            )
        
        return LockStatus(locked=True, trid_complete=True)
    
    return LockStatus(locked=False, action="Monitor LE due date")
```

---

### 5.2 Preparation Agent

**Purpose**: Update forms, calculate MI, prepare disclosure data.

#### 5.2.1 RegZ-LE Form Updates

```python
class RegZLEUpdater:
    """
    Update RegZ-LE form per SOP requirements
    """
    
    def update(self, loan_id: str) -> Dict:
        updates = {}
        loan_type = get_loan_type(loan_id)
        
        # 1. LE Date Issued = Current Date
        updates["le_date_issued"] = date.today()
        
        # 2. Interest Accrual Options
        updates["interest_days_per_year"] = "360/360"
        updates["zero_percent_payment_option"] = None  # Must be blank
        updates["use_simple_interest_accrual"] = None  # Must be blank
        updates["biweekly_interim_days"] = 365
        
        # 3. Buydown handling
        if get_field(loan_id, "buydown_marked"):
            updates["buydown_contributor"] = get_field(loan_id, "buydown_contributor")
            updates["buydown_type"] = get_field(loan_id, "buydown_type")
            updates["buydown_rate_percent"] = get_field(loan_id, "buydown_rate")
            updates["buydown_term"] = get_field(loan_id, "buydown_term")
        
        # 4. Late Charge - varies by loan type
        if loan_type == "Conventional":
            updates["late_charge_days"] = 15
            updates["late_charge_percent"] = 5.0
        elif loan_type in ["FHA", "VA"]:
            updates["late_charge_days"] = 15
            updates["late_charge_percent"] = 4.0
        
        # Special: North Carolina = 4% for ALL loan types
        if get_field(loan_id, "property_state") == "NC":
            updates["late_charge_percent"] = 4.0
        
        # 5. Assumption
        if loan_type == "Conventional":
            updates["assumption"] = "may not"
        elif loan_type in ["FHA", "VA"]:
            updates["assumption"] = "may, subject to conditions"
        
        # 6. Prepayment handling
        prepayment = get_field(loan_id, "prepayment_status")
        if prepayment in ["Will", "May", "May be"]:
            updates["prepayment_type"] = get_field(loan_id, "prepay_type")
            updates["prepayment_period"] = get_field(loan_id, "prepay_period")
            updates["prepayment_percent"] = get_field(loan_id, "prepay_percent")
        
        return write_fields(loan_id, updates)
```

#### 5.2.2 MI/Funding Fee Calculation

```python
class MICalculator:
    """
    Calculate MIP/Funding Fee based on loan type
    Per SOP: Update MIP/FF Based on Loan Type
    """
    
    def calculate(self, loan_id: str) -> MIResult:
        loan_type = get_loan_type(loan_id)
        ltv = get_ltv(loan_id)
        
        if loan_type == "Conventional":
            return self.conventional_mi(loan_id, ltv)
        elif loan_type == "FHA":
            return self.fha_mip(loan_id)
        elif loan_type == "VA":
            return self.va_funding_fee(loan_id)
        elif loan_type == "USDA":
            return self.usda_guarantee(loan_id)
        
        return MIResult(required=False)
    
    def conventional_mi(self, loan_id: str, ltv: float) -> MIResult:
        """
        SOP: If LTV > 80%, MIP must be updated
        If not updated, request branch to update
        """
        if ltv <= 80:
            return MIResult(required=False)
        
        # Get from MI Certificate if available
        mi_cert = get_mi_certificate(loan_id)
        if mi_cert:
            return MIResult(
                required=True,
                source="mi_cert",
                monthly_amount=mi_cert.monthly,
                upfront_amount=mi_cert.upfront,
                cancel_at_ltv=78.0
            )
        
        # Flag for branch to update
        return MIResult(
            required=True,
            source="needs_update",
            action="Request branch to update MIP"
        )
    
    def fha_mip(self, loan_id: str) -> MIResult:
        """
        SOP: Follow FHA Matrix for MIP
        """
        loan_amount = get_field(loan_id, "loan_amount")
        ufmip = loan_amount * 0.0175  # Always 1.75%
        
        # Annual MIP from FHA Matrix (varies by term/LTV/amount)
        annual_rate = self.get_fha_matrix_rate(loan_id)
        
        return MIResult(
            required=True,
            source="fha_matrix",
            upfront_amount=ufmip,
            annual_rate=annual_rate,
            monthly_amount=(loan_amount * annual_rate) / 12
        )
    
    def va_funding_fee(self, loan_id: str) -> MIResult:
        """
        SOP: VA FF status based on COE (Certificate of Eligibility)
        """
        coe = get_va_coe(loan_id)
        
        if coe.funding_fee_exempt:
            return MIResult(required=False, exempt=True)
        
        # Get rate based on usage, down payment, purpose
        rate = self.get_va_fee_rate(
            first_use=coe.first_use,
            down_payment_pct=get_field(loan_id, "down_payment_percent"),
            purpose=get_field(loan_id, "loan_purpose")
        )
        
        loan_amount = get_field(loan_id, "loan_amount")
        return MIResult(
            required=True,
            source="va_coe",
            funding_fee=loan_amount * rate,
            rate=rate
        )
    
    def usda_guarantee(self, loan_id: str) -> MIResult:
        """
        SOP: UFMIP generally 1% and can be financed
        Annual MIP based on term and amount
        """
        loan_amount = get_field(loan_id, "loan_amount")
        
        return MIResult(
            required=True,
            source="usda",
            upfront_amount=loan_amount * 0.01,  # 1%
            upfront_financed=True,
            annual_rate=0.0035  # Typical rate
        )
```

#### 5.2.3 2015 Itemization Updates

```python
class ItemizationUpdater:
    """
    Update 2015 Itemization form sections per SOP
    """
    
    def update_section_800(self, loan_id: str) -> Dict:
        """
        Section 800 = Origination Charges
        Maps to Section A on LE Page 2
        """
        updates = {}
        
        # 801: Origination fees, paid to "L", APR marked
        updates["801_origination_fee"] = get_field(loan_id, "origination_fee")
        updates["801_paid_to"] = "L"
        updates["801_apr_marked"] = True
        
        # 802: Credits & Points
        updates["802b_credit_for_rate"] = get_field(loan_id, "credit_for_rate")
        updates["802e_loan_discount_points"] = get_field(loan_id, "discount_points")
        updates["802e_bona_fide"] = True  # Must be checked
        
        return updates
    
    def update_section_804_835(self, loan_id: str) -> Dict:
        """
        Section 804-835 = Section B on LE Page 2
        CRITICAL: Hybrid eDoc Fee = $58 for ALL loans
        """
        updates = {}
        
        # Hybrid eDoc/eSigning Fee is MANDATORY
        updates["hybrid_edoc_fee"] = 58.00
        updates["hybrid_edoc_fee_description"] = "Hybrid eSigning Fee"
        
        return updates
    
    def update_section_1000(self, loan_id: str) -> Dict:
        """
        Section 1000 = Impounds/Escrow
        """
        updates = {}
        impounds_waived = get_field(loan_id, "impounds_waived")
        
        if not impounds_waived:
            updates["hoi_escrowed"] = True
            updates["property_taxes_escrowed"] = True
            updates["1002_hoi_months"] = get_field(loan_id, "hoi_escrow_months")
            updates["1002_hoi_monthly"] = get_field(loan_id, "hoi_monthly")
            updates["1004_tax_months"] = get_field(loan_id, "tax_escrow_months")
            updates["1004_tax_monthly"] = get_field(loan_id, "tax_monthly")
        
        # Flood zone check
        if get_field(loan_id, "flood_zone"):
            updates["1006_flood_months"] = get_field(loan_id, "flood_escrow_months")
            updates["1006_flood_monthly"] = get_field(loan_id, "flood_monthly")
        
        # USDA specific
        if get_loan_type(loan_id) == "USDA":
            updates["1010_usda_annual_fee"] = get_field(loan_id, "usda_annual_fee")
        
        updates["1011_aggregate_adjustment"] = get_field(loan_id, "aggregate_adj")
        
        return updates
    
    def update_section_1100(self, loan_id: str) -> Dict:
        """
        Section 1100 = Title Charges (Section C on LE Page 2)
        Different for Purchase vs Refinance
        """
        updates = {}
        purpose = get_field(loan_id, "loan_purpose")
        
        updates["settlement_fee"] = get_field(loan_id, "settlement_fee")
        updates["escrow_closing_fee"] = get_field(loan_id, "escrow_fee")
        updates["lenders_title_insurance"] = get_field(loan_id, "lti")
        
        if purpose == "Purchase":
            updates["owners_title_insurance"] = get_field(loan_id, "oti")
        
        # Mark seller-paid fees
        for fee in ["settlement_fee", "escrow_fee", "oti"]:
            if get_field(loan_id, f"{fee}_seller_paid"):
                updates[f"{fee}_seller_obligated"] = True
        
        return updates
    
    def update_section_1200(self, loan_id: str) -> Dict:
        """
        Section 1200 = Recording & Transfer Taxes (Section E on LE Page 2)
        Recording Fee REQUIRED for all loans
        """
        return {
            "recording_fee": get_field(loan_id, "recording_fee") or 0,
            "transfer_taxes": get_field(loan_id, "transfer_taxes") or 0
        }
    
    def update_section_1300(self, loan_id: str) -> Dict:
        """
        Section 1300 = Additional Settlement (Section H on LE Page 2)
        Pest/Survey must be under Single * line
        """
        updates = {}
        
        pest = get_field(loan_id, "pest_inspection_fee")
        survey = get_field(loan_id, "survey_fee")
        
        # Must be under single asterisk line
        if pest:
            updates["1301_pest_inspection"] = pest
            updates["1301_line_type"] = "single"
        if survey:
            updates["1302_survey_fee"] = survey
            updates["1302_line_type"] = "single"
        
        return updates
    
    def update_section_m(self, loan_id: str) -> Dict:
        """
        Section M = Credits
        CRITICAL: General Lender Credit cannot be reduced once applied!
        """
        updates = {}
        
        updates["m2_m3_emd"] = get_field(loan_id, "earnest_money")
        updates["m4_lender_credit"] = get_field(loan_id, "lender_credit")
        updates["m5_m6_seller_credit"] = get_field(loan_id, "seller_credit")
        
        # Flag if lender credit is being added
        if updates["m4_lender_credit"]:
            updates["lender_credit_requires_approval"] = True
        
        return updates
```

#### 5.2.4 Cash to Close Matching

```python
def match_cash_to_close(loan_id: str) -> CashToCloseResult:
    """
    SOP: CTC must match Estimated Cash to Close on LE page 2
    """
    purpose = get_field(loan_id, "loan_purpose")
    
    if purpose == "Purchase":
        # Check these boxes for Purchase
        updates = {
            "use_actual_down_payment": True,
            "closing_costs_financed": True,
            "include_payoffs_in_adjustments": True
        }
    else:  # Refinance
        # Check Alternative form for Refinance
        updates = {
            "alternative_form_checkbox": True
        }
    
    write_fields(loan_id, updates)
    
    # Verify match
    calculated_ctc = calculate_cash_to_close(loan_id)
    displayed_ctc = get_field(loan_id, "le_page2_ctc")
    
    if abs(calculated_ctc - displayed_ctc) > 0.01:
        return CashToCloseResult(
            matched=False,
            calculated=calculated_ctc,
            displayed=displayed_ctc,
            difference=abs(calculated_ctc - displayed_ctc)
        )
    
    return CashToCloseResult(matched=True)
```

---

### 5.3 Send Agent

**Purpose**: Run compliance checks and order disclosures.

#### 5.3.1 Mavent Compliance Check (MANDATORY)

```python
def check_mavent_compliance(loan_id: str) -> MaventResult:
    """
    SOP: Mavent Fail/Alert/Warning must be cleared before sending
    Tools → Compliance Review → Preview
    """
    compliance = run_mavent_preview(loan_id)
    
    if compliance.has_fails:
        return MaventResult(
            passed=False,
            blocking=True,
            issues=compliance.fails,
            action="Clear Mavent fails before sending"
        )
    
    if compliance.has_alerts or compliance.has_warnings:
        return MaventResult(
            passed=False,
            blocking=True,
            issues=compliance.alerts + compliance.warnings,
            action="Clear Mavent alerts/warnings before sending"
        )
    
    return MaventResult(passed=True)
```

#### 5.3.2 ATR/QM Check (MANDATORY)

```python
def check_atr_qm(loan_id: str) -> ATRQMResult:
    """
    SOP: ATR/QM flags must be GREEN to proceed
    Forms → ATR/QM Management → Qualification → Points and Fees
    """
    atr_qm = get_atr_qm_status(loan_id)
    
    # All these flags must be GREEN
    required_green = [
        "loan_features_flag",
        "points_and_fees_flag",
        "price_limit_flag"
    ]
    
    red_flags = []
    for flag in required_green:
        if atr_qm.get(flag) == "RED":
            red_flags.append(flag)
    
    if red_flags:
        return ATRQMResult(
            passed=False,
            blocking=True,
            red_flags=red_flags,
            action="ATR/QM flags must be GREEN"
        )
    
    return ATRQMResult(passed=True)
```

#### 5.3.3 Order eDisclosures

```python
def order_disclosures(loan_id: str, disclosure_type: str) -> OrderResult:
    """
    SOP: Order the Disclosure Package
    eFolder → eDisclosures → Select Product → Order eDisclosures
    """
    # 1. Check for mandatory audits
    audits = get_mandatory_audits(loan_id)
    if audits:
        return OrderResult(
            success=False,
            blocking=True,
            message=f"Clear mandatory audits first: {audits}"
        )
    
    # 2. Determine product based on loan type
    loan_type = get_loan_type(loan_id)
    product = get_disclosure_product(loan_type)  # Generic Product
    
    # 3. Order via eDisclosures
    result = encompass_order_edisclosures(
        loan_id=loan_id,
        product=product,
        type=disclosure_type  # "initial" or "revised"
    )
    
    return OrderResult(success=True, tracking_id=result.id)
```

---

## 6. State-Specific Rules

### Texas (From SOP)

```python
TEXAS_RULES = {
    "2015_itemization": {
        "line_810": {
            "fee": "Attorney Review Fee",
            "amount": 325.00,
            "payee": "Cain & Kiel, P.C."
        }
    },
    "forms_required": {
        "all_tx": [
            "Texas State Specific Information Form",
            "Texas Banker Mortgage Disclosure"
        ],
        "tx_refinance": [
            "TX Notice Concerning Extensions of Credit",  # 12-day letter
            "Texas A6 form"
        ]
    },
    "updates": {
        "purchase": {
            "date_delivery_initiated": "current_date"
        },
        "refinance": {
            "title_information": "based_on_occupancy_and_refi_type"
        }
    }
}
```

---

## 7. Change of Circumstances (COC/LE)

From SOP - COC triggers and checklist:

```python
class COCProcessor:
    """
    Handle Change of Circumstances (Revised Loan Estimates)
    """
    
    COC_TRIGGERS = [
        "borrower_added_removed_changed",
        "loan_program_change",
        "rate_change",
        "loan_amount_change",
        "fee_increase_above_tolerance",
        "settlement_date_change"
    ]
    
    def check_coc_needed(self, loan_id: str) -> COCCheckResult:
        """
        SOP COC Checklist
        """
        checks = {}
        
        # 1. Disclosure Tracking
        checks["last_le_signed"] = self.check_last_le_signed(loan_id)
        checks["borrower_changed"] = self.check_borrower_changes(loan_id)
        checks["loan_program_changed"] = self.check_program_change(loan_id)
        checks["intent_to_proceed_updated"] = self.check_intent_date(loan_id)
        
        # 2. Blend Integration
        checks["econsent_accepted"] = self.check_econsent(loan_id)
        
        # 3. Disclosure Summary
        checks["cd_status"] = self.check_cd_status(loan_id)
        
        # 4. Compare to last sent LE
        checks["le_changes"] = self.compare_to_last_le(loan_id)
        
        # Determine if COC needed
        needs_coc = any([
            checks["borrower_changed"],
            checks["loan_program_changed"],
            len(checks["le_changes"]) > 0
        ])
        
        return COCCheckResult(
            needs_coc=needs_coc,
            checks=checks,
            changes=checks["le_changes"]
        )
    
    def handle_intent_to_proceed_change(self, loan_id: str):
        """
        SOP: If Intent to Proceed date updated, 
        remove Closing Cost Estimate Expiration Date from LE page
        """
        if self.check_intent_date(loan_id):
            clear_field(loan_id, "closing_cost_estimate_expiration")
```

---

## 8. Special Instructions (from SOP)

```python
SPECIAL_INSTRUCTIONS = {
    "program_change_conv_to_fha": {
        "action": "Send FHA disclosures with revised LE",
        "additional_docs": ["FHA Disclosures Package"]
    },
    "amortization_change_fixed_to_arm": {
        "action": "Send CHARM booklet and ARM disclosure with revised LE",
        "additional_docs": ["CHARM Booklet", "ARM Disclosure"]
    }
}
```

---

## 9. VA Loan Specifics (from SOP)

```python
class VALoanHandler:
    """
    VA Management Form requirements per SOP
    """
    
    def update_va_management(self, loan_id: str, purpose: str):
        updates = {}
        
        # Basic Information tab - always required
        updates["first_use_of_va"] = get_field(loan_id, "va_first_use")
        updates["funding_fee_exempt"] = get_field(loan_id, "va_ff_exempt")
        
        if purpose == "Refinance":
            # Recoupment info required for refinance
            updates["recoupment_info"] = self.calculate_recoupment(loan_id)
        
        write_va_management_form(loan_id, updates)
```

---

## 10. Settlement Service Provider List (SSPL)

```python
def update_sspl(loan_id: str):
    """
    SOP: SSPL must match Section C fees on LE Page 2
    """
    # Get Section C fees
    section_c_fees = get_section_c_fees(loan_id)
    
    # Apply template if not already set
    if not sspl_populated(loan_id):
        apply_sspl_template(loan_id)
    
    # Update SSPL to match Section C
    # All fees must be in CAPITAL letters and same sequence
    sspl_updates = []
    for fee in section_c_fees:
        sspl_updates.append({
            "name": fee.name.upper(),
            "amount": fee.amount,
            "provider": fee.provider
        })
    
    write_sspl(loan_id, sspl_updates)
    
    # Additional entries
    if get_field(loan_id, "pest_inspection_fee"):
        add_sspl_entry(loan_id, "Pest Inspection", "pest_inspection")
    if get_field(loan_id, "survey_fee"):
        add_sspl_entry(loan_id, "Land Survey", "survey")
```

---

## 11. Error Handling & Escalation

| Issue | Severity | Action | Blocking |
|-------|----------|--------|----------|
| LE due date passed | 🔴 Critical | Escalate to Supervisor | ✅ Yes |
| Mavent Fail | 🔴 Critical | Clear before sending | ✅ Yes |
| ATR/QM Red Flag | 🔴 Critical | Fix before sending | ✅ Yes |
| FACT Act blank | 🟡 Medium | Notify LO/Processor for credit pull | ✅ Yes |
| LO not licensed in state | 🔴 Critical | Cannot proceed | ✅ Yes |
| Non-Conventional loan | 🟡 Medium | Log for manual (MVP) | ✅ Yes |
| Texas property | 🟡 Medium | Log for manual (MVP) | ✅ Yes |
| Missing optional field | 🟢 Low | Log warning, continue | ❌ No |

---

## 12. MVP vs Full Implementation

### Phase 1 (MVP - 2 weeks)

| Feature | Include | Notes |
|---------|---------|-------|
| TRID date checks | ✅ | Application Date, LE Due Date |
| Form field validation | ✅ | 1003 URLA, RegZ-LE basics |
| Conventional MI calc | ✅ | LTV > 80% check |
| Cash to Close match | ✅ | Purchase vs Refi logic |
| Mavent check | ✅ | **Mandatory** |
| ATR/QM check | ✅ | **Mandatory** |
| Order eDisclosures | ✅ | Initial Disclosure only |
| Locked loan TRID check | ✅ | Basic implementation |

### Phase 2

| Feature | Notes |
|---------|-------|
| FHA/VA/USDA MI | Full MI calculator |
| Texas state rules | Line 810, 12-day letter |
| COC/LE processing | Change detection |
| SSPL updates | Full matching |
| Home Counseling Providers | Get Agencies automation |
| 4506-C auto-population | Tax transcript forms |

### Phase 3

| Feature | Notes |
|---------|-------|
| All state-specific rules | FL, CO, IL, etc. |
| Full form automation | All 15+ forms |
| Blend integration | eConsent tracking |
| Queue management | Auto-routing |

---

## 13. Tool Inventory (MVP)

### Verification Tools
```python
check_trid_compliance(loan_id: str) -> TRIDResult
check_application_date(loan_id: str) -> DateCheckResult
check_le_due_date(loan_id: str) -> DateCheckResult
check_disclosure_alert(loan_id: str) -> bool
check_lock_status(loan_id: str) -> LockStatus
verify_lo_license(loan_id: str) -> LOVerificationResult
check_form_fields(loan_id: str, form_name: str) -> FormCheckResult
```

### Preparation Tools
```python
update_regz_le(loan_id: str) -> Dict
calculate_mi(loan_id: str) -> MIResult
update_2015_itemization(loan_id: str) -> Dict
match_cash_to_close(loan_id: str) -> CashToCloseResult
update_section_800(loan_id: str) -> Dict
update_section_1000(loan_id: str) -> Dict
update_section_1100(loan_id: str) -> Dict
update_section_m(loan_id: str) -> Dict
```

### Send Tools
```python
check_mavent_compliance(loan_id: str) -> MaventResult
check_atr_qm(loan_id: str) -> ATRQMResult
order_disclosures(loan_id: str, type: str) -> OrderResult
update_queue_status(loan_id: str, status: str) -> bool
```

---

*Document generated December 1, 2025 - Based on Disclosure Desk SOP*

