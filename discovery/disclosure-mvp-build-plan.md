# Disclosure Agent MVP Revision + Shared Components Build Plan

## Current State Analysis

The disclosure agent currently has:

- **Verification Agent**: Checks field existence using CSV field list - works but checks too many fields
- **Preparation Agent**: AI-based field derivation (finds related fields) - missing MI calculation and CD population
- **Request Agent**: Sends email to LO - functional
- **Shared utilities**: `packages/shared/` exists but is empty

### Gap vs MVP Requirements

| MVP Requirement | Current State | Action |

|----------------|---------------|--------|

| Field existence (~20 fields) | Checks all CSV fields | Streamline to critical fields only |

| Conventional MI calculation | Missing | Add to Preparation Agent |

| Basic CD population | Missing | Add to Preparation Agent |

| Fee tolerance flagging | Missing | Add new tool |

| Send email to LO | Exists | Minor refinement |

---

## Phase 1: Shared Components (Day 1-2)

### 1.1 Create `shared/encompass_io.py`

Location: [agents/drawdocs/packages/shared/encompass_io.py](agents/drawdocs/packages/shared/encompass_io.py)

```python
# Interface for both agents to use
def read_fields(loan_id: str, field_ids: List[str]) -> Dict[str, Any]
def write_fields(loan_id: str, updates: Dict[str, Any]) -> bool
def get_loan_type(loan_id: str) -> str  # Returns "Conventional", "FHA", etc.
def get_loan_purpose(loan_id: str) -> str  # Returns "Purchase", "Refinance"
```

Refactor existing code from:

- [agents/disclosure/subagents/preparation_agent/tools/field_derivation_tools.py](agents/disclosure/subagents/preparation_agent/tools/field_derivation_tools.py) - `get_loan_field_value()`, `write_field_value()`
- [agents/disclosure/subagents/verification_agent/tools/field_check_tools.py](agents/disclosure/subagents/verification_agent/tools/field_check_tools.py) - `get_field_value()`

### 1.2 Create `shared/constants.py`

Location: [agents/drawdocs/packages/shared/constants.py](agents/drawdocs/packages/shared/constants.py)

Define MVP critical fields (~20):

```python
DISCLOSURE_CRITICAL_FIELDS = {
    "borrower": ["4000", "4002", "65"],  # Name, SSN, DOB
    "property": ["11", "12", "14"],  # Address, City, State
    "loan": ["1109", "3", "4"],  # Amount, Rate, Term
    "contacts": ["settlement_agent", "title_company"]
}
```

---

## Phase 2: MI Calculator (Day 3-4)

### 2.1 Create `shared/mi_calculator.py`

Location: [agents/drawdocs/packages/shared/mi_calculator.py](agents/drawdocs/packages/shared/mi_calculator.py)

MVP scope: Conventional MI only

```python
def calculate_conventional_mi(
    loan_amount: float,
    appraised_value: float,
    ltv: float,
    mi_cert_data: Optional[Dict] = None
) -> Optional[MIResult]:
    """
    Calculate Conventional PMI for LTV > 80%
    Returns None if LTV <= 80%
    
    MVP: Use MI Cert rates if available, else standard estimate
    """
```

Key logic from [discovery/disclosure_architecture.md](discovery/disclosure_architecture.md):

- Only calculate if LTV > 80%
- Use MI Certificate rates if available
- Cancel at 78% LTV (except 2+ units)
- First renewal: usually 120 months
- Second renewal: usually 0.20%

### 2.2 Add MI Tool to Preparation Agent

Update [agents/disclosure/subagents/preparation_agent/tools/](agents/disclosure/subagents/preparation_agent/tools/) - add `mi_tools.py`:

```python
def calculate_mi(loan_id: str) -> Dict[str, Any]:
    """Tool for agent to calculate MI and populate CD fields"""
    # Read LTV, loan amount from Encompass
    # Call shared MI calculator
    # Return result for CD population
```

---

## Phase 3: Fee Tolerance (Day 5)

### 3.1 Create `shared/fee_tolerance.py`

Location: [agents/drawdocs/packages/shared/fee_tolerance.py](agents/drawdocs/packages/shared/fee_tolerance.py)

MVP scope: Flag only (no auto-cure)

```python
def check_fee_tolerance(
    loan_id: str,
    le_fees: Dict[str, float],
    cd_fees: Dict[str, float]
) -> ToleranceResult:
    """
    Compare LE vs CD fees
    Returns list of violations (0% and 10% tolerance)
    MVP: Flag only, do not apply cures
    """
```

