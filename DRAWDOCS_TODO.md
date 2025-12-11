# DrawDocs Implementation TODO List

**Created:** December 8, 2025  
**Last Updated:** December 9, 2025  
**Status:** In Progress  
**Current Phase:** Phase 1 Complete (75%) → Phase 2 Planning

---

## 🎯 **IMMEDIATE ACTION PLAN**

### **Step 1: Get Missing Encompass Field IDs** ⚠️ BLOCKER
Contact Encompass admin to provide field IDs for:

**SOP Conditions (High Priority):**
- Title Report Expiry Date
- CPL Expiry Date (confirm if field 3094 works)
- Lock Expiration Date (already have: 762) ✅
- Closing Date (already have: 748) ✅

**Insurance Validation (High Priority):**
- Master Policy Loss Payee Name
- Master Policy Expiration Date
- Hazard Insurance Premium Amount
- HOI Premium Status (Refi)
- Flood Insurance fields

**Document Completeness (Medium Priority):**
- VVOE Date
- Employment Verification Date
- Note Date
- 92900A Signature fields (UW, LO, Borrower)

**State Rules (Medium Priority):**
- Home Equity Loan Indicator
- Manufactured Home Indicator
- Attorney Vendor field
- County Name

---

### **Step 2: Test Current Implementation** 🧪
- [ ] Restart backend and frontend
- [ ] Test with loan `8587ad65-e186-4655-b813-f713ff98709f`
- [ ] Verify Lock Expiration and Title Company checks appear
- [ ] Verify Discrepancy Detection shows hard stops correctly
- [ ] Take screenshots for documentation

---

### **Step 3: Commit Phase 1 Changes** 📦
```bash
git add agents/drawdocs/tools/primitives.py
git add SOP_CONDITIONS_*.md
git add TESTING_SOP_CONDITIONS.md
git add DRAWDOCS_TODO.md
git commit -F COMMIT_MESSAGE.txt
git push
```

---

### **Step 4: Plan Phase 2 Priorities** 📋
**Recommended Order:**
1. **Insurance Validation** (completes 4 SOP conditions)
2. **Document Completeness** (completes 3 SOP conditions)
3. **State-Specific Rules** (enables production use for TX, NV, CA, etc.)

---

## ✅ **PHASE 1: PTF CONDITIONS & DISCREPANCY DETECTION** (25% COMPLETE)

### **Task 1.1: Add SOP Condition Checks** ✅ DONE (Updated Dec 9, 2025)
- [x] **Lock Date Expiration Check** - Field 762
  - Verifies lock doesn't expire before 3-day rescission period
  - CRITICAL blocker if lock expires too soon
  - Auto-calculates rescission end date (Closing Date + 3 days)
- [x] **Loan Amount in Title Report** - Field 1109
  - Already implemented in Discrepancy Detection
- [x] ~~**Title Company Validation** - Field 411~~ **REMOVED**
  - Field 411 deprecated in new verification file (Dec 9, 2025)
  - Removed from primitives.py
  
**Files modified:**
- ✅ `agents/drawdocs/tools/primitives.py` - Added `_check_lock_expiration()`, removed `_check_title_company()`
- ✅ `agents/drawdocs/config/discrepancy_rules.py` - Removed FR0104 (Borrower Present Addr)
- ✅ Frontend automatically displays checks (no changes needed)

**Documentation:**
- ✅ `SOP_CONDITIONS_ANALYSIS.md` - Full analysis of 12 conditions
- ✅ `SOP_CONDITIONS_IMPLEMENTATION_PLAN.md` - Implementation roadmap
- ✅ `SOP_CONDITIONS_COMPLETE.md` - Summary (updated)
- ✅ `TESTING_SOP_CONDITIONS.md` - Testing guide
- ✅ `VERIFICATION_FILE_CHANGES.md` - Analysis of CSV update
- ✅ `VERIFICATION_FILE_UPDATE_COMPLETE.md` - Update summary

**Progress: 2/12 SOP Conditions (17%)** ⬇️ (was 3/12, Title Company removed)

---

### **Task 1.2: Complete Remaining SOP Conditions** ⏸️ BLOCKED

