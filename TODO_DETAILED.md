# Docs Draw MVP - Detailed TODO List

**Status**: Primitives Complete ✅ | Ready to Build Agents 🚀

---

## ✅ PHASE 0: Foundation (COMPLETE)

### 1. ✅ Primitive Tools Layer
- [x] Loan context & milestones functions
- [x] Document download & extraction
- [x] Encompass field I/O (read/write)
- [x] Issue logging
- [x] MCP server integration
- [x] CSV-driven field mappings
- [x] Tested with real loan data

### 2. ✅ Environment Setup
- [x] Both .env files loading correctly
- [x] MCP server credentials working
- [x] LandingAI API key present
- [x] OAuth authentication successful

**Result**: All primitives tested and working with loan `b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6`

---

## 🔥 PHASE 1: Update Existing Agents (Week 1)

**Goal**: Make existing agents use the new primitive tools instead of their own implementations

### Task 1: Update Preparation Agent ⏱️ 2-3 hours

**File**: `agents/drawdocs/subagents/preparation_agent/preparation_agent.py`

**Changes Needed**:
```python
# Replace custom implementations with:
from agents.drawdocs.tools import (
    get_loan_context,      # ← Use this instead of custom context logic
    download_documents,     # ← Use this instead of custom download
    extract_entities_from_docs,  # ← Use this for OCR/extraction
    list_required_documents,     # ← Use this for doc requirements
    log_issue                    # ← Use this for error logging
)
```

**Steps**:
1. Read current `preparation_agent.py` implementation
2. Identify what needs to be replaced
3. Update imports
4. Replace custom functions with primitives
5. Test with real loan ID
6. Verify output matches expected `doc_context` format

**Success Criteria**:
- Agent runs without errors
- Returns standardized `doc_context` JSON
- All required documents downloaded and processed

---

### Task 2: Update Verification Agent ⏱️ 2-3 hours

**File**: `agents/drawdocs/subagents/verification_agent/verification_agent.py`

**Changes Needed**:
```python
# Replace custom implementations with:
from agents.drawdocs.tools import (
    get_loan_context,       # ← Use this for loan data
    read_fields,           # ← Use this instead of custom field reading
    run_compliance_check,  # ← Use this for Mavent (stub for now)
    get_compliance_results,# ← Use this for compliance results
    log_issue             # ← Use this for logging
)
```

**Steps**:
1. Read current `verification_agent.py` implementation
2. Update to use `read_fields()` for Encompass data
3. Add logic to compare Encompass vs. doc_context
4. Identify discrepancies
5. Test with real loan

**Success Criteria**:
- Agent compares fields correctly
- Reports discrepancies as JSON
- Decides "success", "needs_review", or "failed"

---

### Task 3: Complete Order Docs Agent ⏱️ 1-2 hours

**File**: `agents/drawdocs/subagents/orderdocs_agent/orderdocs_agent.py`

**Current State**: Minimal implementation
**Target State**: Full deterministic flow

**Changes Needed**:
```python
from agents.drawdocs.tools import (
    order_docs,              # ← Stub - needs Encompass API
    update_milestone_api,    # ← Working!
    send_closing_package,    # ← Stub - needs email service
    log_issue
)
```

**Steps**:
1. Implement order_docs() call (stub for now)
2. Update "Doc Preparation" or "Docs Signing" milestone
3. Send closing package to recipients (stub for now)
4. Return success/failure status
5. Test milestone update

**Success Criteria**:
- Milestone updates successfully
- Returns detailed status
- Handles errors gracefully

---

### Task 4: Define doc_context Schema ⏱️ 30 min

**File**: Create `agents/drawdocs/schemas/doc_context_schema.json`

**Content**: Standardized JSON structure for document extraction results

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "borrowers": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "first_name": {"type": "string"},
          "middle_name": {"type": "string"},
          "last_name": {"type": "string"},
          "ssn": {"type": "string"},
          "dob": {"type": "string", "format": "date"}
        }
      }
    },
    "property": {
      "type": "object",
      "properties": {
        "address": {"type": "string"},
        "city": {"type": "string"},
        "state": {"type": "string"},
        "zip": {"type": "string"}
      }
    },
    "loan": {
      "type": "object",
      "properties": {
        "amount": {"type": "number"},
        "type": {"type": "string"},
        "program": {"type": "string"}
      }
    }
  }
}
```

**Success Criteria**:
- Schema validated with JSON Schema validator
- Documentation created
- Example instances provided

---

## 🎯 PHASE 2: Build Docs Draw Core Agent (Week 2-3)

**Goal**: Create the NEW main workhorse agent that aligns Encompass fields with documents

### Task 5: Create Directory Structure ⏱️ 15 min

**Create**:
```
agents/drawdocs/subagents/drawcore_agent/
├── __init__.py
├── drawcore_agent.py          # Main agent entry point
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

---

