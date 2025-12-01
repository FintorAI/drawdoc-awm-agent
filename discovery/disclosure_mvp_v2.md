# Disclosure Agent MVP v2 - Task Breakdown

## Document Info
- **Created**: December 1, 2025
- **Supersedes**: `disclosure-mvp-build-plan.md`
- **Based On**: Disclosure Desk SOP, `disclosure_architecture_v2.md`
- **Duration**: 2 weeks (10 working days)
- **Owner**: Naomi

---

## 🎯 MVP Definition (Corrected)

### What We're Building

An agent that processes **Initial Loan Estimate (LE) disclosures** for **Conventional loans** only.

### Success Criteria

| # | Criterion | Validation |
|---|-----------|------------|
| 1 | TRID compliance check passes | App Date + LE Due Date validated |
| 2 | Form fields validated | 1003 URLA, RegZ-LE key fields checked |
| 3 | Conventional MI calculated | LTV > 80% triggers MI calc |
| 4 | Cash to Close matches | CTC on LE page 2 matches calculated |
| 5 | Mavent check passes | No Fail/Alert/Warning |
| 6 | ATR/QM flags green | Points & Fees test passes |
| 7 | eDisclosures ordered | Initial Disclosure sent via eFolder |

### Explicit Non-Goals (MVP)

| Feature | Reason | Phase |
|---------|--------|-------|
| FHA/VA/USDA loans | Complex MI, defer | Phase 2 |
| Texas properties | State rules, defer | Phase 2 |
| COC/Revised LE | Change detection complex | Phase 2 |
| Closing Disclosure (CD) | Comes after CTC | Phase 2 |
| Home Counseling Providers | Manual for now | Phase 2 |
| 4506-C auto-population | Manual for now | Phase 2 |
| SSPL updates | Manual for now | Phase 2 |
| Signature tracking | Not needed for LE | Phase 3 |

**Non-MVP Cases**: Log `"Requires manual processing: {reason}"` and hand off.

---

## 📅 Sprint Plan (10 Days)

### Week 1: Foundation + Core Logic

| Day | Focus | Deliverables |
|-----|-------|--------------|
| **1** | TRID Compliance | `trid_checker.py`, date validation tools |
| **2** | Form Validation | `form_validator.py`, 1003 URLA checks |
| **3** | RegZ-LE Updates | `regz_le_updater.py`, field updates |
| **4** | MI Calculation | `mi_calculator.py`, Conventional MI |
| **5** | Cash to Close | `ctc_matcher.py`, Purchase vs Refi logic |

### Week 2: Compliance + Integration

| Day | Focus | Deliverables |
|-----|-------|--------------|
| **6** | Mavent Check | `mavent_checker.py`, compliance tool |
| **7** | ATR/QM Check | `atr_qm_checker.py`, flags validation |
| **8** | eDisclosures Order | `disclosure_orderer.py`, send logic |
| **9** | Agent Integration | Update orchestrator, wire agents |
| **10** | Testing + Polish | End-to-end tests, edge cases |

---

## 📋 Detailed Task Breakdown

### Day 1: TRID Compliance Checker

**Goal**: Validate Application Date and LE Due Date per TRID rules.

#### Files to Create

**1. `packages/shared/trid_checker.py`**

```python
"""
TRID compliance checking utilities.
Per SOP: LE must be sent within 3 business days of Application Date.
"""

from datetime import date, timedelta
from typing import NamedTuple
from dataclasses import dataclass

@dataclass
class TRIDResult:
    compliant: bool
    application_date: date
    le_due_date: date
    days_remaining: int
    action: str = None
    
class TRIDChecker:
    def check_le_timing(self, loan_id: str) -> TRIDResult:
        """
        Check if we're within the 3 business day window.
        """
        app_date = self.get_application_date(loan_id)
        if not app_date:
            return TRIDResult(
                compliant=False,
                application_date=None,
                le_due_date=None,
                days_remaining=0,
                action="Application Date not set - BLOCKING"
            )
        
        le_due = self.calculate_le_due_date(app_date)
        today = date.today()
        
        if today > le_due:
            return TRIDResult(
                compliant=False,
                application_date=app_date,
                le_due_date=le_due,
                days_remaining=0,
                action="LE Due Date PASSED - Escalate to Supervisor"
            )
        
        days_remaining = (le_due - today).days
        return TRIDResult(
            compliant=True,
            application_date=app_date,
            le_due_date=le_due,
            days_remaining=days_remaining
        )
    
    def calculate_le_due_date(self, app_date: date) -> date:
        """
        Calculate LE due date = 3 business days from application.
        Excludes Sundays and federal holidays.
        """
        business_days = 0
        current = app_date
        
        while business_days < 3:
            current += timedelta(days=1)
            if self.is_business_day(current):
                business_days += 1
        
        return current
    
    def is_business_day(self, d: date) -> bool:
        # Sunday = 6
        if d.weekday() == 6:
            return False
        # TODO: Add federal holidays
        return True
    
    def get_application_date(self, loan_id: str) -> date:
        # Read from Encompass
        pass
    
    def check_disclosure_alert(self, loan_id: str) -> bool:
        """
        SOP: "Send Initial Disclosures" alert must exist
        """
        # Read from Alerts & Messages
        pass
```