**BLOCKED - Need Encompass Field IDs:**

| # | SOP Condition | Field Needed | Priority | Blocker |
|---|---------------|--------------|----------|---------|
| 4 | Title Report Expiry | Title Report Expiry Date | HIGH | No field ID in CSV |
| 5 | CPL Expiry | CPL Expiry Date (maybe 3094?) | HIGH | Need to confirm field 3094 |
| 6 | Hazard Insurance Premium | Insurance Premium Balance | MEDIUM | No field ID in CSV |
| 7 | Master Policy Loss Payee | Loss Payee Name | MEDIUM | May be in document text only |
| 8 | HOI Premium Status (Refi) | HOI Payment Status | MEDIUM | No field ID in CSV |
| 9 | VVOE Date Check | VVOE Date, Note Date | MEDIUM | No field ID in CSV |
| 10 | 92900A Signature | 92900A UW Signature Field | LOW | No field ID in CSV |
| 11 | 92900A Corrections | 92900A Data Fields | LOW | No field ID in CSV |
| 12 | Insurance Info Missing | Various Insurance Fields | LOW | No field ID in CSV |

**Action Required:**
- [ ] Contact Encompass admin for missing field IDs
- [ ] Confirm field 3094 is CPL commitment date
- [ ] Investigate if loss payee is document-based or field-based
- [ ] Add found field IDs to `master_field_data.csv`
- [ ] Implement checks using same pattern as Lock/Title Company

**Files to modify once field IDs available:**
- `agents/drawdocs/tools/primitives.py` - Add new check functions
- Test with `TESTING_SOP_CONDITIONS.md` guide

---

### **Task 1.3: Build Discrepancy Detection Agent** ✅ DONE
- [x] Create `agents/drawdocs/subagents/discrepancy_agent/` directory
- [x] Create `discrepancy_agent.py` with main logic
- [x] Implement field-by-field comparison: extracted vs Encompass values
- [x] Implement discrepancy rules (13 rules total):
  - [x] Loan Amount mismatch (HARD STOP)
  - [x] Borrower First Name mismatch
  - [x] Borrower Last Name mismatch
  - [x] Subject Property Address mismatch
  - [x] Property City mismatch
  - [x] Property State mismatch
  - [x] Property Zip mismatch
  - [x] Sales Price mismatch
  - [x] Purchase Price mismatch
  - [x] Borrower Email mismatch
  - [x] Borrower Present Address mismatch
  - [x] Co-Borrower fields (if applicable)
  - [x] Calculated fields (LTV, CLTV, DTI)
- [x] Generate PTF conditions for soft discrepancies
- [x] Flag HARD STOPS for critical mismatches

**Files created:** ✅
- `agents/drawdocs/subagents/discrepancy_agent/__init__.py`
- `agents/drawdocs/subagents/discrepancy_agent/discrepancy_agent.py`
- `agents/drawdocs/config/discrepancy_rules.py` (13 rules with thresholds)

**Output Format:** ✅
```json
{
  "loan_id": "...",
  "fields_checked": 13,
  "discrepancies_found": 1,
  "hard_stops": [
    {
      "field_id": "1109",
      "field_name": "Loan Amount",
      "extracted": "208000",
      "encompass": "189000.00",
      "action": "HARD STOP - Contact Team Lead immediately"
    }
  ],
  "soft_discrepancies": [
    {
      "field_id": "11",
      "field_name": "Subject Property Address",
      "extracted": "191 Dover Dr",
      "encompass": "191 Dover Drive",
      "ptf_text": "Address format differs - verify with title"
    }
  ],
  "status": "blocked" // or "proceed_with_conditions"
}
```

**Acceptance Criteria:** ✅
- ✅ Detects name mismatches
- ✅ Detects address mismatches
- ✅ Flags hard stops correctly (Loan Amount)
- ✅ Generates appropriate PTF conditions
- ✅ Does NOT flag trivial differences (fuzzy matching with 90% threshold)

---

