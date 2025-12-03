# MVP Implementation Roadmap

**Status**: Primitives Complete ✅  
**Next Phase**: Agent Implementation

---

## 1. Current State vs. MVP Architecture

### ✅ Completed: Primitive Tools Layer

All primitive functions implemented in `agents/drawdocs/tools/primitives.py`:

| Category | Functions | Status |
|----------|-----------|--------|
| **Loan Context** | `get_loan_context()`, `get_loan_milestones()`, `get_milestone_by_name()`, `update_milestone_api()`, `add_milestone_log()` | ✅ Complete |
| **Documents** | `list_required_documents()`, `download_documents()`, `extract_entities_from_docs()` | ✅ Complete |
| **Field I/O** | `read_fields()`, `write_fields()` | ✅ Complete |
| **Compliance** | `run_compliance_check()`, `get_compliance_results()` | ⚠️ Stubs (needs Mavent API) |
| **Distribution** | `order_docs()`, `send_closing_package()` | ⚠️ Stubs (needs implementation) |
| **Logging** | `log_issue()` | ✅ Complete |

### 🎯 MVP Architecture Mapping

| MVP Component | Current Implementation | Status |
|---------------|----------------------|--------|
| **Docs Prep Agent** | `subagents/preparation_agent/` | 🟡 Exists, needs integration |
| **Docs Draw Core Agent** | Not implemented | 🔴 **NEW - Priority** |
| **Audit & Compliance Agent** | `subagents/verification_agent/` | 🟡 Exists, needs integration |
| **Order Docs & Distribution** | `subagents/orderdocs_agent/` | 🟡 Minimal, needs completion |

---

## 2. Implementation Plan (4 Phases)

### Phase 1: Integrate Existing Agents with Primitives 🔥 **START HERE**

**Goal**: Update existing agents to use the new primitive tools instead of their own implementations.

#### A. Update Preparation Agent
**Location**: `agents/drawdocs/subagents/preparation_agent/preparation_agent.py`

**Current**: Has its own document downloading and extraction logic  
**Target**: Use primitives from `agents/drawdocs/tools/primitives.py`

**Changes Needed**:
```python
from agents.drawdocs.tools import (
    get_loan_context,
    download_documents,
    extract_entities_from_docs,
    list_required_documents,
    log_issue
)

def run(loan_id: str) -> dict:
    """
    Docs Prep Agent - MVP Implementation
    
    Responsibilities:
    1. Check preconditions (CTC, CD Approved, Docs Ordered queue)
    2. Download required documents
    3. Extract entities and build doc_context
    4. Handle missing/invalid docs
    """
    
    # 1. Get loan context and check preconditions
    context = get_loan_context(loan_id, include_milestones=True)
    
    # Check flags
    if not context['flags']['is_ctc']:
        log_issue(loan_id, "ERROR", "Loan is not Clear to Close")
        return {"status": "failed", "reason": "not_ctc"}
    
    if not context['flags']['cd_approved']:
        log_issue(loan_id, "ERROR", "CD not approved")
        return {"status": "failed", "reason": "cd_not_approved"}
    
    # 2. List and download required documents
    required_docs = list_required_documents(loan_id)
    documents = download_documents(loan_id, required_docs)
    
    if not documents:
        log_issue(loan_id, "ERROR", "Failed to download required documents")
        return {"status": "failed", "reason": "docs_missing"}
    
    # 3. Extract entities and build doc_context
    doc_context = extract_entities_from_docs(documents)
    
    # 4. Return standardized output
    return {
        "status": "success",
        "loan_id": loan_id,
        "loan_context": context,
        "doc_context": doc_context,
        "documents_processed": len(documents)
    }
```

**Output Schema**: Define `doc_context` JSON structure (see Section 4)

---

#### B. Update Verification Agent
**Location**: `agents/drawdocs/subagents/verification_agent/verification_agent.py`