**2. `agents/disclosure/subagents/verification_agent/tools/trid_tools.py`**

```python
"""
ADK tools for TRID checking.
"""

from google.adk.tools import ToolContext
from packages.shared.trid_checker import TRIDChecker

checker = TRIDChecker()

def check_trid_compliance(loan_id: str, ctx: ToolContext) -> dict:
    """
    Check TRID compliance for loan.
    
    Returns:
        dict with compliant status, dates, and any required action.
    """
    result = checker.check_le_timing(loan_id)
    
    return {
        "compliant": result.compliant,
        "application_date": str(result.application_date),
        "le_due_date": str(result.le_due_date),
        "days_remaining": result.days_remaining,
        "action": result.action,
        "blocking": not result.compliant
    }

def check_disclosure_alert_exists(loan_id: str, ctx: ToolContext) -> dict:
    """
    Check if "Send Initial Disclosures" alert exists.
    """
    exists = checker.check_disclosure_alert(loan_id)
    
    return {
        "alert_exists": exists,
        "blocking": not exists,
        "action": None if exists else "Alert missing - TRID info may be incomplete"
    }
```

#### Tests to Write

```python
# tests/test_trid_checker.py

def test_le_due_date_calculation():
    """3 business days from Monday = Thursday"""
    pass

def test_le_due_date_over_weekend():
    """3 business days from Friday = Wednesday"""
    pass

def test_past_due_date_escalation():
    """Past due should return escalate action"""
    pass
```

#### Definition of Done - Day 1
- [ ] `TRIDChecker` class implemented
- [ ] `check_trid_compliance` tool works
- [ ] `check_disclosure_alert_exists` tool works
- [ ] Unit tests pass
- [ ] Tested against 1 real loan in Encompass

---

### Day 2: Form Field Validation

**Goal**: Validate key fields in 1003 URLA and other required forms.

#### Files to Create

**1. `packages/shared/form_validator.py`**

```python
"""
Form field validation per SOP requirements.
"""

from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class FormCheckResult:
    form_name: str
    all_valid: bool
    missing_fields: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

# From SOP - Critical fields that must not be blank
REQUIRED_FIELDS = {
    "1003_URLA_Lender": [
        "borrower_name",      # Field ID: 4000
        "borrower_ssn",       # Field ID: 65
        "property_address",   # Field ID: 11
        "property_city",      # Field ID: 12
        "property_state",     # Field ID: 14
        "property_zip",       # Field ID: 15
        "loan_amount",        # Field ID: 1109
        "loan_purpose",       # Field ID: 19
        "occupancy_type",     # Field ID: 1811
    ],
    "1003_URLA_Part1": [
        "mailing_address",
        # SOP: "Same as Current" should be marked
    ],
    "1003_URLA_Part2": [
        "current_employment",
        "gross_monthly_income",
        "total_income",
    ],
    "1003_URLA_Part4": [
        "lo_name",
        "lo_nmls_id",
        "lo_company_nmls",
    ],
    "Borrower_Summary_Origination": [
        "channel",
        "current_status",
        "application_date",
    ],
}

class FormValidator:
    def validate_form(self, loan_id: str, form_name: str) -> FormCheckResult:
        """Validate all required fields for a form."""
        if form_name not in REQUIRED_FIELDS:
            return FormCheckResult(
                form_name=form_name,
                all_valid=True,
                warnings=[f"Unknown form: {form_name}"]
            )
        
        required = REQUIRED_FIELDS[form_name]
        values = self.get_form_fields(loan_id, required)
        
        missing = []
        for field_name in required:
            if not values.get(field_name):
                missing.append(field_name)
        
        return FormCheckResult(
            form_name=form_name,
            all_valid=len(missing) == 0,
            missing_fields=missing
        )
    
    def validate_all_required_forms(self, loan_id: str) -> Dict[str, FormCheckResult]:
        """Validate all required forms for disclosure."""
        results = {}
        for form_name in REQUIRED_FIELDS.keys():
            results[form_name] = self.validate_form(loan_id, form_name)
        return results
    
    def get_form_fields(self, loan_id: str, field_names: List[str]) -> Dict:
        # Read from Encompass
        pass
```