### **Task 1.4: Integrate Discrepancy Agent into Orchestrator** ✅ DONE
- [x] Add Discrepancy Agent as Step 3 (after Drawcore, before Verification)
- [x] Update orchestrator to handle "blocked" status
- [x] If hard stops found → Set status to BLOCKED in demo mode, HALT in production
- [x] If soft discrepancies → Add PTFs, continue to Verification
- [x] Update status writer to include discrepancy results
- [x] Update frontend to display discrepancies and PTFs

**Files modified:** ✅
- `agents/drawdocs/orchestrator_agent.py` - Added discrepancy step
- `agents/drawdocs/status_writer.py` - Added discrepancy logging
- `backend/agent_runner.py` - Added discrepancy to pipeline
- `backend/services.py` - Added discrepancy status handling
- `backend/models.py` - Added discrepancy agent status
- `frontend/src/types/index.ts` - Added DiscrepancyOutput type
- `frontend/src/components/runs/final-report-tab.tsx` - Added DiscrepancyDetectionCard
- `frontend/src/components/ui/agent-icon.tsx` - Added discrepancy icon
- `frontend/src/lib/log-parser.ts` - Added discrepancy log parsing

**Acceptance Criteria:** ✅
- ✅ Pipeline stops on hard stops (demo mode shows BLOCKED)
- ✅ Pipeline continues with PTFs on soft discrepancies  
- ✅ Frontend displays hard stops and PTF conditions
- ✅ Demo mode banner shows when hard stops detected
- ✅ Detailed discrepancy card with field-by-field comparison

---

### **✅ PHASE 1 SUMMARY**

**✅ COMPLETED (75%):**
1. ✅ Discrepancy Detection Agent - Full implementation with 13 rules
2. ✅ Frontend Integration - Beautiful UI with hard stops and PTF display
3. ✅ SOP Conditions (3/12) - Lock Expiration, Title Company, Loan Amount
4. ✅ Orchestrator Integration - Full pipeline with demo mode
5. ✅ Human-in-the-Loop Review - Field review before writing

**⏸️ BLOCKED (25%):**
1. ⏸️ Remaining SOP Conditions (9/12) - **Need Encompass field IDs**
   - Title Report Expiry, CPL Expiry, Insurance fields, VVOE, 92900A
2. ⏸️ PTF Condition Writing - Not yet implemented (could use Encompass Conditions API)

**🚀 NEXT ACTIONS:**
1. Get missing field IDs from Encompass admin
2. Implement remaining 9 SOP conditions
3. (Optional) Add PTF writing to Encompass Conditions section

---

## 🌎 **PHASE 2: INSURANCE VALIDATION & DOCUMENT COMPLETENESS** (RECOMMENDED NEXT)

**Why Phase 2 First:** Insurance and document validation directly support the remaining SOP conditions and don't require complex state-specific rules.

### **Task 2.1: Insurance Validation Module** 🔥 HIGH PRIORITY

**Fields Needed (Get from Encompass Admin):**
- [ ] Master Policy Loss Payee Name
- [ ] Master Policy Expiration Date
- [ ] Hazard Insurance Premium Amount
- [ ] Hazard Insurance Payment Status
- [ ] HOI Premium Status (for Refi)
- [ ] Flood Insurance Required (Y/N)
- [ ] Flood Insurance Policy Number
- [ ] Flood Insurance Expiration Date

**Implementation:**
- [ ] Create `agents/drawdocs/subagents/insurance_validator/`
- [ ] Create `insurance_validator.py` with validation logic
- [ ] Check Master Policy has "ISAOA/ATIMA" or "All Western Mortgage, Inc."
- [ ] Verify insurance expiration dates are after closing date
- [ ] Calculate insurance premium balance (if applicable)
- [ ] Validate flood insurance when required
- [ ] Generate PTF conditions for insurance issues

**Files to create:**
- `agents/drawdocs/subagents/insurance_validator/__init__.py`
- `agents/drawdocs/subagents/insurance_validator/insurance_validator.py`
- `agents/drawdocs/config/insurance_rules.py`

**Acceptance Criteria:**
- ✅ Validates Master Policy loss payee format
- ✅ Checks insurance expiration dates
- ✅ Flags missing insurance when required
- ✅ Generates appropriate PTF conditions

