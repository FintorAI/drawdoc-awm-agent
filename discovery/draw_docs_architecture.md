# Draw Docs Agent Architecture (Refined)

## Document Info
- **Created**: November 28, 2025
- **Based On**: SOP Analysis, MVP Boilerplate, Gap Analysis
- **Owner**: Anton

---

## 1. Overview

The Draw Docs Agent handles the complete process of preparing and ordering closing documents after a loan receives Clear to Close (CTC) status. This is a **complex, document-heavy workflow** with 29 major steps, 35+ documents to verify, and extensive state/loan-type/branch-specific rules.

### Key Complexity Drivers
- Document verification against Encompass fields
- PTF (Prior to Funding) condition management
- State-specific rules (TX, FL, NV, CA, CO, IL)
- Loan-type specific forms (FHA, VA, USDA, Conventional)
- Branch/Investor-specific overrides
- Hard stops vs soft stops logic
- External integrations (MERS, Mavent, USPS)

---

## 2. Entry Conditions (Prerequisites)

Before processing begins, verify ALL of these:

| Condition | Check Method | Hard Stop if Fails |
|-----------|--------------|-------------------|
| CTC Status | Milestone = "Clear to Close" (bold) | ✅ Yes |
| CD Approved | CD Status = "CD Approved" | ✅ Yes |
| CD Acknowledged | Initial CD signed by Borrower(s) | ✅ Yes |
| 3-Day Wait Complete | CD ACK date + 3 business days passed | ✅ Yes |
| Docs Ordered Queue | Loan in "Closer – Docs Ordered" pipeline | ✅ Yes |

**TAT (Turnaround Time)**: 6 Business Hours from queue entry + CD approved + ACK

---

## 3. Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DRAW DOCS ORCHESTRATOR                                 │
│                                                                                  │
│  Coordinates agents, manages state, handles escalations                         │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────────┐   ┌───────────────────────┐   ┌────────────────────────┐
│  DOCS PREP AGENT  │──▶│  DOCS DRAW CORE AGENT │──▶│ AUDIT & COMPLIANCE     │
│                   │   │                       │   │ AGENT                  │
│ • Entry checks    │   │ • 5 Phases            │   │ • Cross-validation     │
│ • Doc download    │   │ • Field updates       │   │ • Mavent compliance    │
│ • Entity extract  │   │ • PTF conditions      │   │ • Fee variance/cures   │
│ • doc_context     │   │ • State rules         │   │ • Final approval       │
└───────────────────┘   └───────────────────────┘   └────────────────────────┘
                                                               │
                                                               ▼
                                                    ┌────────────────────────┐
                                                    │ ORDER & DISTRIBUTION   │
                                                    │ (Deterministic)        │
                                                    │                        │
                                                    │ • Generate package     │
                                                    │ • Update milestone     │
                                                    │ • Send to parties      │
                                                    └────────────────────────┘