**2. `agents/disclosure/subagents/verification_agent/tools/form_tools.py`**

```python
"""
ADK tools for form validation.
"""

from packages.shared.form_validator import FormValidator

validator = FormValidator()

def validate_disclosure_forms(loan_id: str, ctx) -> dict:
    """
    Validate all required forms for disclosure.
    
    Returns summary of all form validations with any missing fields.
    """
    results = validator.validate_all_required_forms(loan_id)
    
    all_valid = all(r.all_valid for r in results.values())
    all_missing = []
    
    for form_name, result in results.items():
        if result.missing_fields:
            all_missing.extend([f"{form_name}.{f}" for f in result.missing_fields])
    
    return {
        "all_valid": all_valid,
        "missing_fields": all_missing,
        "blocking": not all_valid,
        "form_results": {k: v.__dict__ for k, v in results.items()}
    }

def validate_single_form(loan_id: str, form_name: str, ctx) -> dict:
    """Validate a specific form."""
    result = validator.validate_form(loan_id, form_name)
    return result.__dict__
```

#### Definition of Done - Day 2
- [ ] `FormValidator` class implemented
- [ ] All SOP-required fields defined
- [ ] `validate_disclosure_forms` tool works
- [ ] Returns clear list of missing fields
- [ ] Tested against real loan

---

### Day 3: RegZ-LE Updates

**Goal**: Update RegZ-LE form fields per SOP requirements.

#### Files to Create

**1. `packages/shared/regz_le_updater.py`**

```python
"""
RegZ-LE form updater per SOP.
"""

from datetime import date
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class RegZLEUpdateResult:
    success: bool
    updates_made: Dict[str, any]
    errors: list = None

class RegZLEUpdater:
    def update(self, loan_id: str) -> RegZLEUpdateResult:
        """
        Update RegZ-LE form per SOP requirements.
        """
        updates = {}
        loan_type = self.get_loan_type(loan_id)
        property_state = self.get_property_state(loan_id)
        
        # 1. LE Date Issued = Current Date
        updates["le_date_issued"] = date.today().isoformat()
        
        # 2. Interest Accrual Options
        updates["interest_days_per_year"] = "360/360"
        updates["zero_percent_payment_option"] = ""  # Must be blank
        updates["use_simple_interest_accrual"] = ""  # Must be blank
        updates["biweekly_interim_days"] = 365
        
        # 3. Late Charge - varies by loan type and state
        late_days, late_pct = self.get_late_charge(loan_type, property_state)
        updates["late_charge_days"] = late_days
        updates["late_charge_percent"] = late_pct
        
        # 4. Assumption
        updates["assumption"] = self.get_assumption_text(loan_type)
        
        # 5. Handle Buydown if marked
        if self.has_buydown(loan_id):
            buydown_updates = self.get_buydown_updates(loan_id)
            updates.update(buydown_updates)
        
        # 6. Handle Prepayment
        prepay_updates = self.get_prepayment_updates(loan_id)
        updates.update(prepay_updates)
        
        # Write updates
        success = self.write_updates(loan_id, updates)
        
        return RegZLEUpdateResult(
            success=success,
            updates_made=updates
        )
    
    def get_late_charge(self, loan_type: str, state: str) -> tuple:
        """
        SOP Late Charge Rules:
        - Conventional: 15 Days, 5%
        - FHA/VA: 15 Days, 4%
        - North Carolina: 4% for ALL loan types
        """
        if state == "NC":
            return (15, 4.0)
        
        if loan_type == "Conventional":
            return (15, 5.0)
        elif loan_type in ["FHA", "VA"]:
            return (15, 4.0)
        
        return (15, 5.0)  # Default
    
    def get_assumption_text(self, loan_type: str) -> str:
        """
        SOP Assumption Rules:
        - Conventional: "may not"
        - FHA/VA: "may, subject to conditions"
        """
        if loan_type == "Conventional":
            return "may not"
        elif loan_type in ["FHA", "VA"]:
            return "may, subject to conditions"
        return "may not"
    
    def has_buydown(self, loan_id: str) -> bool:
        # Check buydown_marked field
        pass
    
    def get_buydown_updates(self, loan_id: str) -> Dict:
        """Get buydown field updates if buydown is marked."""
        return {
            "buydown_contributor": self.get_field(loan_id, "buydown_contributor"),
            "buydown_type": self.get_field(loan_id, "buydown_type"),
            "buydown_rate_percent": self.get_field(loan_id, "buydown_rate"),
            "buydown_term": self.get_field(loan_id, "buydown_term"),
        }
    
    def get_prepayment_updates(self, loan_id: str) -> Dict:
        """
        SOP: If Prepayment is "Will, May, May be", update penalty fields.
        """
        prepay_status = self.get_field(loan_id, "prepayment_status")
        
        if prepay_status in ["Will not", "May not"]:
            return {}
        
        return {
            "prepayment_type": self.get_field(loan_id, "prepay_type"),
            "prepayment_period": self.get_field(loan_id, "prepay_period"),
            "prepayment_percent": self.get_field(loan_id, "prepay_percent"),
        }
    
    # Encompass field access methods
    def get_loan_type(self, loan_id: str) -> str:
        pass
    
    def get_property_state(self, loan_id: str) -> str:
        pass
    
    def get_field(self, loan_id: str, field: str):
        pass
    
    def write_updates(self, loan_id: str, updates: Dict) -> bool:
        pass
```