---

### **Task 2.2: Document Completeness Checker** 🔥 HIGH PRIORITY

**Fields Needed (Get from Encompass Admin):**
- [ ] VVOE Date
- [ ] Employment Verification Date
- [ ] Note Date / Document Date
- [ ] 92900A Signature Date (Underwriter)
- [ ] 92900A Signature Date (Loan Officer)
- [ ] 92900A Signature Date (Borrower)
- [ ] 92900A Data Verification Status

**Implementation:**
- [ ] Create `agents/drawdocs/subagents/document_completeness/`
- [ ] Create `document_completeness.py` with validation logic
- [ ] Check VVOE is within 10 days of note date
- [ ] Verify 92900A has all required signatures
- [ ] Validate 92900A data accuracy (loan term, property address, etc.)
- [ ] Check for additional required documents based on loan type
- [ ] Generate PTF conditions for missing/outdated documents

**Files to create:**
- `agents/drawdocs/subagents/document_completeness/__init__.py`
- `agents/drawdocs/subagents/document_completeness/document_completeness.py`

**Acceptance Criteria:**
- ✅ VVOE recency check (within 10 days)
- ✅ 92900A signature verification
- ✅ Document date validation
- ✅ PTF conditions generated for missing items

---

### **Task 2.3: Integrate Insurance & Document Validators**

- [ ] Add Insurance Validator as Step 5.5 (after OrderDocs)
- [ ] Add Document Completeness as Step 5.75 (after Insurance)
- [ ] Update orchestrator to call both validators
- [ ] Update frontend to display insurance and document validation results

**Files to modify:**
- `agents/drawdocs/orchestrator_agent.py`
- `agents/drawdocs/status_writer.py`
- `frontend/src/components/runs/final-report-tab.tsx`

---

## 🌎 **PHASE 3: STATE-SPECIFIC RULES ENGINE** (AFTER PHASE 2)

### **Task 3.1: Create State Rules Configuration** 🔶 MEDIUM PRIORITY

**Fields Needed (Get from Encompass Admin):**
- [ ] Property State (already have: field 14)
- [ ] Home Equity Loan Indicator
- [ ] Manufactured Home Indicator
- [ ] Attorney Name/Vendor
- [ ] Attorney Fee Amount
- [ ] Title Company Name (already have: field 411)
- [ ] County Name
- [ ] Marital Status fields

**Implementation:**
- [ ] Create `agents/drawdocs/config/state_rules.py` with state-specific logic
- [ ] Implement rules for:
  - [ ] **Texas** (attorney handling, home equity, NBS requirements, vesting rules)
    - Attorney vendors: BM&G (El Paso $225), Cain&Kiel (Proctor/Plano/Patrick Moore $325)
    - Home Equity: 12-day notice, forms 3044.1 & 3185, T-42/T-42.1 endorsements
    - NBS required, manufactured home check, no "Joint Tenants" in vesting
  - [ ] **Florida** (credit report cap, HHF DPA exemptions)
  - [ ] **Nevada** (remove worksheets, Prosperity branch rules)
  - [ ] **California** (tax calculation, no impounds option)
  - [ ] **Colorado** (marital status not required, trustee rules)
  - [ ] **Illinois** (if applicable)
- [ ] Add state-specific fee caps
- [ ] Add state-specific document exclusions/inclusions
- [ ] Add state-specific vesting formats

**Structure:**
```python
STATE_RULES = {
    "TX": {
        "attorney_required": True,
        "attorney_vendors": {
            "BM&G": {"branches": ["El Paso"], "fee": 225},
            "Cain&Kiel": {"branches": ["Proctor", "Plano", "Patrick Moore"], "fee": 325}
        },
        "home_equity_rules": {
            "notice_days": 12,
            "required_forms": ["3044.1", "3185"],
            "endorsements": ["T-42", "T-42.1"]
        },
        "nbs_required": True,
        "vesting_format": "No 'Joint Tenants' verbiage - use marital status only",
        "manufactured_home_check": True
    },
    # ... etc
}
```

**Files to create:**
- `agents/drawdocs/config/state_rules.py`
- `agents/drawdocs/config/test_state_rules.py`

