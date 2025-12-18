# Disclosure Agent v2 (LE-Focused)

**Last Updated**: December 18, 2025  
**Version**: 2.0 (LE-focused architecture with 22 GAPS implementations)  

---

## Overview

The Disclosure Agent automates Initial Loan Estimate (LE) disclosure preparation and delivery per the Disclosure Desk SOP. It consists of three sequential sub-agents that verify, prepare, and send disclosures.

### Key v2 Changes from v1

| Aspect | v1 (CD-focused) | v2 (LE-focused) |
|--------|-----------------|-----------------|
| **Primary Document** | Closing Disclosure (CD) | **Loan Estimate (LE)** |
| **TRID Compliance** | Not implemented | **3-business-day rule** for LE |
| **Mandatory Checks** | None | **Mavent + ATR/QM** (blocking) |
| **Hard Stops** | Generic missing fields | **Phone/Email HARD STOP (G1)** |
| **Closing Date Rule** | Not implemented | **15-day minimum (G8)** |
| **Form Validation** | ~20 generic fields | **15+ SOP-specific forms** |
| **RegZ-LE Updates** | Not implemented | **Late charge, assumption, buydown** |
| **Cash to Close** | Not implemented | **Purchase vs Refi logic** |
| **Send Method** | Email to LO | **eDisclosures API** ordering |

---

## Architecture (v2)

```
┌─────────────────────────────────────────────────────────────┐
│                  DISCLOSURE ORCHESTRATOR (v2)                │
│                                                              │
│  Step 0: PRE-CHECK                                           │
│  ├── Check milestone status                                  │
│  ├── Check disclosure tracking (LE already sent?)            │
│  └── Validate loan eligibility                               │
│                                                              │
│  Routes: Initial LE (MVP) vs COC/LE (Phase 2)                │
└────────────────────┬─────────────────────────────────────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
     ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ VERIFICATION│ │ PREPARATION │ │ SEND AGENT  │
│ AGENT (v2)  │→│ AGENT (v2)  │→│ (v2)        │
│             │ │             │ │             │
│ • TRID      │ │ • RegZ-LE   │ │ • Mavent ✓  │
│   compliance│ │   updates   │ │ • ATR/QM ✓  │
│ • Hard stops│ │ • MI calc   │ │ • eDisc API │
│   (G1)      │ │ • CTC match │ │ • Order LE  │
│ • Closing   │ │ • Field pop │ │             │
│   date (G8) │ │             │ │             │
│ • Forms     │ │             │ │             │
│ • Lock      │ │             │ │             │
│   status    │ │             │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
```

---

## Sub-Agents

### 1. Verification Agent (v2)

**Purpose**: Validate prerequisites for Initial LE disclosure.

**v2 Additions**:
- ✅ **TRID Compliance**: App Date + 3-business-day LE Due Date
- ✅ **G1 (Hard Stops)**: Missing phone/email BLOCKS disclosure
- ✅ **G8 (15-Day Rule)**: Closing date ≥ 15 days from app/lock date
- ✅ **Lock Status**: Locked vs non-locked flow
- ✅ **Form Validation**: 1003 URLA (all 4 parts), RegZ-LE, FACT Act, etc.

**Blocking Conditions**:
- Application Date not set
- LE Due Date passed → Escalate to Supervisor
- Missing Phone or Email → HARD STOP
- Closing date < 15 days
- Texas property (special rules)
- Non-Conventional loan type

**GAPS Implemented**: G1 (Phone/Email Hard Stop), G2 (FACT Act), G8 (15-Day Rule), G9 (USPS Validation), G10 (URLA Part 1), G11 (LO NMLS), G12 (Borrower Summary), G13 (Comments), G14 (Credit Validation), G15 (Consent), G17 (Company License)

**Tools**: `check_trid_dates`, `check_hard_stops`, `check_closing_date_rule`, `validate_disclosure_form_fields`, `check_mvp_eligibility`, plus 9 GAPS validation tools

[📁 Full README](./subagents/verification_agent/README.md)

---

### 2. Preparation Agent (v2)

**Purpose**: Prepare LE by updating RegZ-LE form, calculating MI, and matching CTC.