**2. `agents/disclosure/subagents/preparation_agent/tools/regz_le_tools.py`**

```python
"""ADK tools for RegZ-LE updates."""

from packages.shared.regz_le_updater import RegZLEUpdater

updater = RegZLEUpdater()

def update_regz_le_form(loan_id: str, ctx) -> dict:
    """
    Update RegZ-LE form with SOP-required values.
    """
    result = updater.update(loan_id)
    
    return {
        "success": result.success,
        "updates_made": result.updates_made,
        "errors": result.errors
    }
```

#### Definition of Done - Day 3
- [ ] `RegZLEUpdater` class implemented
- [ ] Late charge logic correct per loan type
- [ ] Assumption logic correct
- [ ] Buydown handling works
- [ ] Prepayment handling works
- [ ] Tested against real loan

---

### Day 4: MI Calculation (Conventional)

**Goal**: Calculate Mortgage Insurance for Conventional loans with LTV > 80%.

#### Files to Create

**1. `packages/shared/mi_calculator.py`**

```python
"""
Mortgage Insurance calculator.
MVP: Conventional only.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class MIResult:
    required: bool
    loan_type: str
    ltv: float
    source: str = None           # "mi_cert" or "needs_update" or "not_required"
    monthly_amount: float = 0.0
    upfront_amount: float = 0.0
    cancel_at_ltv: float = None
    action: str = None

class MICalculator:
    def calculate(self, loan_id: str) -> MIResult:
        """
        Calculate MI based on loan type.
        MVP: Conventional only.
        """
        loan_type = self.get_loan_type(loan_id)
        
        if loan_type != "Conventional":
            return MIResult(
                required=False,
                loan_type=loan_type,
                ltv=0,
                source="not_supported_mvp",
                action=f"Requires manual processing: {loan_type} loan"
            )
        
        return self.calculate_conventional_mi(loan_id)
    
    def calculate_conventional_mi(self, loan_id: str) -> MIResult:
        """
        SOP: If LTV > 80%, MIP must be updated.
        If not updated, request branch to update.
        """
        loan_amount = self.get_field(loan_id, "loan_amount")
        appraised_value = self.get_field(loan_id, "appraised_value")
        
        ltv = (loan_amount / appraised_value) * 100
        
        if ltv <= 80:
            return MIResult(
                required=False,
                loan_type="Conventional",
                ltv=ltv,
                source="not_required"
            )
        
        # Check for MI Certificate
        mi_cert = self.get_mi_certificate(loan_id)
        
        if mi_cert and mi_cert.monthly_rate:
            monthly = loan_amount * mi_cert.monthly_rate / 12
            return MIResult(
                required=True,
                loan_type="Conventional",
                ltv=ltv,
                source="mi_cert",
                monthly_amount=monthly,
                upfront_amount=mi_cert.upfront or 0,
                cancel_at_ltv=78.0  # Standard cancellation
            )
        
        # MI Certificate not available - flag for branch
        return MIResult(
            required=True,
            loan_type="Conventional",
            ltv=ltv,
            source="needs_update",
            action="MIP required but not set - request branch to update"
        )
    
    def get_loan_type(self, loan_id: str) -> str:
        pass
    
    def get_field(self, loan_id: str, field: str):
        pass
    
    def get_mi_certificate(self, loan_id: str):
        pass
```