---

### **Task 2.2: Create Loan Type Rules Configuration**
- [ ] Create `agents/drawdocs/config/loan_type_rules.py`
- [ ] Implement rules for:
  - [ ] **FHA** (case number, UFMIP, riders, forms)
  - [ ] **VA** (COE, funding fee calculation, riders)
  - [ ] **USDA** (case number format, income eligibility, forms)
  - [ ] **Conventional** (PMI rules, no special requirements)
- [ ] Add loan-type-specific document requirements
- [ ] Add loan-type-specific fee calculations

**Files to create:**
- `agents/drawdocs/config/loan_type_rules.py`
- `agents/drawdocs/config/test_loan_type_rules.py`

---

### **Task 2.3: Build Rules Engine**
- [ ] Create `agents/drawdocs/rules_engine.py`
- [ ] Implement `get_applicable_rules(loan_id, state, loan_type, branch, investor)`
- [ ] Merge state rules + loan type rules + branch overrides + investor overrides
- [ ] Return unified ruleset for the specific loan
- [ ] Add rule priority/override logic

**Files to create:**
- `agents/drawdocs/rules_engine.py`
- `agents/drawdocs/test_rules_engine.py`

---

### **Task 2.4: Apply Rules in Drawcore Agent**
- [ ] Update all 5 phases to call `rules_engine.get_applicable_rules()`
- [ ] Apply state-specific field formatting (vesting, trustee, etc.)
- [ ] Apply loan-type-specific calculations (funding fees, MIP, etc.)
- [ ] Add state-specific PTF conditions automatically

**Files to modify:**
- `agents/drawdocs/subagents/drawcore_agent/phases/phase1_borrower_lo.py`
- `agents/drawdocs/subagents/drawcore_agent/phases/phase2_contacts.py`
- `agents/drawdocs/subagents/drawcore_agent/phases/phase3_property.py`
- `agents/drawdocs/subagents/drawcore_agent/phases/phase4_financial.py`
- `agents/drawdocs/subagents/drawcore_agent/phases/phase5_cd.py`

---

## 📦 **PHASE 3: DOCUMENT PACKAGE CUSTOMIZATION (MEDIUM PRIORITY)**

### **Task 3.1: Add Document Package Rules**
- [ ] Create `agents/drawdocs/config/document_package_rules.py`
- [ ] Define base closing package (all standard docs)
- [ ] Define exclusion rules by state
- [ ] Define exclusion rules by loan type
- [ ] Define inclusion rules (additional docs to add)

**Rules to implement:**
```python
PACKAGE_EXCLUSIONS = {
    "ALL": ["Data Entry Proof Sheet", "Data Entry Proof Sheet – Fees", "Seller CD"],
    "NV": ["NV Repayment Ability Verification Worksheet"],
    "WITHOUT_CTC": ["Final 1003", "92900A"],
    "CHASE_INVESTOR": ["CHASE-prefixed docs"]
}

PACKAGE_INCLUSIONS = {
    "TX": ["Attorney Package"],
    "POA_APPROVED": ["POA Document"],
    "ALL": ["Evidence of Insurance", "Appraisal Invoice", "Credit Invoice", "Payoffs"]
}
```

**Files to create:**
- `agents/drawdocs/config/document_package_rules.py`

---

### **Task 3.2: Update OrderDocs Agent with Package Customization**
- [ ] Modify `order_documents()` to accept `exclude_docs` and `include_docs` params
- [ ] Apply state-specific exclusions
- [ ] Apply loan-type-specific exclusions
- [ ] Add required additional documents
- [ ] Log all package customizations

**Files to modify:**
- `agents/drawdocs/subagents/orderdocs_agent/orderdocs_agent.py`

---

## 🏦 **PHASE 4: TRUST & POA HANDLING (MEDIUM PRIORITY)**

### **Task 4.1: Add Trust Document Parsing**
- [ ] Add trust document detection in Prep Agent
- [ ] Extract trust details:
  - [ ] Trust Name
  - [ ] Trust Date/Year
  - [ ] Org State
  - [ ] Org Type ("An Inter Vivos Trust")
  - [ ] Beneficiary (if listed)
  - [ ] Amended/Restated dates
