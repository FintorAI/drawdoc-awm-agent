# Shared Utilities (`packages/shared`)

This package contains shared utilities used by **both Disclosure Agent and Draw Docs Agent** pipelines.

---

## 📋 Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AGENT PIPELINE USAGE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────┐     ┌────────────────────────────────┐  │
│  │    DISCLOSURE AGENT (v2)      │     │      DRAW DOCS AGENT           │  │
│  │    Initial LE → COC/LE → CD   │     │      After CTC + CD ACK        │  │
│  └───────────────────────────────┘     └────────────────────────────────┘  │
│              │                                      │                       │
│              └──────────────┬───────────────────────┘                       │
│                             ▼                                               │
│              ┌─────────────────────────────┐                                │
│              │      SHARED UTILITIES       │                                │
│              │      (packages/shared)      │                                │
│              └─────────────────────────────┘                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 File Structure

```
packages/shared/
├── __init__.py              # Public exports
├── README.md                # This file
│
├── ─── CORE UTILITIES ───
├── auth.py                  # OAuth2 authentication
├── encompass_client.py      # HTTP client wrapper
├── encompass_io.py          # Field read/write API
├── constants.py             # Shared constants & field IDs
├── csv_utils.py             # CSV field mapping utilities
│
├── ─── DISCLOSURE AGENT v2 ───
├── trid_checker.py          # TRID compliance (app date, LE due date)
├── form_validator.py        # Form field validation (15+ forms)
├── regz_le_updater.py       # RegZ-LE form updates
├── ctc_matcher.py           # Cash to Close matching
├── atr_qm_checker.py        # ATR/QM flag validation
├── disclosure_orderer.py    # eDisclosures API ordering
├── milestone_checker.py     # Pre-check (milestones, tracking)
│
├── ─── SHARED (DISCLOSURE + DRAW DOCS) ───
├── mi_calculator.py         # MI calculation (all loan types)
├── fee_tolerance.py         # Fee tolerance checking
├── mavent_checker.py        # Mavent compliance check
│
└── ─── TESTING ───
    └── test_auth.py         # Authentication tests
```

---

## 🔧 Module Reference

### Core Utilities

#### ⚠️ `encompass_client.py` vs `encompass_io.py`

**These two files serve similar purposes but are used by different parts of the codebase:**

| File | Method | Used By | Status |
|------|--------|---------|--------|
| `encompass_io.py` | Direct `requests` HTTP calls | **v2 shared modules** | ✅ Primary |
| `encompass_client.py` | `copilotagent.EncompassConnect` | **Draw Docs agents** | 📦 Legacy |

**For v2 Disclosure, use `encompass_io.py` functions:**
```python
from packages.shared import read_fields, write_fields
```

**For Draw Docs (legacy), use `encompass_client.py`:**
```python
from packages.shared import get_encompass_client
client = get_encompass_client()
```

---

#### `auth.py` - OAuth2 Authentication
```python
from packages.shared import get_access_token, get_auth_manager

# Get current access token (auto-refreshes if expired)
token = get_access_token()

# Get auth manager for more control
auth_manager = get_auth_manager()
token_info = auth_manager.get_token()
```

**Environment Variables:**
- `ENCOMPASS_CLIENT_ID` - OAuth2 client ID
- `ENCOMPASS_CLIENT_SECRET` - OAuth2 client secret
- `ENCOMPASS_INSTANCE_ID` - Encompass instance ID
- `ENCOMPASS_USERNAME` - API username
- `ENCOMPASS_PASSWORD` - API password
- `ENCOMPASS_API_BASE_URL` - Base URL (default: `https://api.elliemae.com`)

---

#### `encompass_io.py` - Field I/O
```python
from packages.shared import read_fields, read_field, write_fields, write_field

# Read multiple fields
values = read_fields(loan_id, ["4000", "4002", "1109"])
borrower_name = values.get("4000")

# Read single field
interest_rate = read_field(loan_id, "3")

# Write multiple fields
write_fields(loan_id, {"4000": "John", "4002": "Doe"})

# Write single field
write_field(loan_id, "1109", 500000.00)

# Get loan metadata
loan_type = get_loan_type(loan_id)       # "Conventional", "FHA", etc.
loan_purpose = get_loan_purpose(loan_id)  # "Purchase", "Refinance"
summary = get_loan_summary(loan_id)       # Full summary dict
```

---