**2. `agents/disclosure/subagents/preparation_agent/tools/mi_tools.py`**

```python
"""ADK tools for MI calculation."""

from packages.shared.mi_calculator import MICalculator

calculator = MICalculator()

def calculate_mortgage_insurance(loan_id: str, ctx) -> dict:
    """
    Calculate MI for the loan.
    MVP: Conventional only.
    """
    result = calculator.calculate(loan_id)
    
    return {
        "required": result.required,
        "loan_type": result.loan_type,
        "ltv": round(result.ltv, 3),
        "source": result.source,
        "monthly_amount": round(result.monthly_amount, 2),
        "upfront_amount": round(result.upfront_amount, 2),
        "cancel_at_ltv": result.cancel_at_ltv,
        "action": result.action,
        "blocking": result.source == "needs_update"
    }
```

#### Definition of Done - Day 4
- [ ] `MICalculator` class implemented
- [ ] LTV calculation correct
- [ ] MI Certificate lookup works
- [ ] "needs_update" action returned when MI Cert missing
- [ ] Tested with LTV > 80% and LTV <= 80% loans

---

### Day 5: Cash to Close Matching

**Goal**: Match Cash to Close per SOP (Purchase vs Refinance logic).

#### Files to Create

**1. `packages/shared/ctc_matcher.py`**

```python
"""
Cash to Close matching per SOP.
"""

from dataclasses import dataclass

@dataclass
class CTCResult:
    matched: bool
    calculated_ctc: float
    displayed_ctc: float
    difference: float
    updates_made: dict
    
class CTCMatcher:
    def match_cash_to_close(self, loan_id: str) -> CTCResult:
        """
        SOP: CTC must match Estimated Cash to Close on LE page 2.
        Different settings for Purchase vs Refinance.
        """
        purpose = self.get_loan_purpose(loan_id)
        updates = {}
        
        if purpose == "Purchase":
            # SOP: Check these boxes for Purchase
            updates = {
                "use_actual_down_payment": True,
                "closing_costs_financed": True,
                "include_payoffs_in_adjustments": True,
            }
        else:  # Refinance
            # SOP: Check Alternative form for Refinance
            updates = {
                "alternative_form_checkbox": True,
            }
        
        # Apply updates
        self.write_updates(loan_id, updates)
        
        # Verify match
        calculated = self.calculate_ctc(loan_id)
        displayed = self.get_displayed_ctc(loan_id)
        
        difference = abs(calculated - displayed)
        matched = difference < 0.01  # Allow penny rounding
        
        return CTCResult(
            matched=matched,
            calculated_ctc=calculated,
            displayed_ctc=displayed,
            difference=difference,
            updates_made=updates
        )
    
    def get_loan_purpose(self, loan_id: str) -> str:
        pass
    
    def calculate_ctc(self, loan_id: str) -> float:
        pass
    
    def get_displayed_ctc(self, loan_id: str) -> float:
        pass
    
    def write_updates(self, loan_id: str, updates: dict):
        pass
```

**2. Tool wrapper** (similar pattern)

#### Definition of Done - Day 5
- [ ] Purchase CTC logic implemented
- [ ] Refinance CTC logic implemented
- [ ] Match verification works
- [ ] Difference calculation correct
- [ ] Tested with Purchase and Refinance loans

---

### Day 6: Mavent Compliance Check

**Goal**: Check Mavent compliance (must pass before sending).

#### Files to Create

**1. `packages/shared/mavent_checker.py`**