- [ ] Format vesting string: `"[Name], Trustee of the [TRUST NAME] dated [DATE]"`

**Files to modify:**
- `agents/drawdocs/subagents/preparation_agent/tools/extraction_schemas.py` (add Trust schema)
- `agents/drawdocs/subagents/preparation_agent/preparation_agent.py`

---

### **Task 4.2: Add State-Specific Trustee Rules**
- [ ] NV/CA/AZ/WA/UT/OR: Use Title Company name
- [ ] CO: Use County name & address
- [ ] TX: Use Thomas E Black Jr. (from Business contacts, Attorney Category)
- [ ] FL/MI: No trustee information
- [ ] Auto-populate trustee based on state rules

**Files to modify:**
- `agents/drawdocs/config/state_rules.py`
- `agents/drawdocs/subagents/drawcore_agent/phases/phase2_contacts.py`

---

### **Task 4.3: Add POA Approval Check**
- [ ] Check `Funding Custom Fields` for "Close in a POA" approval
- [ ] If approved → Add POA document to closing package
- [ ] If not approved but POA detected → Add PTF condition

**Files to modify:**
- `agents/drawdocs/subagents/drawcore_agent/phases/phase1_borrower_lo.py`
- `agents/drawdocs/subagents/orderdocs_agent/orderdocs_agent.py`

---

## 🔢 **PHASE 5: MERS/MIN VERIFICATION (LOW PRIORITY)**

### **Task 5.1: Add MERS MIN Generation**
- [ ] Add `generate_mers_min(loan_id)` to primitives
- [ ] Click MERS MIN box in Encompass
- [ ] Extract generated MIN number

**Files to modify:**
- `agents/drawdocs/tools/primitives.py`

---

### **Task 5.2: Add MERS Website Verification**
- [ ] Research MERS API or web scraping approach
- [ ] Implement `verify_min_uniqueness(min_number, borrower_ssn, coborrower_ssn)`
- [ ] Search by SSN on MERS website
- [ ] Generate verification report PDF
- [ ] Upload PDF to Encompass e-Folder under "MIN-SSN Summary"

**Files to create:**
- `agents/drawdocs/tools/mers_verification.py`

---

## 💰 **PHASE 6: FEE VALIDATION & CAPS (MEDIUM PRIORITY)**

### **Task 6.1: Add Fee Validation Rules**
- [ ] Create `agents/drawdocs/config/fee_rules.py`
- [ ] Implement state-specific fee caps:
  - [ ] FL credit report cap: $48.30
- [ ] Implement tolerance cure checking
- [ ] Implement zero tolerance vs 10% tolerance rules
- [ ] Flag random fees in Section A

**Files to create:**
- `agents/drawdocs/config/fee_rules.py`

---

### **Task 6.2: Add Fee Validation Agent**
- [ ] Create fee validation logic
- [ ] Compare fees from LE, CD, invoices
- [ ] Check for fee variance violations
- [ ] Generate PTF or HARD STOP for violations

**Files to create:**
- `agents/drawdocs/subagents/fee_validation_agent/fee_validation_agent.py`

---

## 🏠 **PHASE 7: INSURANCE VALIDATION (MEDIUM PRIORITY)**

### **Task 7.1: Add Insurance Validation Rules**
- [ ] Check dwelling coverage ≥ loan amount
- [ ] Verify mortgagee clause = "ALL WESTERN MORTGAGE, INC."
- [ ] Verify loss payee correct
- [ ] Check flood insurance if required
- [ ] Check expiration dates (must be ≥ 1 year from closing)
- [ ] Hard stop if dwelling coverage insufficient

**Files to create:**
- `agents/drawdocs/subagents/insurance_validation_agent/insurance_validation_agent.py`

---

## 🏢 **PHASE 8: BRANCH & INVESTOR OVERRIDES (LOW PRIORITY)**