**v2 Additions**:
- ✅ **RegZ-LE Form Updates**: LE Date Issued, Interest Accrual (360/360), Late Charge, Assumption
- ✅ **Cash to Close Matching**: Purchase vs Refinance checkbox logic
- ✅ **MI Calculation**: Conventional only (MVP)

**Workflow**:
1. Update RegZ-LE fields per SOP
2. Calculate Mortgage Insurance (if LTV > 80%)
3. Match Cash to Close (set checkboxes)
4. Populate missing LE fields using AI derivation

**GAPS Implemented**: G3 (Home Counseling), G4 (Transcript Forms - Full API), G5 (2015 Itemization), G6 (SSPL Management), G7 (ABA Template), G18 (RegZ-LE Fields), G19 (Blend ORGID), G20 (eFolder Products)

**Tools**: `update_regz_le_fields`, `calculate_loan_mi`, `match_ctc`, `verify_ctc_match`, `get_le_field_status`, plus 8 GAPS implementation tools

[📁 Full README](./subagents/preparation_agent/README.md)

---

### 3. Send Agent (v2) 🆕

**Purpose**: Run mandatory compliance checks and order eDisclosures.

**v2 Features** (replaces Request Agent):
- ✅ **Mavent Compliance Check**: MANDATORY - all Fail/Alert/Warning must be cleared
- ✅ **ATR/QM Flag Check**: MANDATORY - flags must NOT be RED
- ✅ **eDisclosures Ordering**: 3-step API flow (Audit → Order → Deliver)

**Blocking Conditions**:
- Mavent has any Fail/Alert/Warning → BLOCK
- ATR/QM has any RED flag → BLOCK
- Audit has unresolved issues → BLOCK

**GAPS Implemented**: G16 (Audit Exception Filter), G21 (LO Review Workflow)

**API Flow**:
```
Step 1: POST /encompassdocs/v1/documentAudits/opening
Step 2: POST /encompassdocs/v1/documentOrders/opening
Step 3: POST /encompassdocs/v1/documentOrders/opening/{docSetId}/delivery
```

**Tools**: `check_mavent`, `check_atr_qm`, `audit_loan`, `order_disclosure_package`

[📁 Full README](./subagents/send_agent/README.md)

---

### 4. Request Agent (v1 - Legacy)

**Status**: ⚠️ Deprecated in v2  
**Purpose**: Send email notifications to LOs (v1 functionality)  
**v2 Replacement**: Send Agent now handles disclosure ordering via eDisclosures API

*Note: Request Agent remains available for email notifications if needed, but the primary disclosure delivery mechanism in v2 is the eDisclosures API via the Send Agent.*

[📁 Legacy README](./subagents/request_agent/README.md)

---

## Usage

### Command Line

```bash
# Run full orchestrator (v2)
python agents/disclosure/orchestrator_agent.py \
  --loan-id "your-loan-guid" \
  --lo-email "lo@example.com" \
  --demo

# Run individual sub-agents
python agents/disclosure/subagents/verification_agent/verification_agent.py --loan-id "..."
python agents/disclosure/subagents/preparation_agent/preparation_agent.py --loan-id "..." --demo
python agents/disclosure/subagents/send_agent/send_agent.py --loan-id "..." --dry-run
```

### Python API

```python
from agents.disclosure import run_disclosure_orchestrator

results = run_disclosure_orchestrator(
    loan_id="your-loan-guid",
    lo_email="lo@example.com",  # Optional in v2
    demo_mode=True,
    skip_non_mvp=False  # Set True to skip non-MVP loans
)

# v2 Output includes:
print(results["pre_check"])  # NEW: Milestone & disclosure tracking
print(results["verification"]["output"]["trid_compliance"])  # NEW: TRID results
print(results["preparation"]["output"]["regz_le_result"])  # NEW: RegZ-LE updates
print(results["preparation"]["output"]["ctc_result"])  # NEW: CTC match
print(results["send"]["output"]["mavent_result"])  # NEW: Mavent compliance
print(results["send"]["output"]["atr_qm_result"])  # NEW: ATR/QM flags
print(results["tracking_id"])  # NEW: eDisclosures tracking ID
print(results["blocking_issues"])  # NEW: List of blockers
```

---

## MVP Scope (v2)

### ✅ Included