```python
"""
Mavent compliance checking.
SOP: Must clear all Fail/Alert/Warning before sending.
"""

from dataclasses import dataclass, field
from typing import List

@dataclass
class MaventResult:
    passed: bool
    has_fails: bool = False
    has_alerts: bool = False
    has_warnings: bool = False
    issues: List[str] = field(default_factory=list)
    action: str = None

class MaventChecker:
    def check_compliance(self, loan_id: str) -> MaventResult:
        """
        SOP: Tools → Compliance Review → Preview
        All Fail/Alert/Warning must be cleared.
        """
        # Run Mavent preview
        preview = self.run_mavent_preview(loan_id)
        
        has_fails = len(preview.fails) > 0
        has_alerts = len(preview.alerts) > 0
        has_warnings = len(preview.warnings) > 0
        
        all_issues = preview.fails + preview.alerts + preview.warnings
        
        if has_fails:
            return MaventResult(
                passed=False,
                has_fails=True,
                has_alerts=has_alerts,
                has_warnings=has_warnings,
                issues=all_issues,
                action="Clear Mavent FAILS before sending - BLOCKING"
            )
        
        if has_alerts or has_warnings:
            return MaventResult(
                passed=False,
                has_alerts=has_alerts,
                has_warnings=has_warnings,
                issues=all_issues,
                action="Clear Mavent alerts/warnings before sending - BLOCKING"
            )
        
        return MaventResult(passed=True)
    
    def run_mavent_preview(self, loan_id: str):
        """Run Mavent compliance preview via Encompass."""
        pass
```

**2. Tool wrapper**

```python
def check_mavent_compliance(loan_id: str, ctx) -> dict:
    """
    Check Mavent compliance for loan.
    MANDATORY: Must pass before ordering disclosures.
    """
    result = checker.check_compliance(loan_id)
    
    return {
        "passed": result.passed,
        "has_fails": result.has_fails,
        "has_alerts": result.has_alerts,
        "has_warnings": result.has_warnings,
        "issues": result.issues,
        "action": result.action,
        "blocking": not result.passed
    }
```

#### Definition of Done - Day 6
- [ ] `MaventChecker` class implemented
- [ ] Mavent preview integration works
- [ ] Fails/Alerts/Warnings correctly detected
- [ ] Returns blocking=True when issues exist
- [ ] Tested with passing and failing loans

---

### Day 7: ATR/QM Check

**Goal**: Verify ATR/QM flags are green.

#### Files to Create

**1. `packages/shared/atr_qm_checker.py`**

```python
"""
ATR/QM checking.
SOP: Flags must be GREEN to proceed.
"""

from dataclasses import dataclass, field
from typing import List

@dataclass
class ATRQMResult:
    passed: bool
    loan_features_flag: str    # "GREEN", "YELLOW", "RED"
    points_fees_flag: str
    price_limit_flag: str
    red_flags: List[str] = field(default_factory=list)
    action: str = None

class ATRQMChecker:
    def check(self, loan_id: str) -> ATRQMResult:
        """
        SOP: Forms → ATR/QM Management → Qualification → Points and Fees
        All flags must be GREEN.
        """
        atr_qm = self.get_atr_qm_status(loan_id)
        
        flags = {
            "loan_features": atr_qm.loan_features_flag,
            "points_fees": atr_qm.points_and_fees_flag,
            "price_limit": atr_qm.price_limit_flag,
        }
        
        red_flags = [k for k, v in flags.items() if v == "RED"]
        
        if red_flags:
            return ATRQMResult(
                passed=False,
                loan_features_flag=flags["loan_features"],
                points_fees_flag=flags["points_fees"],
                price_limit_flag=flags["price_limit"],
                red_flags=red_flags,
                action=f"ATR/QM RED flags: {red_flags} - BLOCKING"
            )
        
        return ATRQMResult(
            passed=True,
            loan_features_flag=flags["loan_features"],
            points_fees_flag=flags["points_fees"],
            price_limit_flag=flags["price_limit"],
        )
    
    def get_atr_qm_status(self, loan_id: str):
        """Read ATR/QM status from Encompass."""
        pass
```

#### Definition of Done - Day 7
- [ ] `ATRQMChecker` class implemented
- [ ] ATR/QM status read from Encompass
- [ ] Red flag detection works
- [ ] Returns blocking=True when red flags exist
- [ ] Tested with passing and failing loans

---

### Day 8: eDisclosures Ordering

**Goal**: Order Initial Disclosure package via eFolder.

#### Files to Create

**1. `packages/shared/disclosure_orderer.py`**