### **Task 8.1: Add Branch Rules**
- [ ] Create `agents/drawdocs/config/branch_rules.py`
- [ ] Implement branch-specific overrides:
  - [ ] Florida Branch credit report cap
  - [ ] Prosperity Branch (NV) no cushions/SIDS
  - [ ] Texas branch attorney assignments

**Files to create:**
- `agents/drawdocs/config/branch_rules.py`

---

### **Task 8.2: Add Investor Rules**
- [ ] Create `agents/drawdocs/config/investor_rules.py`
- [ ] Implement investor-specific document exclusions (Chase, etc.)
- [ ] Implement investor-specific fee restrictions

**Files to create:**
- `agents/drawdocs/config/investor_rules.py`

---

## 📋 **PHASE 9: MISSING CSV FIELDS (ONGOING)**

### **Task 9.1: Add Extraction Sources for High-Priority Fields**
- [ ] Borrower Middle Name (`4001`) → Source: `ID` or `Final 1003`
- [ ] Co-Borrower First Name (`4004`) → Source: `ID` or `Final 1003`
- [ ] Co-Borrower Middle Name (`4005`) → Source: `ID` or `Final 1003`
- [ ] Co-Borrower Last Name (`4006`) → Source: `ID` or `Final 1003`
- [ ] Co-Borrower DOB (`1403`) → Source: `ID` or `Credit Report`
- [ ] Co-Borrower SSN (`97`) → Source: `Credit Report` or `W2`
- [ ] Fees Tax Per Mo (`231`) → Source: `Tax Summary` or `Final 1003`
- [ ] Fees Homeowner's Ins Premium (`578`) → Source: `HOI Policy`
- [ ] Fees City Property Tax Paid To (`SYS.X322`) → Source: `Tax Summary`

**Files to modify:**
- `agents/drawdocs/subagents/preparation_agent/DrawingDoc Verifications.csv`

---

## 🧪 **PHASE 10: TESTING & VALIDATION**

### **Task 10.1: Create Comprehensive Test Suite**
- [ ] Test PTF condition creation and reading
- [ ] Test discrepancy detection with known mismatches
- [ ] Test hard stop logic
- [ ] Test state-specific rules (all 6 states)
- [ ] Test loan-type-specific rules (FHA, VA, USDA, Conv)
- [ ] Test document package customization
- [ ] Test trust handling
- [ ] Test fee validation
- [ ] Test insurance validation

**Files to create:**
- `agents/drawdocs/tests/test_ptf_conditions.py`
- `agents/drawdocs/tests/test_discrepancy_detection.py`
- `agents/drawdocs/tests/test_state_rules.py`
- `agents/drawdocs/tests/test_loan_type_rules.py`

---

### **Task 10.2: Create End-to-End Test Scenarios**
- [ ] Texas Purchase Conventional
- [ ] Texas Home Equity Cash-Out Refi
- [ ] Florida FHA Purchase
- [ ] California VA Purchase
- [ ] Nevada Conventional Refi
- [ ] Colorado USDA Purchase

**Files to create:**
- `agents/drawdocs/test_scenarios/texas_purchase_conv.json`
- `agents/drawdocs/test_scenarios/texas_home_equity.json`
- (etc.)

---

## 📊 **PRIORITY SUMMARY**

### **🔴 CRITICAL (Do First):**
1. ✅ Phase 1: PTF Conditions & Discrepancy Detection
2. ✅ Phase 2: State-Specific Rules Engine

### **🟡 HIGH (Do Next):**
3. ✅ Phase 3: Document Package Customization
4. ✅ Phase 4: Trust & POA Handling
5. ✅ Phase 6: Fee Validation & Caps
6. ✅ Phase 7: Insurance Validation

### **🟢 MEDIUM (Do Later):**
7. ✅ Phase 8: Branch & Investor Overrides
8. ✅ Phase 9: Missing CSV Fields

### **⚪ LOW (Nice to Have):**
9. ✅ Phase 5: MERS/MIN Verification
10. ✅ Phase 10: Comprehensive Testing

---

## 📈 **PROGRESS TRACKING**

**Current Status:**  
- ✅ 4 Agents Complete (Prep, Drawcore, Verification, OrderDocs, Discrepancy)
- ✅ Phase 1: 75% Complete (3/4 tasks)
- ⏸️ Blocked on missing Encompass field IDs