```

---

## 4. Agent Specifications

### 4.1 Docs Prep Agent

**Purpose**: Validate preconditions, download documents, extract structured data into `doc_context`.

#### Responsibilities

1. **Entry Condition Verification**
   - Check CTC status, CD approval, CD ACK, 3-day wait, queue placement
   - Verify no Pre-Funding QC flags
   - Check ARM Lock Desk approval (if ARM)
   - Check Non-QM Eric Gut review (if Non-QM)

2. **Document Collection** (35+ documents)
   ```
   Application Section:
   - Initial 1003, Approval Final, MI Certificate, Borrower IDs, SSN Verification
   
   Government Section:
   - FHA Case Assignment, FHA Refinance Auth, VA Case Assignment, VA COE
   
   Credit Section:
   - Credit Report, Payoff (Refinance)
   
   Property Section:
   - Title Report, Appraisal, Purchase Agreement, Tax Summary, USPS ZIP
   - Evidence of Insurance (HO6, HO3, Master), Flood Certificate, POA
   
   Disclosures Section:
   - Initial LE, Last Disclosed LE
   
   Closing Section:
   - Invoices, CD/COC CD, CD ACK, Final 1003, Escrow Wire, CPL, Pre-Note VOE
   ```

3. **Entity Extraction** → Build `doc_context`
   - Borrower info (names, SSN, DOB, marital status, vesting)
   - Property info (address, type, occupancy, legal description)
   - Loan info (type, purpose, terms, rate, case numbers)
   - Insurance info (coverage, mortgagee clause, flood zone)
   - Fee info (from LE, CD, invoices)
   - Contact info (title, escrow, agents)

4. **Branch/Investor/State Identification**
   - Identify branch (affects fee caps, approval workflows)
   - Identify investor (affects specific requirements)
   - Identify state (affects rules, endorsements, taxes)

#### Tools Used
```python
get_loan_context(loan_id)
check_entry_conditions(loan_id)
list_required_documents(loan_id, loan_type, state)
download_documents(loan_id, categories[])
extract_entities_from_docs(docs) → doc_context
identify_branch_investor_state(loan_id)
log_issue(loan_id, severity, message)
```

#### Output
```json
{
  "doc_context": {
    "borrowers": [...],
    "property": {...},
    "loan": {...},
    "insurance": {...},
    "fees": {...},
    "contacts": {...},
    "metadata": {
      "branch_id": "...",
      "investor_id": "...",
      "state": "...",
      "loan_type": "FHA|VA|USDA|Conventional",
      "purpose": "Purchase|Refinance|CashOut"
    }
  },
  "missing_docs": [...],
  "issues": [...]
}
```

#### Error Handling
- Missing critical doc → Log issue, HALT
- Missing non-critical doc → Add to issues, CONTINUE with PTF condition

---

### 4.2 Docs Draw Core Agent

**Purpose**: Apply `doc_context` to Encompass across 5 phases, adding PTF conditions as needed.

This is the **workhorse agent** - most complex, handles the bulk of the 29 SOP steps.

#### Phase Structure

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                         DOCS DRAW CORE AGENT                                    │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  PHASE 1: Borrower & Loan Officer Setup                                        │
│  ────────────────────────────────────────                                       │
│  • SOP Steps: 4, 5, 6, 7                                                        │
│  • Forms: Borrower Summary, Borrower Info-Vesting, Trust Section, 1003 Page-3  │
│  • Special: MIN/MERS verification, SSA Authorization, Trust handling           │
│                                                                                 │
│  PHASE 2: Contacts & Vendors                                                    │
│  ────────────────────────────────                                               │
│  • SOP Steps: 9, 12                                                             │
│  • Forms: File Contacts, Closing Vendor Information                             │
│  • Special: Trustee by state, Docs Prepared By (TX vs others)                  │
│                                                                                 │
│  PHASE 3: Property & Program (FHA/VA/USDA/Conv)                                │
│  ──────────────────────────────────────────────                                 │
│  • SOP Steps: 13, 14, 15, 16                                                    │
│  • Forms: Property Information, HUD 92900ALT, VA Management, USDA Management   │
│  • Special: Riders, Endorsements, Case numbers, Funding fees                   │
│                                                                                 │
│  PHASE 4: Financial Setup                                                       │
│  ────────────────────────────                                                   │
│  • SOP Steps: 17, 18, 19, 20, 21, 22                                            │
│  • Forms: RegZ-CD, Aggregate Escrow, 2015 Itemization, Fee Variance            │
│  • Special: MI calculation, Tax calc by state, Impound rules                   │
│                                                                                 │
│  PHASE 5: Closing Disclosure Pages                                              │
│  ───────────────────────────────────                                            │
│  • SOP Steps: 23, 24, 25, 26, 27                                                │
│  • Forms: CD Pages 1-5                                                          │
│  • Special: Rescission dates, Disbursement dates, APR verification             │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

#### Phase 1: Borrower & Loan Officer Setup

**Fields to Verify/Update:**

| Form | Field | Source | Validation |
|------|-------|--------|------------|
| Borrower Summary | AWM Loan # | Final 1003 | Exact match |
| Borrower Summary | Borrower Name | Approval Final + 1003 | Exact match |
| Borrower Summary | SSN | Credit + ID docs | Match across all |
| Borrower Summary | DOB | ID docs | Verify |
| Borrower Info-Vesting | Vesting | 1003 (Purchase) or Title+1003 (Refi) | Confirm with processor |
| Borrower Info-Vesting | AKA Names | Credit report, Fraud report, ID | Extract all |
| Borrower Info-Vesting | Vesting Type | Per situation | Individual/Co-Signor/Title Only/Settlor |
| 1003 Page-3 | Lender Name | Static | "ALL WESTERN MORTGAGE, INC." |
| 1003 Page-3 | LO NMLS | Mavent report | Must say PASS |

**Special Handling:**

```python
# MIN Number Generation
def handle_min_verification(loan_id, borrower_ssn, coborrower_ssn):
    """
    1. Click MERS MIN box to generate
    2. Verify uniqueness on MERS website
    3. Search by SSN for borrower & co-borrower
    4. Upload PDF to Encompass under "MIN-SSN Summary"
    """
    pass