```python
"""
Order disclosures via eFolder.
SOP: eFolder → eDisclosures → Select Product → Order eDisclosures
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class OrderResult:
    success: bool
    tracking_id: str = None
    error: str = None
    
class DisclosureOrderer:
    def order_initial_disclosure(self, loan_id: str) -> OrderResult:
        """
        Order Initial Disclosure package.
        """
        # 1. Check for mandatory audits
        audits = self.get_mandatory_audits(loan_id)
        if audits:
            return OrderResult(
                success=False,
                error=f"Clear mandatory audits first: {audits}"
            )
        
        # 2. Get product based on loan type
        loan_type = self.get_loan_type(loan_id)
        product = self.get_disclosure_product(loan_type)
        
        # 3. Order via eDisclosures
        result = self.order_edisclosures(
            loan_id=loan_id,
            product=product,
            disclosure_type="initial"
        )
        
        if result.success:
            return OrderResult(
                success=True,
                tracking_id=result.tracking_id
            )
        
        return OrderResult(
            success=False,
            error=result.error
        )
    
    def get_mandatory_audits(self, loan_id: str) -> list:
        pass
    
    def get_loan_type(self, loan_id: str) -> str:
        pass
    
    def get_disclosure_product(self, loan_type: str) -> str:
        """Map loan type to disclosure product."""
        return "Generic Product"  # Per SOP
    
    def order_edisclosures(self, loan_id: str, product: str, disclosure_type: str):
        """Call Encompass eDisclosures API."""
        pass
```

#### Definition of Done - Day 8
- [ ] `DisclosureOrderer` class implemented
- [ ] Mandatory audit check works
- [ ] eDisclosures API integration works
- [ ] Returns tracking ID on success
- [ ] Tested with real disclosure order

---

### Day 9: Agent Integration

**Goal**: Wire up all tools in the agent orchestrator.

#### Files to Modify

**1. Update `agents/disclosure/orchestrator_agent.py`**

```python
"""
Updated orchestrator with MVP flow.
"""

class DisclosureOrchestrator:
    async def process_disclosure(self, loan_id: str) -> DisclosureResult:
        """
        MVP Flow:
        1. Verification Agent - TRID, forms, lock status
        2. Preparation Agent - RegZ-LE, MI, CTC
        3. Send Agent - Mavent, ATR/QM, order
        """
        
        # Check if MVP-supported loan
        loan_type = get_loan_type(loan_id)
        property_state = get_property_state(loan_id)
        
        if loan_type != "Conventional":
            return DisclosureResult(
                success=False,
                manual_required=True,
                reason=f"Non-Conventional loan type: {loan_type}"
            )
        
        if property_state == "TX":
            return DisclosureResult(
                success=False,
                manual_required=True,
                reason="Texas property - requires manual processing"
            )
        
        # Run verification
        verification = await self.run_verification_agent(loan_id)
        if not verification.passed:
            return DisclosureResult(
                success=False,
                blocking_issues=verification.issues
            )
        
        # Run preparation
        preparation = await self.run_preparation_agent(loan_id)
        if not preparation.passed:
            return DisclosureResult(
                success=False,
                blocking_issues=preparation.issues
            )
        
        # Run send
        send = await self.run_send_agent(loan_id)
        if not send.passed:
            return DisclosureResult(
                success=False,
                blocking_issues=send.issues
            )
        
        return DisclosureResult(
            success=True,
            disclosure_ordered=True,
            tracking_id=send.tracking_id
        )
```

**2. Update agent system prompts**

Update each agent's system prompt to use the new tools.

#### Definition of Done - Day 9
- [ ] Orchestrator updated with MVP flow
- [ ] Non-MVP cases return `manual_required=True`
- [ ] All three agents wired up
- [ ] End-to-end flow works
- [ ] Tested with sample loan

---

### Day 10: Testing + Polish

**Goal**: End-to-end testing and edge case handling.

#### Test Scenarios

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Conventional, LTV < 80%, valid | Success, no MI |
| 2 | Conventional, LTV > 80%, MI Cert exists | Success, MI calculated |
| 3 | Conventional, LTV > 80%, no MI Cert | Blocking, request MI update |
| 4 | FHA loan | Manual required (non-MVP) |
| 5 | Texas property | Manual required (non-MVP) |
| 6 | Missing Application Date | Blocking, TRID fail |
| 7 | LE Due Date passed | Blocking, escalate |
| 8 | Mavent fails | Blocking, clear fails |
| 9 | ATR/QM red flags | Blocking, fix flags |
| 10 | All checks pass | Success, disclosure ordered |