### Task 6: Implement Phase 1 - Borrower & LO ⏱️ 4-6 hours

**File**: `phases/phase1_borrower_lo.py`

**Responsibility**: Update borrower and loan officer information

**Fields to Update** (from DrawingDoc Verifications CSV):
- 4000: Borrower First Name
- 4001: Borrower Middle Name
- 4002: Borrower Last Name
- 65: Borrower SSN
- 1402: Borrower DOB
- 52: Borrower Marital Status
- 66: Borrower Home Phone
- 1240: Borrower Email
- 4004, 4005, 4006: Co-Borrower names
- 97: Co-Borrower SSN
- ... (20-30 fields total)

**Implementation**:
1. Define field mappings from CSV
2. Read current Encompass values
3. Compare with doc_context
4. Generate list of updates
5. Write updates to Encompass
6. Log any issues
7. Return summary

**Success Criteria**:
- All borrower fields correctly updated
- No data loss
- Issues logged for missing data

---

### Task 7: Implement Phase 2 - Contacts & Vendors ⏱️ 3-4 hours

**File**: `phases/phase2_contacts_vendors.py`

**Fields**:
- Title Company (Name, Contact, Email, Phone)
- Escrow Company
- Hazard Insurance
- Settlement Agent
- Real Estate Broker
- ... (15-20 fields)

---

### Task 8: Implement Phase 3 - Property & Program ⏱️ 3-4 hours

**File**: `phases/phase3_property_program.py`

**Fields**:
- Subject Property (Address, City, State, Zip)
- Property Type
- Occupancy Type
- Loan Type
- Loan Program
- Loan Purpose
- ... (25-30 fields)

---

### Task 9: Implement Phase 4 - Financial Setup ⏱️ 4-6 hours

**File**: `phases/phase4_financial_setup.py`

**Fields**:
- Loan Amount
- Interest Rate
- Loan Term
- LTV
- Fees (Origination, Appraisal, etc.)
- Escrow/Impound details
- MI details
- ... (30-40 fields)

---

### Task 10: Implement Phase 5 - Closing Disclosure ⏱️ 4-6 hours

**File**: `phases/phase5_closing_disclosure.py`

**Fields**:
- Closing Date
- First Payment Date
- Closing Costs
- Cash to Close
- APR
- Lender Credits
- ... (20-30 fields)

---

### Task 11: Main Drawcore Agent ⏱️ 2-3 hours

**File**: `drawcore_agent.py`

**Implementation**:
```python
def run(loan_id: str, doc_context: dict) -> dict:
    """
    Execute 5 phases to align Encompass with documents
    """
    results = {"phases": {}, "total_updates": 0}
    
    for phase_name, phase_func in phases:
        phase_result = phase_func(loan_id, doc_context)
        results["phases"][phase_name] = phase_result
        results["total_updates"] += phase_result["updates_made"]
    
    return results
```

**Success Criteria**:
- All 5 phases execute successfully
- Returns detailed summary
- Handles errors gracefully
- Logs all updates

---

## 🎼 PHASE 3: Create Orchestrator (Week 4)

### Task 12: Build Main Orchestrator ⏱️ 3-4 hours

**File**: `agents/drawdocs/orchestrator_agent.py`

**Implementation**:
```python
def run_docs_draw(loan_id: str, recipients: dict = None) -> dict:
    """
    Main 4-step pipeline:
    1. Docs Prep Agent
    2. Docs Draw Core Agent
    3. Audit & Compliance Agent
    4. Order Docs & Distribution
    """
    
    # Step 1: Prep
    prep_result = preparation_agent.run(loan_id)
    if prep_result["status"] != "success":
        return {"status": "failed", "step": "preparation"}
    
    # Step 2: Core
    drawcore_result = drawcore_agent.run(loan_id, prep_result["doc_context"])
    
    # Step 3: Verification
    verification_result = verification_agent.run(loan_id, prep_result["doc_context"])
    
    # Step 4: Order Docs
    orderdocs_result = orderdocs_agent.run(loan_id, recipients)
    
    return {
        "status": "success",
        "preparation": prep_result,
        "draw_core": drawcore_result,
        "verification": verification_result,
        "order_docs": orderdocs_result
    }
```

**Success Criteria**:
- All 4 agents execute in sequence
- Errors handled at each step
- Detailed results returned
- Works end-to-end with real loan

---

## 🔧 PHASE 4: Complete Remaining Primitives (Parallel)

### Task 13: Mavent Compliance Integration ⏱️ 4-6 hours

**Files**: 
- `agents/drawdocs/tools/primitives.py` (update stubs)
- Need Mavent API credentials

**Implementation**:
```python
def run_compliance_check(loan_id: str, vendor: str = "Mavent") -> bool:
    """Submit loan for compliance check"""
    # Integrate Mavent API
    pass

def get_compliance_results(loan_id: str) -> dict:
    """Get compliance check results"""
    # Parse Mavent results
    pass
```