| Feature | Description |
|---------|-------------|
| **TRID Compliance** | App Date + 3-business-day LE due date |
| **Hard Stops (G1)** | Phone/Email missing blocks disclosure |
| **15-Day Rule (G8)** | Closing date ≥ 15 days from app/lock |
| **Pre-Check** | Milestone status, disclosure tracking |
| **Form Validation** | 1003 URLA, RegZ-LE, FACT Act basics |
| **RegZ-LE Updates** | LE Date, Interest Accrual, Late Charge, Assumption |
| **Conventional MI** | LTV > 80% calculation |
| **Cash to Close** | Purchase vs Refi checkbox logic |
| **Mavent Check** | MANDATORY compliance check |
| **ATR/QM Check** | MANDATORY flag check |
| **eDisclosures** | Order Initial Disclosure via API |
| **Locked/Non-Locked** | Flow differentiation |

### 🔴 Phase 2 (Not Included)

| Feature | Reason |
|---------|--------|
| **FHA/VA/USDA MI** | Complex MIP/FF calculations |
| **Texas State Rules** | Line 810, 12-day letter, A6 form |
| **COC/LE Processing** | Revised LE (Change of Circumstances) |
| **FACT Act Boxes (G2)** | Credit score disclosure checkboxes |
| **Home Counseling (G3)** | Get Agencies automation |
| **SSPL Updates (G6)** | Settlement Service Provider List |
| **Auto-Cure Tolerance** | Automatic lender credit application |

---

## Implemented Gaps from SOP

Based on `GAPS.md`, the following have been implemented in v2:

### ✅ G1: Phone/Email Hard Stop
- **Location**: `packages/shared/form_validator.py`, `verification_agent.py`
- **Implementation**: Missing phone (FE0117) or email (1240) BLOCKS disclosure
- **Tool**: `check_hard_stops()`

### ✅ G8: Closing Date 15-Day Rule
- **Location**: `packages/shared/trid_checker.py`, `verification_agent.py`
- **Implementation**: Closing date (748) ≥ 15 days from app date (not locked) or last rate set date (locked)
- **Tool**: `check_closing_date_rule()`

### ✅ Pre-Check Integration
- **Location**: `packages/shared/milestone_checker.py`, `orchestrator_agent.py`
- **Implementation**: Step 0 runs before verification
- **Functions**: `run_pre_check()`, `get_disclosure_tracking_logs()`, `get_loan_milestones()`

---

## Output Structure (v2)

```json
{
  "loan_id": "...",
  "timestamp": "2025-12-03T10:30:00",
  "demo_mode": true,
  "disclosure_type": "initial_le",
  "is_mvp_supported": true,
  "loan_type": "Conventional",
  "property_state": "NV",
  
  "pre_check": {
    "can_proceed": true,
    "disclosure_tracking": {
      "success": true,
      "le_already_sent": false
    },
    "milestones_api": {
      "success": true,
      "current_milestone": "Processing"
    }
  },
  
  "verification": {
    "status": "success",
    "output": {
      "trid_compliance": {
        "compliant": true,
        "days_remaining": 2
      },
      "hard_stop_check": {
        "has_hard_stops": false
      },
      "closing_date_check": {
        "is_valid": true,
        "days_until_closing": 20
      }
    }
  },
  
  "preparation": {
    "status": "success",
    "output": {
      "regz_le_result": {
        "success": true,
        "updates_made": {"LE1.X1": "2025-12-03", "672": 15, "673": 5.0}
      },
      "mi_result": {
        "requires_mi": false
      },
      "ctc_result": {
        "matched": true,
        "calculated_ctc": 50000.00
      }
    }
  },
  
  "send": {
    "status": "success",
    "output": {
      "mavent_result": {
        "passed": true,
        "total_issues": 0
      },
      "atr_qm_result": {
        "passed": true,
        "red_flags": []
      },
      "order_result": {
        "success": true,
        "tracking_id": "abc-123-def"
      }
    }
  },
  
  "tracking_id": "abc-123-def",
  "blocking_issues": [],
  "summary": "..."
}
```

---

## Configuration

Set environment variables in `.env`:

```env
# Encompass API
ENCOMPASS_API_BASE_URL=https://concept.api.elliemae.com
ENCOMPASS_CLIENT_ID=your_client_id
ENCOMPASS_CLIENT_SECRET=your_secret
ENCOMPASS_INSTANCE_ID=your_instance_id

# Optional: Email notifications (if using Request Agent for notifications)
EMAIL_SERVICE=smtp
EMAIL_FROM=noreply@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_password
```