#### `constants.py` - Shared Constants
```python
from packages.shared import (
    LoanType, LoanPurpose, PropertyState,
    FieldIds, DISCLOSURE_CRITICAL_FIELDS,
    REGZ_LE_FIELDS, TRID_FIELDS, ATR_QM_FIELDS,
    MVPExclusions,
)

# Check MVP eligibility
if LoanType.is_mvp_supported(loan_type):
    # Process as MVP
    pass

if PropertyState.is_mvp_supported("TX"):
    # False - Texas excluded from MVP
    pass
```

---

### Disclosure Agent v2 Modules

#### `trid_checker.py` - TRID Compliance
```python
from packages.shared import (
    TRIDChecker, check_trid_compliance, check_closing_date,
    calculate_le_due_date, get_trid_checker,
)

# Check TRID compliance (app date, LE due within 3 business days)
checker = get_trid_checker()
result = checker.check_le_timing(loan_id)

if result.is_past_due:
    print(f"BLOCKING: {result.action}")  # Escalate to supervisor
else:
    print(f"LE due in {result.days_remaining} days")

# Check closing date (G8: 15-day rule)
closing_result = checker.check_closing_date(loan_id)
if not closing_result.is_compliant:
    print(f"BLOCKING: {closing_result.blocking_reason}")
```

---

#### `form_validator.py` - Form Validation
```python
from packages.shared import (
    FormValidator, validate_disclosure_forms,
    check_hard_stop_fields, HARD_STOP_FIELDS,
)

# Validate all required forms
validator = get_form_validator()
result = validator.validate_all_required_forms(loan_id)

if not result.all_required_present:
    print(f"Missing: {result.missing_fields}")

# Check hard stops (G1: Phone/Email required)
hard_stop_result = validator.check_hard_stops(loan_id)
if hard_stop_result.has_hard_stops:
    print(f"BLOCKING: {hard_stop_result.blocking_message}")
```

---

#### `regz_le_updater.py` - RegZ-LE Updates
```python
from packages.shared import (
    RegZLEUpdater, update_regz_le_form,
    get_late_charge, get_assumption_text,
)

# Update RegZ-LE form per SOP
updater = get_regz_le_updater()
result = updater.update(loan_id)

# Get late charge settings
late_days, late_percent = get_late_charge("Conventional", "CA")
# Returns: (15, 5.0) for Conventional
# Returns: (15, 4.0) for FHA/VA or NC state
```

---

#### `ctc_matcher.py` - Cash to Close Matching
```python
from packages.shared import CTCMatcher, match_cash_to_close

# Match cash to close
matcher = get_ctc_matcher()
result = matcher.match(loan_id)

if not result.matched:
    print(f"CTC mismatch: calculated ${result.calculated:.2f}, "
          f"displayed ${result.displayed:.2f}")
```

---

#### `atr_qm_checker.py` - ATR/QM Validation
```python
from packages.shared import (
    ATRQMChecker, check_atr_qm_flags, get_points_fees_status,
)

# Check ATR/QM flags (must be GREEN)
checker = get_atr_qm_checker()
result = checker.check(loan_id)

if not result.passed:
    print(f"BLOCKING: Red flags = {result.red_flags}")
```

---

#### `mavent_checker.py` - Compliance Check
```python
from packages.shared import MaventChecker, check_mavent_compliance

# Check Mavent compliance (MANDATORY before sending)
checker = get_mavent_checker()
result = checker.check(loan_id)

if not result.passed:
    print(f"BLOCKING: {len(result.issues)} compliance issues")
```

---

#### `disclosure_orderer.py` - eDisclosures API
```python
from packages.shared import (
    DisclosureOrderer, order_initial_disclosure, audit_loan_for_disclosure,
)

# Order initial disclosure via eDisclosures API
orderer = get_disclosure_orderer()

# Step 1: Audit loan
audit_result = orderer.audit(loan_id, application_id)

# Step 2: Create document order
doc_set_id = orderer.create_order(audit_result.audit_snapshot_id)

# Step 3: Deliver to borrower
result = orderer.deliver(loan_id, doc_set_id, borrower_info)
```

---

#### `milestone_checker.py` - Pre-Check
```python
from packages.shared import (
    MilestoneChecker, run_pre_check,
    get_disclosure_tracking_logs, get_loan_milestones,
)

# Run comprehensive pre-check
result = run_pre_check(loan_id)

if not result.can_proceed:
    print(f"BLOCKING: {result.blocking_reason}")
else:
    print("Loan eligible for initial disclosure")

# Check if LE already sent
tracking = get_disclosure_tracking_logs(loan_id)
if tracking.initial_le_sent:
    print("Initial LE already sent - COC flow required")
```