# Trust Handling (if approved for Trust)
def handle_trust(loan_id, trust_doc):
    """
    Extract from Trust document:
    - Trust Name, Trust Date/Year
    - Org State, Org Type ("An Inter Vivos Trust")
    - Beneficiary (if any)
    - Amended/Restated dates
    
    Format vesting: "Borrower name, Trustee of the TRUST NAME dated TRUST DATE"
    
    Add PTF: "TRUST Revocable Rider – Title Company to update Settlor(s) 
              information on Trust rider (Section – C) prior of recording."
    """
    pass
```

**State-Specific Vesting Rules:**
```python
STATE_VESTING_RULES = {
    "CA": {
        "married_nbs_not_on_title": "Married Man/Woman as his/her Sole and Separate property"
    },
    "NV": {
        "married_nbs_not_on_title": "Married Man/Woman as his/her Sole and Separate property"
    },
    "CO": {
        "marital_status_in_vesting": False  # Not required
    },
    "TX": {
        "joint_tenants_allowed": False,  # No "Joint Tenants" verbiage
        "attorney_handles": True
    }
}
```

#### Phase 2: Contacts & Vendors

**File Contacts to Update:**

| Contact Type | Source | Special Handling |
|--------------|--------|------------------|
| Lender | Static | AWM address, NMLS 14210 |
| Investor | Business Contact | If applicable |
| Title Insurance | Title Report | Copy to Settlement if same |
| Escrow Company | Wire Instructions | Bank ABA, Account, License IDs |
| Settlement Agent | File Contacts | Check "Add to CD Contact Info" = YES |
| Hazard Insurance | HOI Policy + Receipt | All fields |
| Flood Insurance | Flood Policy + Receipt | If in flood zone |
| Docs Prepared By | Static/Attorney | AWM (all) or BM&G/Cain & Kiel (TX) |

**Trustee by State:**
```python
STATE_TRUSTEE = {
    "NV": "same_as_title",
    "CA": "same_as_title",
    "AZ": "same_as_title",
    "WA": "same_as_title",
    "UT": "same_as_title",
    "OR": "same_as_title",
    "CO": "county_name_address",  # From Business Contacts >> No Category
    "TX": "Thomas E Black Jr.",   # From Business Contacts >> Attorney
    "FL": None,  # No trustee
    "MI": None   # No trustee
}
```

#### Phase 3: Property & Program

**Property Information:**

| Field | Source | Logic |
|-------|--------|-------|
| Property Type | Appraisal | SFR/PUD/Condo/MH |
| Occupancy | 1003 | Primary/Secondary/Investment |
| PUD/Condo Name | Title Report (Exhibit A) or Appraisal | |
| Flood Zone | Flood Cert | Cross-verify with Insurance & Appraisal |
| Parcel Number | Tax Summary/Cert/Title | |
| Legal Description | 1003 or "See Prelim" | |
| Endorsements | Property type + State | See tables below |

**Property Type Logic:**
```python
def determine_property_type(appraisal_type, hoa_fees, units):
    if units >= 2 and units <= 4:
        return "Detached"  # Even if Attached on Appraisal
    if appraisal_type == "SFR(Detached)" and hoa_fees > 0:
        return "PUD"
    if appraisal_type == "SFR(Detached)" and hoa_fees == 0:
        return "Detached"
    return appraisal_type