**Current**: Has its own field lookup and verification logic  
**Target**: Use primitives for field reading and compliance checks

**Changes Needed**:
```python
from agents.drawdocs.tools import (
    get_loan_context,
    read_fields,
    run_compliance_check,
    get_compliance_results,
    log_issue
)

def run(loan_id: str, doc_context: dict) -> dict:
    """
    Audit & Compliance Agent - MVP Implementation
    
    Responsibilities:
    1. Cross-check required fields are present
    2. Verify no inconsistencies
    3. Run Mavent compliance
    4. Decide if ready for docs or needs human review
    """
    
    # 1. Read critical fields for verification
    critical_fields = [
        "4000", "4002",  # Borrower names
        "1109", "1172",  # Loan amount, type
        "14", "11",      # Property state, address
        # Add more from CSV...
    ]
    
    current_values = read_fields(loan_id, critical_fields)
    
    # 2. Compare with doc_context
    discrepancies = []
    for field_id in critical_fields:
        encompass_value = current_values.get(field_id)
        doc_value = doc_context.get(field_id)  # Map from doc_context
        
        if encompass_value != doc_value:
            discrepancies.append({
                "field_id": field_id,
                "encompass": encompass_value,
                "document": doc_value
            })
    
    # 3. Run compliance check
    compliance_result = run_compliance_check(loan_id, "Mavent")
    compliance_details = get_compliance_results(loan_id)
    
    # 4. Decide outcome
    if discrepancies:
        log_issue(loan_id, "WARNING", f"Found {len(discrepancies)} discrepancies")
    
    if not compliance_result:
        log_issue(loan_id, "ERROR", "Compliance check failed")
        return {"status": "failed", "reason": "compliance_failed"}
    
    return {
        "status": "success" if not discrepancies else "needs_review",
        "discrepancies": discrepancies,
        "compliance": compliance_details
    }
```

---

#### C. Complete Order Docs Agent
**Location**: `agents/drawdocs/subagents/orderdocs_agent/orderdocs_agent.py`

**Current**: Minimal implementation  
**Target**: Full deterministic flow for ordering and distribution

**Changes Needed**:
```python
from agents.drawdocs.tools import (
    order_docs,
    update_milestone_api,
    send_closing_package,
    log_issue
)
from datetime import datetime

def run(loan_id: str, recipients: dict) -> dict:
    """
    Order Docs & Distribution - Deterministic Flow
    
    Responsibilities:
    1. Trigger docs draw
    2. Update milestones
    3. Send closing package
    4. Confirm success
    """
    
    try:
        # 1. Order docs
        order_result = order_docs(loan_id)
        if not order_result:
            log_issue(loan_id, "ERROR", "Failed to order docs")
            return {"status": "failed", "reason": "order_failed"}
        
        # 2. Update milestone
        today = datetime.now().strftime("%m/%d/%Y")
        milestone_updated = update_milestone_api(
            loan_id=loan_id,
            milestone_name="Doc Preparation",  # Or "Docs Signing"
            status="Finished",
            comment=f"DOCS Out on {today}"
        )
        
        if not milestone_updated:
            log_issue(loan_id, "WARNING", "Failed to update milestone")
        
        # 3. Send closing package
        send_result = send_closing_package(
            loan_id=loan_id,
            recipients=recipients
        )
        
        if not send_result:
            log_issue(loan_id, "WARNING", "Failed to send closing package")
        
        return {
            "status": "success",
            "docs_ordered": order_result,
            "milestone_updated": milestone_updated,
            "package_sent": send_result,
            "timestamp": today
        }
        
    except Exception as e:
        log_issue(loan_id, "ERROR", f"Order docs failed: {str(e)}")
        return {"status": "failed", "error": str(e)}
```

---

### Phase 2: Implement Docs Draw Core Agent 🔥 **CRITICAL**

**Location**: Create `agents/drawdocs/subagents/drawcore_agent/`

This is the **NEW** main workhorse agent that doesn't exist yet.