Key tolerance rules:

- 0% tolerance: Section A fees (origination, discount points)
- 10% tolerance: Section B fees (when using SPL provider)
- No tolerance: Section C fees (borrower-shopped)

---

## Phase 4: Revise Disclosure Agents (Day 3-5 parallel)

### 4.1 Streamline Verification Agent

Update [agents/disclosure/subagents/verification_agent/verification_agent.py](agents/disclosure/subagents/verification_agent/verification_agent.py):

Changes:

1. Import critical fields from `shared/constants.py` instead of CSV
2. Reduce from all fields to ~20 critical fields
3. Add loan-type awareness (skip MI fields for LTV <= 80%)
4. Faster execution (fewer API calls)

### 4.2 Enhance Preparation Agent

Update [agents/disclosure/subagents/preparation_agent/preparation_agent.py](agents/disclosure/subagents/preparation_agent/preparation_agent.py):

Changes:

1. Add MI calculation step (new `mi_tools.py`)
2. Add basic CD field population (pages 1-3)
3. Add fee tolerance flagging (new `tolerance_tools.py`)
4. Use shared `encompass_io.py` for field IO

New agent instruction flow:

```
1. Calculate MI (if Conventional > 80% LTV)
2. Populate basic CD fields
3. Check fee tolerance (flag violations)
4. Clean/normalize existing fields (existing functionality)
```

### 4.3 Minor Request Agent Updates

Update [agents/disclosure/subagents/request_agent/request_agent.py](agents/disclosure/subagents/request_agent/request_agent.py):

Changes:

1. Include MI calculation result in email
2. Include fee tolerance flags in email
3. Add handoff data structure for Draw Docs

---

## Phase 5: Integration + Testing (Week 2)

### 5.1 Update Orchestrator

Update [agents/disclosure/orchestrator_agent.py](agents/disclosure/orchestrator_agent.py):

Changes:

1. Pass MI result from Preparation to Request
2. Pass tolerance flags from Preparation to Request
3. Add non-MVP case handling (log and hand off)
```python
# Non-MVP handling
if loan_type != "Conventional":
    return {"status": "manual_required", "reason": "Non-Conventional loan type"}
```


### 5.2 Create Handoff Schema

Add to [agents/drawdocs/packages/shared/handoff.py](agents/drawdocs/packages/shared/handoff.py):

```python
@dataclass
class DisclosureHandoff:
    cd_status: str
    cd_ack_date: Optional[date]
    waiting_period_ends: Optional[date]
    tolerance_issues: List[str]
    mi_calculated: Optional[Dict]
```

### 5.3 Update Tests

Update [agents/disclosure/test_orchestrator.py](agents/disclosure/test_orchestrator.py):

- Add MI calculation test
- Add fee tolerance test
- Add non-MVP case test

---

## File Changes Summary

### New Files (6)

1. `agents/drawdocs/packages/shared/encompass_io.py`
2. `agents/drawdocs/packages/shared/mi_calculator.py`
3. `agents/drawdocs/packages/shared/fee_tolerance.py`
4. `agents/drawdocs/packages/shared/constants.py`
5. `agents/drawdocs/packages/shared/handoff.py`
6. `agents/disclosure/subagents/preparation_agent/tools/mi_tools.py`

### Modified Files (5)

1. `agents/disclosure/subagents/verification_agent/verification_agent.py` - use critical fields only
2. `agents/disclosure/subagents/preparation_agent/preparation_agent.py` - add MI + CD + tolerance
3. `agents/disclosure/subagents/request_agent/request_agent.py` - include MI and tolerance in email
4. `agents/disclosure/orchestrator_agent.py` - add non-MVP handling
5. `agents/disclosure/test_orchestrator.py` - add new tests

---

## Timeline Alignment

| Day | Task | Files |

|-----|------|-------|

| 1-2 | shared/encompass_io.py + constants.py | 2 new files |

| 3-4 | shared/mi_calculator.py + mi_tools.py | 2 new files |

| 5 | shared/fee_tolerance.py | 1 new file |

| 5 | Update verification agent | 1 modified |

| 3-5 | Update preparation agent | 1 modified |

| 6-7 | Update orchestrator + request agent | 2 modified |

| 8-10 | Integration testing + bug fixes | tests |