```

**Riders Required:**
```python
RIDERS = {
    "PUD": ["PUD Rider"],
    "Condo": ["Condo Rider"],
    "Investment": ["1-4 Family Rider"],
    "Secondary": ["Second Home Rider"],
    "ManufacturedHome": ["MH Rider", "Affixation of Affidavit"],
    "Trust": ["Revocable Trust Rider"],
    "203K": ["203K Rehabilitation Rider"],
    "SecondLien": ["Second Lien Rider"]
}
```

**Endorsements by State (Non-TX):**
```python
ENDORSEMENTS_STANDARD = {
    "SFR": ["8.1", "9.10-06"],
    "PUD": ["8.1", "9.10-06", "5.1-06", "115.4"],
    "Condo": ["8.1", "9.10-06", "4.1-06", "116.2"],
    "ARM_SFR": ["8.1", "9.10-06", "111.5"],
    "ARM_PUD": ["8.1", "9.10-06", "111.5", "5.1-06", "115.4"],
    "ARM_Condo": ["8.1", "9.10-06", "111.5", "4.1-06", "116.2"],
    "Manufacture": ["8.1", "9.10-06", "ALTA7"],
    "Manufacture_PUD": ["8.1", "9.10-06", "ALTA7", "5.1-06", "115.4"]
}
```

**Endorsements Texas:**
```python
ENDORSEMENTS_TX = {
    "SFR": ["T-19", "T-36"],
    "PUD": ["T-19", "T-36", "T-17"],
    "Condo": ["T-19", "T-36", "T-28"],
    "ARM_SFR": ["T-19", "T-36", "T-33"],
    "ARM_PUD": ["T-19", "T-36", "T-17", "T-33"],
    "ARM_Condo": ["T-19", "T-36", "T-28", "T-33"],
    "Manufacture": ["T-19", "T-36", "T-31", "T-31.1", "ALTA 7"],
    "Manufacture_PUD": ["T-19", "T-36", "T-17", "T-31", "T-31.1", "ALTA 7"],
    "HomeEquity": ["T-19", "T-36", "T-42", "T-42.1"],
    "HomeEquity_PUD": ["T-19", "T-36", "T-42", "T-42.1", "T-17"],
    "HomeEquity_Condo": ["T-19", "T-36", "T-42", "T-42.1", "T-28"],
    "HomeEquity_Manufacture": ["T-19", "T-36", "T-31", "T-42", "T-42.1", "T-31.1", "ALTA 7"],
    "HomeEquity_Manufacture_PUD": ["T-19", "T-36", "T-17", "T-31", "T-42", "T-42.1", "T-31.1", "ALTA 7"]
}
```

**Loan-Type Specific Handlers:**

```python
# FHA Handler
class FHAHandler:
    def process(self, doc_context):
        """
        Forms: HUD 92900ALT, FHA Management
        
        Fields:
        - FHA Case# from FHA Case Assignment
        - Case Assigned Date
        - SOA (Section of Act)
        - ADP Code (see ADP Code list, 796 for Buydown)
        - MIP Refund (Refinance) - use FUNDING month, must be positive
        
        Action: Click "GET MI" button before docs issued
        """
        pass

# VA Handler
class VAHandler:
    def process(self, doc_context):
        """
        Forms: VA Management, VA 26-1820
        
        Fields:
        - VA Case# from Case Assignment, Final Approval, 1003/92900A
        - Funding Fee Exempt from COE
        - VA Funding Fee (verify against chart)
        
        Funding Fee Chart (after April 7, 2023):
        Purchase <5% down: First=2.15%, Subsequent=3.30%
        Purchase 5-10% down: 1.50%
        Purchase >=10% down: 1.25%
        Cash-Out: First=2.15%, Subsequent=3.30%
        IRRRL: 0.50%
        
        VA 26-1820:
        - Section 6: Nearest Living Relative
        - Section 7: Loan Purpose
        - Section 12: Vested
        - Section 27B: Occupancy
        - Lines 20-21: Taxes & Insurance amounts
        """
        pass

# USDA Handler
class USDAHandler:
    def process(self, doc_context):
        """
        Form: USDA Management
        
        Fields:
        - Agency Case No (9 digits from Commitment)
        - Funding fee factor
        - Technology Fee: $25 (commitments on/after 1/1/2020)
          Disclosed in Sec-B, 0% tolerance, APR fee
          Paid to: AWM
        """
        pass
```

#### Phase 4: Financial Setup

**RegZ-CD Fields:**

| Field | Source | Validation |
|-------|--------|------------|
| Loan Program | Transaction | Per loan type |
| Disclosed APR | Last CD | Match |
| Purchase Price | Purchase Agreement | Match |
| Appraised Value | Appraisal Report | Match |
| 1st Payment Date | Note Date + 1 month | Calculate |
| CD Date Issued | Closing Date | Same |
| Application Date | Initial 1003 | |
| Rate Lock Date | Last LE | |
| Document Date | Closing Date | |

**Closing Date Validation:**
```python
def validate_closing_date(cd_ack_date, proposed_closing_date):
    """
    Closing date must be AFTER 3 business days of CD ACK
    Exclude: Sundays, Federal Holidays
    """
    pass
```

**Rescission Date (Refinance Primary Only):**
```python
def calculate_rescission_date(closing_date):
    """
    Rescission includes Mon-Sat (exclude Sunday & Federal holidays)
    Example: Closing 01/26 (Sat) → Rescission ends 01/30 (Wed)
    """
    pass