#### Structure:
```
drawcore_agent/
├── __init__.py
├── drawcore_agent.py          # Main agent
├── phases/
│   ├── __init__.py
│   ├── phase1_borrower_lo.py
│   ├── phase2_contacts_vendors.py
│   ├── phase3_property_program.py
│   ├── phase4_financial_setup.py
│   └── phase5_closing_disclosure.py
├── example_input.json
├── example_output.json
└── README.md
```

#### Core Implementation:
```python
# agents/drawdocs/subagents/drawcore_agent/drawcore_agent.py

from agents.drawdocs.tools import (
    get_loan_context,
    read_fields,
    write_fields,
    log_issue
)
from .phases import (
    run_phase1_borrower_lo,
    run_phase2_contacts_vendors,
    run_phase3_property_program,
    run_phase4_financial_setup,
    run_phase5_closing_disclosure
)

def run(loan_id: str, doc_context: dict) -> dict:
    """
    Docs Draw Core Agent - Main Workhorse
    
    Executes 5 phases to align Encompass with documents:
    1. Borrower & LO
    2. Contacts & Vendors
    3. Property & Program
    4. Financial Setup
    5. Closing Disclosure
    """
    
    results = {
        "loan_id": loan_id,
        "phases": {},
        "total_updates": 0,
        "total_issues": 0
    }
    
    phases = [
        ("borrower_lo", run_phase1_borrower_lo),
        ("contacts_vendors", run_phase2_contacts_vendors),
        ("property_program", run_phase3_property_program),
        ("financial_setup", run_phase4_financial_setup),
        ("closing_disclosure", run_phase5_closing_disclosure)
    ]
    
    for phase_name, phase_func in phases:
        print(f"\n🔄 Running Phase: {phase_name}")
        
        try:
            phase_result = phase_func(loan_id, doc_context)
            results["phases"][phase_name] = phase_result
            results["total_updates"] += phase_result.get("updates_made", 0)
            results["total_issues"] += len(phase_result.get("issues", []))
            
        except Exception as e:
            log_issue(loan_id, "ERROR", f"Phase {phase_name} failed: {str(e)}")
            results["phases"][phase_name] = {"status": "failed", "error": str(e)}
    
    results["status"] = "success" if results["total_issues"] == 0 else "needs_review"
    return results
```

#### Example Phase Implementation:
```python
# agents/drawdocs/subagents/drawcore_agent/phases/phase1_borrower_lo.py

from agents.drawdocs.tools import read_fields, write_fields, log_issue

def run_phase1_borrower_lo(loan_id: str, doc_context: dict) -> dict:
    """
    Phase 1: Borrower & Loan Officer Setup
    
    Fields to update (from CSV):
    - 4000: Borrower First Name
    - 4001: Borrower Middle Name
    - 4002: Borrower Last Name
    - 65: Borrower SSN
    - 1402: Borrower DOB
    - 52: Borrower Marital Status
    - ... (add more from DrawingDoc Verifications CSV)
    """
    
    # Define field mappings (from CSV)
    field_mappings = {
        "4000": "borrower_first_name",
        "4002": "borrower_last_name",
        "65": "borrower_ssn",
        "1402": "borrower_dob",
        # ... map CSV field IDs to doc_context keys
    }
    
    field_ids = list(field_mappings.keys())
    
    # 1. Read current Encompass values
    current_values = read_fields(loan_id, field_ids)
    
    # 2. Compare with doc_context
    updates = []
    issues = []
    
    for field_id, doc_key in field_mappings.items():
        encompass_value = current_values.get(field_id, "")
        doc_value = doc_context.get(doc_key, "")
        
        if encompass_value != doc_value and doc_value:
            updates.append({
                "field_id": field_id,
                "old_value": encompass_value,
                "new_value": doc_value
            })
        elif not doc_value and not encompass_value:
            issues.append({
                "field_id": field_id,
                "severity": "WARNING",
                "message": f"Missing value in both Encompass and documents"
            })
    
    # 3. Write updates
    if updates:
        write_result = write_fields(loan_id, updates)
        if not write_result:
            log_issue(loan_id, "ERROR", f"Failed to write {len(updates)} fields in Phase 1")
    
    # 4. Log issues
    for issue in issues:
        log_issue(loan_id, issue["severity"], issue["message"])
    
    return {
        "status": "success",
        "updates_made": len(updates),
        "issues": issues,
        "fields_checked": len(field_ids)
    }
```