---

### Shared Modules (Disclosure + Draw Docs)

> **Note**: `handoff.py` was removed. Draw Docs is **queue-driven**, not handoff-driven.
> It monitors Encompass for: CTC + CD Approved + CD ACK'd + 3-day wait passed.

#### `mi_calculator.py` - MI Calculation
```python
from packages.shared import (
    MIResult, calculate_mi,
    calculate_conventional_mi, calculate_fha_mip,
    calculate_va_funding_fee, calculate_usda_guarantee,
)

# Calculate MI based on loan type
result = calculate_mi(loan_id)

if result.requires_mi:
    print(f"Monthly MI: ${result.monthly_amount:.2f}")
    print(f"Cancel at LTV: {result.cancel_at_ltv}%")

# Conventional: LTV > 80% requires MI
# FHA: UFMIP 1.75% + annual MIP
# VA: Funding fee (varies by usage/down payment)
# USDA: 1% upfront + annual fee
```

---

#### `fee_tolerance.py` - Fee Tolerance (CD Processing)
```python
from packages.shared import (
    check_fee_tolerance, ToleranceResult,
    SECTION_A_FEES, SECTION_B_FEES,
)

# Check fee tolerance between LE and CD
result = check_fee_tolerance(le_fees, cd_fees)

if result.has_violations:
    print(f"Cure needed: ${result.total_cure_needed:.2f}")
    # Section A: 0% tolerance (cannot increase)
    # Section B: 10% aggregate tolerance
    # Section C: No tolerance (borrower shopped)
```

---

## 🔄 Architecture Comparison

### v1 vs v2 Disclosure

| Aspect | v1 (Deprecated) | v2 (Current) |
|--------|-----------------|--------------|
| Primary Document | Closing Disclosure (CD) | **Loan Estimate (LE)** |
| Timing | After CTC | **Within 3 business days** of app |
| Mavent Check | Not needed | **MANDATORY** |
| ATR/QM Check | Missing | **MANDATORY** |
| Form Validation | ~20 generic fields | **15+ SOP-specific forms** |
| Pre-Check | None | **Milestones + Disclosure Tracking** |

---

## 🚨 MVP Scope

**Supported:**
- Loan Type: **Conventional only**
- States: **NV, CA only**
- Disclosure Type: **Initial LE only**

**Excluded (Phase 2+):**
- FHA/VA/USDA loans
- Texas properties (special rules)
- COC/Revised LE processing
- CD processing via Disclosure Agent

---

## 📦 Import Examples

```python
# Full import
from packages.shared import (
    # Core
    get_access_token, read_fields, write_fields,
    get_loan_type, get_loan_purpose,
    
    # v2 Disclosure
    check_trid_compliance, validate_disclosure_forms,
    update_regz_le_form, match_cash_to_close,
    check_atr_qm_flags, check_mavent_compliance,
    order_initial_disclosure, run_pre_check,
    
    # Shared
    calculate_mi, check_fee_tolerance,
    
    # Constants
    LoanType, PropertyState, MVPExclusions,
)
```

---

## 🧪 Testing

```bash
# Test authentication
python -m packages.shared.test_auth

# Run from disclosure agent tests
cd agents/disclosure
python -m pytest test_orchestrator.py -v
```

---

## 📝 Adding New Modules

1. Create module file in `packages/shared/`
2. Add exports to `__init__.py`
3. Update this README
4. Add tests

---

---

## 🔧 Future Consolidation Opportunities

### Potential Redundancy: `encompass_client.py`

When Draw Docs is refactored to v2 architecture, `encompass_client.py` can be **removed** and all agents can use `encompass_io.py` directly. This would:
- Eliminate the `copilotagent` dependency
- Standardize on direct `requests` HTTP calls
- Reduce code duplication

**Migration path:**
```python
# OLD (Draw Docs)
client = get_encompass_client()
values = client.read_loan_fields(loan_id, ["4000", "4002"])

# NEW (v2 style)
values = read_fields(loan_id, ["4000", "4002"])
```

---

*Last Updated: December 2, 2025*
*Architecture: Disclosure Agent v2 (SOP-Aligned)*