```

**Disbursement Date:**
```python
def calculate_disbursement_date(state, purpose, closing_date, rescission_end):
    """
    Dry State: Next business day after Closing
    Wet State: Same day as Closing
    Refinance Primary: Next business day after Rescission
    Business days = Mon-Fri only
    """
    pass
```

**Aggregate Escrow Calculation:**

| Field | Calculation |
|-------|-------------|
| 1st Payment Date | Closing + 1 month |
| Taxes Monthly | Tax Summary / 12 |
| Insurance Monthly | HOI / 12 |
| MI Monthly | If applicable |
| Cushion | 2 months (Tax+Ins), 0 (MI) |
| Starting Balance | Must be POSITIVE |
| Aggregate Adjustment | NEGATIVE or ZERO |

**State-Specific Tax Calculations:**
```python
STATE_TAX_CALC = {
    "NV": lambda sales_price: sales_price * 0.01 / 12,  # New Construction
    "AZ": lambda sales_price: sales_price * 0.01 / 12,  # New Construction
    "CA": lambda sales_price, tax_summary: max(sales_price * 0.0125 / 12, tax_summary / 12),
    "CO": "mill_levy_or_1_percent",  # Per UW Approval
    "other": lambda tax_cert, title: max(tax_cert, title)  # Higher of Tax Cert or Title
}
```

**Impound Rules:**
```python
IMPOUND_RULES = {
    "FHA": {"taxes": True, "insurance": True},  # Required
    "VA": {"taxes": True, "insurance": True},   # Required
    "Conventional": {"required_above_ltv": 80},  # Required if LTV > 80%
    "CA_Conventional": {"no_impound_up_to_ltv": 90},  # Optional up to 90%
    "Flood": {"always_impounded": True}  # Always, even if Impound = NO
}
```

**2015 Itemization - APR Fees:**
```python
APR_FEES = {
    "origination": True,
    "discount_points": True,
    "ufmip": True,
    "monthly_mi": True,
    "appraisal_r3_amc": True,
    "credit_report": False,
    "recording": False,
    "section_f": False,  # Except Prepaid Interest
    "section_g": False,  # Except Monthly MI
    "section_h": False
}
```

#### Phase 5: Closing Disclosure Pages

**CD Page 1:**
- Closing Information (Date, Agent, File#)
- Loan Information (Term, Purpose, Product)
- Property (Address verification - FINAL CALL is Docs Team)
- Loan Type (AWM Loan#, MIC#)
- Transaction Information (Borrower, Seller, Lender)
- Loan Terms (Amount, Rate, P&I)
- Projected Payments

**CD Page 2:**
- Section A-D: Loan Costs
- Section E-J: Other Costs

**CD Page 3:**
- Summaries of Transactions
- MIP Refund handling (FHA Refinance)
- Payoff requirements (full name, full account#)
- Cash to Close verification

**CD Page 4:**
- Loan Disclosures (Assumption, Demand, Negative Amort, Partial Payments)
- Escrow section
- AP Table (ARM only)

**CD Page 5:**
- APR verification (cannot increase >0.125% from COC CD)
- Contact Information
- Confirm Receipt (Signature type: "By Name")

**3-Day Wait Triggers:**
```python
THREE_DAY_WAIT_TRIGGERS = [
    "APR increase > 0.125%",
    "Product change (Jumbo↔Conforming, Conv↔Govt, FHA↔VA, Fixed↔ARM)",
    "Prepayment penalty added"
]
```

#### Tools Used by Docs Draw Core Agent
```python
# Core IO
read_fields(form_id, field_ids[])
write_fields(form_id, updates[])

# State Rules
get_state_endorsements(state, property_type, amortization, is_home_equity)
get_state_tax_calculation(state, is_new_construction, sales_price, tax_summary)
get_state_vesting_rules(state)
get_state_trustee(state, county)

# Loan-Type Handlers
process_fha(loan_id, doc_context)
process_va(loan_id, doc_context)
process_usda(loan_id, doc_context)
process_conventional(loan_id, doc_context)

# Insurance
calculate_dwelling_coverage(dwelling, erc_percent)
verify_mortgagee_clause(hoi_doc, lender, loan_number)
verify_flood_coverage(loan_amount, max_coverage=250000)

# Conditions
add_ptf_condition(loan_id, condition_text, assign_to_dept)
get_condition_sets(loan_type, purpose)