---

### Phase 3: Create Orchestrator

**Location**: `agents/drawdocs/orchestrator_agent.py`

```python
from agents.drawdocs.subagents.preparation_agent import preparation_agent
from agents.drawdocs.subagents.drawcore_agent import drawcore_agent
from agents.drawdocs.subagents.verification_agent import verification_agent
from agents.drawdocs.subagents.orderdocs_agent import orderdocs_agent
from agents.drawdocs.tools import log_issue

def run_docs_draw(loan_id: str, recipients: dict = None) -> dict:
    """
    Main Orchestrator for Docs Draw MVP
    
    Executes 4-step pipeline:
    1. Docs Prep Agent
    2. Docs Draw Core Agent
    3. Audit & Compliance Agent
    4. Order Docs & Distribution
    """
    
    print(f"\n{'='*80}")
    print(f"Starting Docs Draw for Loan: {loan_id}")
    print(f"{'='*80}\n")
    
    # Step 1: Docs Prep
    print("Step 1: Docs Prep Agent")
    prep_result = preparation_agent.run(loan_id)
    
    if prep_result["status"] != "success":
        return {
            "status": "failed",
            "step": "preparation",
            "reason": prep_result.get("reason"),
            "details": prep_result
        }
    
    doc_context = prep_result["doc_context"]
    
    # Step 2: Docs Draw Core
    print("\nStep 2: Docs Draw Core Agent")
    drawcore_result = drawcore_agent.run(loan_id, doc_context)
    
    if drawcore_result["status"] == "failed":
        return {
            "status": "failed",
            "step": "draw_core",
            "details": drawcore_result
        }
    
    # Step 3: Audit & Compliance
    print("\nStep 3: Audit & Compliance Agent")
    verification_result = verification_agent.run(loan_id, doc_context)
    
    if verification_result["status"] == "failed":
        return {
            "status": "failed",
            "step": "verification",
            "details": verification_result
        }
    
    if verification_result["status"] == "needs_review":
        log_issue(loan_id, "WARNING", "Verification found issues - needs human review")
        return {
            "status": "needs_review",
            "step": "verification",
            "discrepancies": verification_result.get("discrepancies"),
            "details": verification_result
        }
    
    # Step 4: Order Docs & Distribution
    print("\nStep 4: Order Docs & Distribution")
    orderdocs_result = orderdocs_agent.run(loan_id, recipients or {})
    
    if orderdocs_result["status"] != "success":
        return {
            "status": "failed",
            "step": "order_docs",
            "details": orderdocs_result
        }
    
    # Success!
    print(f"\n{'='*80}")
    print("✅ Docs Draw Completed Successfully")
    print(f"{'='*80}\n")
    
    return {
        "status": "success",
        "loan_id": loan_id,
        "preparation": prep_result,
        "draw_core": drawcore_result,
        "verification": verification_result,
        "order_docs": orderdocs_result
    }
```

---

### Phase 4: Complete Remaining Primitives

**Priority Order**:

1. **`run_compliance_check()`** - Integrate Mavent API
2. **`get_compliance_results()`** - Parse Mavent results
3. **`order_docs()`** - Integrate Encompass docs ordering API
4. **`send_closing_package()`** - Integrate email service (SendGrid/AWS SES)
5. **`list_required_documents()`** - Refine with lender-specific logic

---

## 3. Testing Strategy