---

## Testing

```bash
# Run orchestrator test
python agents/disclosure/test_orchestrator.py

# Test individual agents
python agents/disclosure/subagents/verification_agent/test_all_fields.py
```

---

## Error Handling

| Error | Severity | Agent | Action |
|-------|----------|-------|--------|
| LE due date passed | 🔴 Critical | Verification | Escalate to Supervisor |
| Missing phone/email | 🔴 Critical | Verification | HARD STOP - cannot proceed |
| Closing < 15 days | 🔴 Critical | Verification | Adjust closing date |
| Mavent Fail | 🔴 Critical | Send | Clear before sending |
| ATR/QM Red Flag | 🔴 Critical | Send | Fix before sending |
| Texas property | 🟡 Medium | Verification | Log for manual (MVP) |
| Non-Conventional | 🟡 Medium | Verification | Log for manual (MVP) |
| Missing optional field | 🟢 Low | All | Log warning, continue |

---

## Architecture Documents

- **v2 Architecture**: [`discovery/disclosure_architecture_v2.md`](../../discovery/disclosure_architecture_v2.md)
- **Gaps Analysis**: [`GAPS.md`](./GAPS.md)
- **v1 Implementation Summary**: [`IMPLEMENTATION_SUMMARY.md`](./IMPLEMENTATION_SUMMARY.md) *(archived - describes v1)*

---

## Status Summary

### v2 Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Pre-Check | ✅ Complete | Milestone, disclosure tracking, eligibility |
| TRID Compliance | ✅ Complete | 3-day rule, app date, LE due date |
| Hard Stops (G1) | ✅ Complete | Phone/email blocking |
| 15-Day Rule (G8) | ✅ Complete | Closing date validation |
| Form Validation | ✅ MVP | Basic forms, expand in Phase 2 |
| RegZ-LE Updates | ✅ Complete | Late charge, assumption, interest accrual |
| MI Calculation | ✅ Conventional | FHA/VA/USDA in Phase 2 |
| CTC Matching | ✅ Complete | Purchase vs Refi logic |
| Mavent Check | ✅ Complete | Mandatory compliance |
| ATR/QM Check | ✅ Complete | Mandatory flag check |
| eDisclosures | ✅ Complete | 3-step API ordering |
| Request Agent | ⚠️ Deprecated | Replaced by Send Agent in v2 |

---

## Quick Reference

### Entry Points

| Script | Purpose |
|--------|---------|
| `orchestrator_agent.py` | Full v2 workflow |
| `subagents/verification_agent/verification_agent.py` | TRID, forms, hard stops |
| `subagents/preparation_agent/preparation_agent.py` | RegZ-LE, MI, CTC |
| `subagents/send_agent/send_agent.py` | Mavent, ATR/QM, order |
| `subagents/request_agent/request_agent.py` | Legacy email notifications |

### Key Environment Variables

```bash
ENCOMPASS_API_BASE_URL=https://concept.api.elliemae.com
ENCOMPASS_CLIENT_ID=...
ENCOMPASS_CLIENT_SECRET=...
ENCOMPASS_INSTANCE_ID=...
```

### Common Commands

```bash
# Full workflow
python agents/disclosure/orchestrator_agent.py --loan-id <GUID> --lo-email <EMAIL> --demo

# Skip non-MVP loans
python agents/disclosure/orchestrator_agent.py --loan-id <GUID> --lo-email <EMAIL> --demo --skip-non-mvp

# Test with existing loan
python agents/disclosure/test_orchestrator.py
```

---

## GAPS Implementation Status

All 22 gaps from the Disclosure Desk SOP have been implemented:

- **Fully Implemented (8)**: G1, G4, G8, G9, G11, G14, G16, G19
- **Partial/Manual (13)**: G2, G3, G5, G6, G7, G10, G12, G13, G15, G17, G18, G20, G21
- **Out of Scope (1)**: G22 (Texas rules - excluded from MVP)

See [`GAPS_IMPLEMENTATION_PROGRESS.md`](./GAPS_IMPLEMENTATION_PROGRESS.md) for detailed implementation notes.

---

*Document last updated: December 18, 2025*  
*Version: 2.0 (LE-focused with complete GAPS implementation)*