---

### Task 14: Order Docs API Integration ⏱️ 2-3 hours

**Files**: 
- `agents/drawdocs/tools/primitives.py` (update stub)
- Need Encompass docs ordering endpoint

**Implementation**:
```python
def order_docs(loan_id: str) -> bool:
    """Trigger docs generation in Encompass"""
    # Call Encompass docs API
    pass
```

---

### Task 15: Email Service Integration ⏱️ 2-3 hours

**Files**: 
- `agents/drawdocs/tools/primitives.py` (update stub)
- Need SendGrid/AWS SES credentials

**Implementation**:
```python
def send_closing_package(loan_id: str, recipients: dict) -> bool:
    """Email closing package to recipients"""
    # Integrate email service
    pass
```

---

### Task 16: List Required Documents Refinement ⏱️ 1-2 hours

**Files**: 
- `agents/drawdocs/tools/primitives.py` (enhance logic)

**Enhancements**:
- Add lender-specific requirements
- Add state-specific documents
- Add loan-type-specific requirements

---

## 🧪 PHASE 5: Testing & Deployment (Week 4)

### Task 17: End-to-End Testing ⏱️ 4-6 hours

**Create**: `agents/drawdocs/test_mvp.py`

**Tests**:
1. Test with successful loan (all docs present)
2. Test with missing documents
3. Test with field discrepancies
4. Test with compliance failures
5. Test error handling
6. Performance testing (time to complete)

**Success Criteria**:
- >95% of test loans pass Prep Agent
- >90% of fields correctly updated by Core Agent
- >85% pass Audit & Compliance
- Complete process in <5 minutes
- <15% require human intervention

---

## 📊 Summary Statistics

### Tasks by Phase:
- ✅ Phase 0 (Foundation): 2/2 complete
- 🔥 Phase 1 (Existing Agents): 0/4 complete
- 🎯 Phase 2 (Core Agent): 0/7 complete
- 🎼 Phase 3 (Orchestrator): 0/1 complete
- 🔧 Phase 4 (APIs): 0/4 complete
- 🧪 Phase 5 (Testing): 0/1 complete

### Total: 2/19 tasks complete (11%)

### Estimated Time:
- Phase 1: 6-8 hours (Week 1)
- Phase 2: 20-30 hours (Week 2-3)
- Phase 3: 3-4 hours (Week 4)
- Phase 4: 9-14 hours (Parallel to 1-3)
- Phase 5: 4-6 hours (Week 4)

**Total**: ~42-62 hours (4-6 weeks part-time)

---

## 🎯 Recommended Order

### This Week (Week 1):
1. ✅ Define doc_context schema (30 min)
2. 🔥 Update Preparation Agent (3 hours)
3. 🔥 Test Preparation Agent with real loan (1 hour)
4. 🔥 Update Verification Agent (3 hours)

### Next Week (Week 2):
5. 🎯 Create Drawcore structure (15 min)
6. 🎯 Implement Phase 1 (6 hours)
7. 🎯 Implement Phase 2 (4 hours)
8. 🎯 Implement Phase 3 (4 hours)

### Week 3:
9. 🎯 Implement Phase 4 (6 hours)
10. 🎯 Implement Phase 5 (6 hours)
11. 🎯 Test all phases (2 hours)

### Week 4:
12. 🎼 Create Orchestrator (4 hours)
13. 🧪 End-to-end testing (6 hours)
14. 🔧 Complete remaining APIs as needed

---

## 🚀 Quick Start

**To begin RIGHT NOW**:

```bash
# Option 1: Start with easiest task (Prep Agent)
cd /Users/antonboquer/Documents/Fintor/drawdoc-awm-agent
code agents/drawdocs/subagents/preparation_agent/preparation_agent.py

# Option 2: Start with most valuable task (Drawcore Agent)
mkdir -p agents/drawdocs/subagents/drawcore_agent/phases
code agents/drawdocs/subagents/drawcore_agent/drawcore_agent.py

# Option 3: See what you have first
python -m agents.drawdocs.subagents.preparation_agent.preparation_agent
```

---

## ❓ Decision Points

**Need to decide**:
1. Which Mavent API? (need credentials)
2. Which email service? (SendGrid, AWS SES, Mailgun?)
3. Encompass docs ordering endpoint? (need API documentation)
4. How to handle partial failures? (continue or stop?)
5. Where to store logs? (database, S3, local files?)

---

## 📚 Reference Documents

- `MVP_IMPLEMENTATION_ROADMAP.md` - Detailed implementation plan
- `PRIMITIVES_COMPLETE_SUMMARY.md` - What primitives are available
- `docs_draw_agentic_architecture.md` - Original architecture
- `packages/data/DrawingDoc Verifications - Sheet1.csv` - Field mappings source

---

**Ready to start? Pick any task and let's build!** 🚀