Create test script: `agents/drawdocs/test_mvp.py`

```python
from agents.drawdocs.orchestrator_agent import run_docs_draw

# Test with real loan
loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"

result = run_docs_draw(
    loan_id=loan_id,
    recipients={
        "title_company": "title@example.com",
        "loan_officer": "lo@example.com",
        "processor": "processor@example.com"
    }
)

print(json.dumps(result, indent=2))
```

---

## 4. Doc Context Schema

Define standardized `doc_context` JSON structure:

```json
{
  "borrowers": [
    {
      "first_name": "John",
      "middle_name": "A",
      "last_name": "Doe",
      "ssn": "123-45-6789",
      "dob": "1980-01-15",
      "marital_status": "Married",
      "email": "john@example.com",
      "phone": "555-1234"
    }
  ],
  "property": {
    "address": "123 Main St",
    "city": "Los Angeles",
    "state": "CA",
    "zip": "90001",
    "type": "Single Family",
    "occupancy": "Primary Residence"
  },
  "loan": {
    "amount": 400000,
    "type": "Conventional",
    "program": "Fixed 30",
    "purpose": "Purchase",
    "rate": 3.5,
    "term": 360,
    "ltv": 80.0
  },
  "program_specifics": {
    "fha_case_number": null,
    "va_case_number": null,
    "mi_certificate_number": null
  },
  "fees": {
    "origination": 1000,
    "appraisal": 500,
    "credit_report": 50
  },
  "documents_used": [
    "Final 1003",
    "Approval Final",
    "Borrower ID"
  ]
}
```

---

## 5. Next Immediate Actions

### Week 1: Phase 1 - Integration
1. ✅ Update `preparation_agent.py` to use primitives
2. ✅ Update `verification_agent.py` to use primitives  
3. ✅ Complete `orderdocs_agent.py` implementation
4. ✅ Define `doc_context` schema
5. ✅ Test each agent individually

### Week 2: Phase 2 - Core Agent
1. ✅ Create `drawcore_agent/` structure
2. ✅ Implement Phase 1 (Borrower & LO)
3. ✅ Implement Phase 2 (Contacts & Vendors)
4. ✅ Implement Phase 3 (Property & Program)
5. ✅ Test Phase 1-3

### Week 3: Phase 2 Continued
1. ✅ Implement Phase 4 (Financial Setup)
2. ✅ Implement Phase 5 (Closing Disclosure)
3. ✅ Test all phases together
4. ✅ Refine field mappings from CSV

### Week 4: Phase 3 & 4 - Orchestrator & Polish
1. ✅ Create `orchestrator_agent.py`
2. ✅ End-to-end testing with real loans
3. ✅ Complete remaining primitives (Mavent, email)
4. ✅ Documentation and deployment prep

---

## 6. Success Metrics

| Metric | Target |
|--------|--------|
| % of loans passing Prep Agent | >95% |
| % of fields correctly updated by Core Agent | >90% |
| % passing Audit & Compliance | >85% |
| Docs successfully ordered | >95% |
| Time from start to docs out | <5 minutes |
| Human intervention required | <15% |

---

## 7. Questions to Answer

Before starting implementation:

1. ✅ **Doc Context Schema**: Is the proposed JSON structure comprehensive?
2. ⚠️  **Mavent Integration**: Do you have Mavent API credentials?
3. ⚠️  **Email Service**: SendGrid, AWS SES, or other for closing packages?
4. ⚠️  **Encompass Docs API**: Endpoint for triggering docs draw?
5. ✅ **Field Mappings**: Use DrawingDoc Verifications CSV as source of truth?

---

## Summary

**You're here** ⭐: Primitives Complete

**Next step**: Phase 1 - Update existing agents to use primitives (Week 1)

**Big milestone**: Implement Docs Draw Core Agent (Week 2-3)

**End goal**: Full orchestrated pipeline working end-to-end (Week 4)