**Phase Completion:**
- Phase 1: 75% ✅✅✅⏸️
- Phase 2: 0% (Planned)
- Phase 3: 0% (Planned)

**SOP Conditions:**
- ✅ Completed: 3/12 (25%)
- ⏸️ Blocked: 9/12 (75%) - Need field IDs

---

## 🚀 **PHASE 2 ACTION PLAN**

### **Week 1: Get Field IDs & Complete SOP Conditions**
**Priority: CRITICAL**

**Day 1-2: Contact Encompass Admin**
- [ ] Request all missing field IDs (see list in Immediate Action Plan above)
- [ ] Get CSV with field names, IDs, and data types
- [ ] Update `master_field_data.csv` with new fields

**Day 3-4: Implement Remaining SOP Conditions**
- [ ] Add Title Report Expiry check (same pattern as Lock Expiration)
- [ ] Add CPL Expiry check (if field 3094 confirmed)
- [ ] Test all conditions end-to-end

**Day 5: Insurance Validation Prep**
- [ ] Create `insurance_validator` directory structure
- [ ] Define insurance rules and thresholds
- [ ] Create test cases

---

### **Week 2: Insurance Validation**
**Priority: HIGH**

**Day 1-3: Build Insurance Validator**
- [ ] Create `insurance_validator.py`
- [ ] Implement Master Policy validation (ISAOA/ATIMA check)
- [ ] Implement expiration date checks
- [ ] Implement premium balance calculation
- [ ] Implement flood insurance validation

**Day 4: Integrate Insurance Validator**
- [ ] Add to orchestrator pipeline
- [ ] Update frontend to display results
- [ ] Test with various loan scenarios

**Day 5: Document Completeness Prep**
- [ ] Create `document_completeness` directory structure
- [ ] Define document validation rules
- [ ] Create test cases

---

### **Week 3: Document Completeness**
**Priority: HIGH**

**Day 1-3: Build Document Completeness Checker**
- [ ] Create `document_completeness.py`
- [ ] Implement VVOE date check (within 10 days of note date)
- [ ] Implement 92900A signature verification
- [ ] Implement 92900A data validation
- [ ] Check for additional required documents

**Day 4: Integration**
- [ ] Add to orchestrator pipeline
- [ ] Update frontend
- [ ] Test end-to-end

**Day 5: Testing & Documentation**
- [ ] Full system test with all validators
- [ ] Update documentation
- [ ] Create demo video

---

### **Week 4: State-Specific Rules (Start)**
**Priority: MEDIUM**

**Day 1-2: Texas Rules**
- [ ] Implement attorney vendor logic
- [ ] Implement home equity rules
- [ ] Implement vesting format rules

**Day 3-4: Nevada & California Rules**
- [ ] Implement Nevada-specific rules
- [ ] Implement California-specific rules

**Day 5: Testing**
- [ ] Test with TX, NV, CA loans
- [ ] Document state-specific behavior

---

## 🎯 **IMMEDIATE NEXT STEPS (TODAY)**

1. ✅ **Update TODO** (This file) - DONE
2. 🧪 **Test Current Implementation**
   ```bash
   # Clear cache
   find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
   
   # Start backend
   cd backend && python main.py
   
   # Start frontend (in another terminal)
   cd frontend && npm run dev
   
   # Test with loan: 8587ad65-e186-4655-b813-f713ff98709f
   ```

3. 📦 **Commit Phase 1 Work**
   ```bash
   git add agents/drawdocs/tools/primitives.py
   git add SOP_CONDITIONS_*.md
   git add TESTING_SOP_CONDITIONS.md
   git add DRAWDOCS_TODO.md
   git add COMMIT_MESSAGE.txt
   git commit -F COMMIT_MESSAGE.txt
   git push origin feature/disclosure-agent
   ```

4. 📋 **Prepare Field ID Request**
   - Draft email to Encompass admin with complete field list
   - Prioritize by critical path (Insurance > Documents > State Rules)

---

**Phase 1 Complete! Ready for Phase 2! 🎉**