#### Files to Create

**1. `tests/test_disclosure_e2e.py`**

```python
"""End-to-end disclosure tests."""

import pytest
from agents.disclosure.orchestrator_agent import DisclosureOrchestrator

@pytest.fixture
def orchestrator():
    return DisclosureOrchestrator()

class TestMVPFlow:
    async def test_conventional_ltv_under_80(self, orchestrator):
        """Conventional with LTV < 80% should pass without MI."""
        result = await orchestrator.process_disclosure("test_loan_conv_low_ltv")
        assert result.success
        # MI should not be required
        
    async def test_conventional_ltv_over_80_with_cert(self, orchestrator):
        """Conventional with LTV > 80% and MI cert should calculate MI."""
        result = await orchestrator.process_disclosure("test_loan_conv_high_ltv")
        assert result.success
        # MI should be calculated
        
    async def test_fha_returns_manual(self, orchestrator):
        """FHA loan should return manual required."""
        result = await orchestrator.process_disclosure("test_loan_fha")
        assert not result.success
        assert result.manual_required
        assert "FHA" in result.reason
        
    async def test_texas_returns_manual(self, orchestrator):
        """Texas property should return manual required."""
        result = await orchestrator.process_disclosure("test_loan_texas")
        assert not result.success
        assert result.manual_required
        assert "Texas" in result.reason

class TestBlocking:
    async def test_mavent_fail_blocks(self, orchestrator):
        """Mavent fail should block disclosure."""
        result = await orchestrator.process_disclosure("test_loan_mavent_fail")
        assert not result.success
        assert "Mavent" in str(result.blocking_issues)
        
    async def test_atr_qm_red_blocks(self, orchestrator):
        """ATR/QM red flag should block disclosure."""
        result = await orchestrator.process_disclosure("test_loan_atr_red")
        assert not result.success
        assert "ATR/QM" in str(result.blocking_issues)
```

#### Definition of Done - Day 10
- [ ] All test scenarios pass
- [ ] Edge cases handled
- [ ] Error messages are clear
- [ ] Logging is useful
- [ ] Demo-ready

---

## 📁 File Structure (Final)

```
packages/
└── shared/
    ├── __init__.py
    ├── trid_checker.py        # Day 1
    ├── form_validator.py      # Day 2
    ├── regz_le_updater.py     # Day 3
    ├── mi_calculator.py       # Day 4
    ├── ctc_matcher.py         # Day 5
    ├── mavent_checker.py      # Day 6
    ├── atr_qm_checker.py      # Day 7
    └── disclosure_orderer.py  # Day 8

agents/disclosure/
├── orchestrator_agent.py      # Updated Day 9
├── subagents/
│   ├── verification_agent/
│   │   ├── verification_agent.py
│   │   └── tools/
│   │       ├── trid_tools.py        # Day 1
│   │       └── form_tools.py        # Day 2
│   ├── preparation_agent/
│   │   ├── preparation_agent.py
│   │   └── tools/
│   │       ├── regz_le_tools.py     # Day 3
│   │       ├── mi_tools.py          # Day 4
│   │       └── ctc_tools.py         # Day 5
│   └── send_agent/
│       ├── send_agent.py
│       └── tools/
│           ├── mavent_tools.py      # Day 6
│           ├── atr_qm_tools.py      # Day 7
│           └── order_tools.py       # Day 8

tests/
├── test_trid_checker.py
├── test_form_validator.py
├── test_mi_calculator.py
├── test_disclosure_e2e.py
└── ...
```

---

## 🚀 Summary

| Day | Deliverable | Lines of Code (Est.) |
|-----|-------------|---------------------|
| 1 | TRID Checker | ~150 |
| 2 | Form Validator | ~200 |
| 3 | RegZ-LE Updater | ~200 |
| 4 | MI Calculator | ~150 |
| 5 | CTC Matcher | ~100 |
| 6 | Mavent Checker | ~100 |
| 7 | ATR/QM Checker | ~80 |
| 8 | Disclosure Orderer | ~100 |
| 9 | Agent Integration | ~200 |
| 10 | Testing | ~300 |
| **Total** | | **~1,580** |

---

*Document generated December 1, 2025 - Based on Disclosure Desk SOP*