# External
verify_min_uniqueness(min_number, ssn_list)  # MERS
validate_property_address(address)  # USPS

# Logging
log_issue(loan_id, severity, message)
```

---

### 4.3 Audit & Compliance Agent

**Purpose**: Final verification, compliance checks, fee variance cures.

#### Responsibilities

1. **Cross-Section Validation**
   - Borrower names consistent across all forms
   - Loan amount matches everywhere
   - Interest rate matches everywhere
   - Property address matches (Tax Cert, USPS, County records)

2. **Fee Variance / Tolerance Cures**
   ```python
   def calculate_fee_variance(loan_id):
       """
       Compare LE vs Current Itemization (or Last CD vs Current if fees changed)
       
       0% Tolerance: Section A fees
       10% Tolerance: Section B fees (when using SPL provider)
       No Tolerance: Section C fees (borrower-shopped)
       
       Cure Calculation:
       1. Required Cure Amount (auto or manual)
       2. Applied Cure Amount (from Line 3)
       3. Apply to Lender Credit
       4. Apply to Principal (POC) if needed
       """
       pass
   ```

3. **Mavent Compliance**
   ```python
   def run_mavent(loan_id):
       """
       1. Click "Order" button
       2. Wait for report
       3. Check for failures
       4. If FAIL → Escalate to supervisor
       5. Must PASS before ordering docs
       
       Note: Mavent run AFTER docs issued
       """
       pass
   ```

4. **Hard Stop Detection**
   ```python
   HARD_STOPS = [
       "Loan Amount mismatch",
       "Interest Rate mismatch",
       "Monthly Hazard/Tax discrepancy with UW",
       "Insufficient Dwelling Coverage",
       "Approval Expiration passed",
       "Random fees in Section A",
       "Pre-Funding QC flagged",
       "ARM not approved by Lock Desk",
       "Non-QM not reviewed by Eric Gut"
   ]
   ```

5. **Decision**
   - All checks PASS → Mark ready for docs
   - Soft issues → Auto-add PTF conditions, proceed
   - Hard stops → Escalate, HALT

#### Tools Used
```python
read_fields(form_id, field_ids[])
run_compliance_check(loan_id, "Mavent")
get_compliance_results(loan_id)
calculate_fee_variance(loan_id)
apply_tolerance_cure(loan_id, cure_amount)
detect_hard_stops(loan_id)
log_issue(loan_id, severity, message)
```

---

### 4.4 Order & Distribution (Deterministic)

**Purpose**: Generate package, update milestone, distribute to parties.

#### Responsibilities

1. **Generate Package**
   ```python
   def order_docs(loan_id):
       """
       1. Go to RegZ-CD → Click "Order Docs"
       2. Order Type: "Closing"
       3. Clear Data Audits (related ones)
       4. Select "All Closing Docs"
       
       REMOVE from package:
       - Data Entry Proof Sheet (& Fees version)
       - Seller CD
       - NV Repayment Ability Worksheet (Nevada)
       - Final 1003 & 92900A (if without CTC)
       - Loan Modification Agreement Disclosure (ARM)
       - CHASE-prefixed docs (Chase investor)
       
       ADD to package:
       - Additional docs to be signed
       - POA (if applicable)
       - Attorney Package (Texas)
       - Evidence of Insurance
       - Invoices
       - Payoffs
       - Hold Harmless (if without CTC)
       """
       pass
   ```

2. **Update Milestone**
   ```python
   update_milestone(loan_id, "Docs Ordered – Finished", "DOCS Out on [Date]")
   ```

3. **Send Package**
   ```python
   def send_package(loan_id):
       """
       To: LO, Processor, Title/Escrow, docs@allwestern.com
       Subject: "Loan Docs: [AWM Loan#]_[Borrower Name]"
       
       Branch-specific:
       - Proctor/Plano/P Moore: Need LO/Processor approval FIRST
       - Patrick Moore: Must be copied on all emails
       
       State-specific:
       - Illinois: Email ILAPLD notification to LO
       """
       pass
   ```

---

## 5. Configuration Modules

### 5.1 State Rules Configuration

```python
STATE_CONFIG = {
    "TX": {
        "attorney_required": True,
        "attorneys": {
            "el_paso": {"name": "BM&G", "fee": 225},
            "proctor_plano_pmoore": {"name": "Cain & Kiel", "fee": 325}
        },
        "home_equity": {
            "12_day_notice": True,
            "deed_of_trust_form": "3044.1",
            "affidavit_form": "3185",
            "endorsements_extra": ["T-42", "T-42.1"]
        },
        "nbs_requirements": {
            "primary": "spouse_must_be_in_vesting",
            "secondary_investment": "not_required_if_sole_separate"
        },
        "manufactured_home": {
            "check_conversion": True,
            "endorsement": "T-31"
        },
        "vesting": {
            "joint_tenants": False
        }
    },
    "FL": {
        "credit_report_cap": 48.30,  # Florida Branch only
        "hhf_dpa_exemptions": ["transfer_tax", "documentary_stamp", "intangible_tax"]
    },
    "NV": {
        "remove_from_package": ["NV Repayment Ability Verification Worksheet"],
        "prosperity_branch": {
            "no_cushions": True,
            "no_sids_impounds": True
        }
    },
    "CA": {
        "tax_calc": "1.25% or tax_summary, whichever higher",
        "no_impound_ltv_max": 90  # Conventional only
    },
    "CO": {
        "marital_status_in_vesting": False,
        "trustee": "county",
        "tax_calc": "mill_levy_or_1_percent"
    },
    "IL": {
        "apld_notification": True,
        "apld_portal_instructions": True
    }
}
```

### 5.2 Branch Configuration

```python
BRANCH_CONFIG = {
    "prosperity": {
        "state": "NV",
        "rules": {
            "no_cushions": True,
            "no_sids_impounds": True
        }
    },
    "florida_branch": {
        "credit_report_cap": 48.30
    },
    "proctor_plano_pmoore": {
        "approval_required": ["LO", "Processor"],
        "patrick_moore_copy": True,
        "attorneys": ["PPDocs, Inc.", "Cain & Kiel"]
    },
    "el_paso": {
        "attorney": "BM&G",
        "attorney_fee": 225
    },
    "ray_lockery": {
        "credit_report_cap": {
            "before_2025_01_06": 195,
            "on_or_after_2025_01_06": 260
        },
        "los": ["Jonathan Hunter Ross", "William Denight", "Jennifer Mims", 
                "Ray Lockery", "Jeanne Leach", "Heather Leach", "Hunter Ross"]
    },
    "note_llc": {
        "identifier": "yellow_pipeline",
        "email_domain": "@notemortgage.com",
        "conventional": {"alt_lender": "NOTE LLC", "mers_org_id": "1017344"},
        "government": {"alt_lender": None, "mers_org_id": "1006909"},
        "replace_docs": ["Wire Fraud disclosure", "Funding Letter"]
    }
}
```

### 5.3 Investor Configuration

```python
INVESTOR_CONFIG = {
    "SGCP": {
        "investment_occupancy": {
            "prepayment_penalty": True,
            "use_calculator": True
        }
    },
    "CHASE": {
        "exclude_docs": ["CHASE-*"],
        "arm_assumption": "will_allow"
    },
    "Pentagon_Federal": {
        "4506c_line_5a": "TALX Corporation address"
    },
    "Bayview_Lakeview_DSCR": {
        "second_level_review": "closing_manager",
        "business_loan_rider": "bayview_format",
        "guarantor_signature": True
    },
    "ARC_DSCR": {
        "business_loan_rider_if_llc": True,
        "guaranty_agreement": True
    },
    "CHFA": {
        "hoi_deductible_max": 5000,
        "nbs_allowed": False,
        "second_dot_corner": "awm_mailing"
    },
    "TDHCA": {
        "hoi_deductible": "max(dwelling * 0.02, 2500)"
    },
    "THDA": {
        "hoi_deductible": "max(loan_amount * 0.01, 2500)"
    },
    "Metro_DPA_Lakeview": {
        "flood_cert_fee_payee": "Master Servicer",
        "tax_service_fee_payee": "Master Servicer"
    },
    "US_MRBP": {
        "hip_first_time": {"compliance_fee": 225},
        "hip_other": {"compliance_fee": 275},
        "hal": {"compliance_fee": 275},
        "govt_hip_tax_exempt_rider": False
    }
}
```

### 5.4 Loan-Type Configuration

```python
LOAN_TYPE_CONFIG = {
    "FHA": {
        "mip_refund_basis": "funding_date",  # Not note date
        "adp_code_buydown": 796,
        "streamline_no_appraisal_value": "original_property_value",
        "get_mi_button": True,
        "missing_92900a_page3": "add_ptf"
    },
    "VA": {
        "irrrl_fees": "financed_not_ptc",
        "cashout_form": "VA Cash Out Refinance Comparison",
        "max_cash_back_irrrl": 500,
        "attorney_fee_not_to_veteran": True,
        "credit_report_no_cap": True
    },
    "USDA": {
        "technology_fee": 25,
        "tech_fee_effective_date": "2020-01-01",
        "tech_fee_tolerance": "0%",
        "tech_fee_apr": True
    },
    "ARM": {
        "lock_desk_approval_required": True,
        "click_get_index": True,
        "apr_increase_threshold": 0.250,
        "remove_loan_mod_disclosure": True
    },
    "NonQM": {
        "eric_gut_review": True,
        "mavent_high_cost_expected": True,
        "investors": ["Acra", "SG Capital", "Onslow", "Verus", "Maxex", "Deephaven"],
        "atr_qm_eligibility": "Exempt"
    },
    "DPA": {
        "second_level_review": True,
        "screenshot_required": ["Investor Loan Program", "Reservation form"]
    },
    "PrivateMoney": {
        "non_mom": True,  # No MERS
        "balloon": True,
        "3_4_month_term": {"addendum": "Late Penalty"}
    },
    "Construction": {
        "max_draws": 6,
        "additional_draw_fee": 375,
        "completion_date": "closing + 12 months",
        "disclosures": ["AWM Construction Loan Program", "Addendum to Construction Note"]
    },
    "Buydown": {
        "agreement_required": True,
        "use_calculator": True,
        "funds_section": "H",
        "funds_payee": "AWM",
        "disclosures": ["Temporary Buydown", "Buydown Letter of Servicing"],
        "fha_adp_code": 796,
        "borrower_paid": {"eric_gut_review": True}
    }
}
```

---

## 6. Error Handling Matrix

| Issue Type | Severity | Action | Auto-Continue |
|------------|----------|--------|---------------|
| Missing non-critical doc | Soft | Add PTF condition | ✅ Yes |
| Address mismatch (minor) | Soft | Add PTF, flag for title | ✅ Yes |
| Name mismatch (minor) | Soft | Add PTF condition | ✅ Yes |
| Loan Amount mismatch | Hard | HALT, contact Team Lead | ❌ No |
| Interest Rate mismatch | Hard | HALT, contact Team Lead | ❌ No |
| Insurance coverage insufficient | Hard | HALT, request updated HOI | ❌ No |
| Approval expired | Hard | HALT, request UW update | ❌ No |
| Mavent FAIL | Hard | HALT, supervisor review | ❌ No |
| Pre-Funding QC flagged | Hard | HALT, wait for clearance | ❌ No |
| ARM Lock Desk not approved | Hard | HALT, wait for approval | ❌ No |
| Non-QM not reviewed | Hard | HALT, wait for Eric Gut | ❌ No |

---

## 7. Testing Scenarios

| Scenario | Loan Type | State | Complexity | Key Validations |
|----------|-----------|-------|------------|-----------------|
| Standard Purchase | Conventional | NV | Low | Basic flow |
| FHA Purchase | FHA | CA | Medium | Case#, MIP, ADP Code |
| VA Cash-Out | VA | TX | High | Funding fee, Attorney, Home Equity |
| USDA Purchase | USDA | CO | Medium | Tech fee, County trustee |
| ARM Refinance | Conventional ARM | FL | High | Lock Desk, Index, Credit cap |
| Trust Close | Conventional | NV | High | Trust handling, Rider |
| Non-QM DSCR | Non-QM | CA | High | Eric Gut, Investor rules |
| Construction | Construction | AZ | High | Draw schedule, Completion |
| DPA | FHA + DPA | TX | High | 2nd review, Investor, State |

---

## 8. Implementation Priority

### Phase 1 (MVP)
1. Docs Prep Agent (entry checks, doc download, basic extraction)
2. Docs Draw Core Agent (Phases 1-5 for Conventional only)
3. Basic Audit (field consistency, no Mavent yet)
4. Order & Distribution (deterministic)

### Phase 2
1. Add FHA/VA/USDA handlers
2. Add State Rules Engine (start with TX, CA, NV)
3. Add Mavent integration
4. Add Fee Variance/Cure logic

### Phase 3
1. Add Branch/Investor configurations
2. Add Trust handling
3. Add MIN/MERS verification
4. Add remaining state rules

### Phase 4
1. Add Non-QM, DPA, Construction, Buydown handlers
2. Add escalation workflows
3. Add approval routing
4. Performance optimization

---

*Document generated November 28, 2025*

