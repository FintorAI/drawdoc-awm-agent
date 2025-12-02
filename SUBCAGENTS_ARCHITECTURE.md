# Recommended Sub-Agent Architecture Based on 28 Steps

## Current Sub-Agents

1. **Preparation Agent** ✅
   - Downloads and extracts entities per file
   - Maps extracted fields to Encompass field IDs
   - Covers: Steps 2-3 (Document Download & Organization)

2. **Verification Agent** ✅
   - Checks if extracted files/fields are present
   - Verifies extracted values against Encompass
   - Covers: Cross-cutting verification across all steps

3. **Orderdocs Agent** ✅
   - Verifies if changes are implemented
   - Checks that all required fields are populated
   - Covers: Final validation before closing

---

## Recommended Additional Sub-Agents

Based on the 28 steps, here are the logical groupings for additional sub-agents:

### 1. **Borrower Setup Agent** (Steps 4-7)
**Purpose**: Verify and update all borrower-related information and loan originator details

**Responsibilities:**
- **Step 4**: Initial Setup & Pre-Verification
  - Verify POA (Power of Attorney) approval status
  - Verify Trust approval status
  - Check Pricing overage adjustments
- **Step 5**: Borrower Summary - Origination
  - Verify borrower information (name, SSN, DOB, phone, email, marital status)
  - Generate and verify MERS MIN number
  - Cross-reference with Final 1003, Approval Final, Driver's License, SSN Card
- **Step 6**: Borrower Information - Vesting
  - Verify and update borrower vesting information
  - Update AKA (Also Known As) names
  - Select correct Vesting Type
  - Verify Occupancy Intent
  - Update Trust information (if applicable)
  - Verify POA status
  - Handle state-specific vesting requirements (TX, CA, NV, CO)
- **Step 7**: 1003 Page-3 - Loan Originator Information
  - Verify Lender name
  - Verify Loan Officer information (Name, NMLS #, Email, Phone, State License)
  - Ensure NMLS compliance

**Key Tools Needed:**
- `verify_borrower_information`
- `generate_verify_mers_min`
- `update_vesting_information`
- `verify_loan_officer_credentials`
- `check_poa_trust_status`

---

### 2. **Contacts & Vendor Agent** (Steps 8-10)
**Purpose**: Verify and update all contact information for parties involved in closing

**Responsibilities:**
- **Step 8**: Closing Conditions
  - Set closing location information (Drawn City, Draw State, Closing County/State)
  - Add closing conditions based on loan type
  - Copy PTF conditions from UW Conditions
- **Step 9**: File Contacts
  - Verify/Update Lender contact information
  - Verify/Update Investor contact (if applicable)
  - Verify/Update Title Insurance Company
  - Verify/Update Escrow Company
  - Verify/Update Settlement Agent
  - Verify/Update Hazard Insurance Company
  - Verify/Update Flood Insurance Company (if applicable)
- **Step 10**: Closing Vendor Information
  - Verify auto-populated vendor information
  - Update Trustee information (state-specific)
  - Verify Docs Prepared By information

**Key Tools Needed:**
- `update_file_contacts`
- `verify_hazard_insurance_contact`
- `verify_flood_insurance_contact`
- `update_closing_conditions`
- `set_trustee_information` (state-specific logic)

---

### 3. **Property & Program Agent** (Steps 11-16)
**Purpose**: Handle property information and government program-specific forms

**Responsibilities:**
- **Step 11**: Property Information
  - Verify Property Type and ensure correct Riders are pulled
  - Verify Project Name (PUD/Condo)
  - Verify Special Endorsements
  - Update Parcel Number, Title Report Date, Legal Description
  - Handle Manufactured Housing details (if applicable)
- **Step 12**: HUD 92900ALT FHA Loan Transmittal (FHA Only)
  - Verify FHA Case Assignment number
  - Update FHA Case#, Case Assigned Date & SOA
- **Step 13**: FHA Management - Refi Authorization (FHA Only)
  - Verify Refinance Authorization
  - Verify MIP Refund amount
- **Step 14**: VA Management (VA Only)
  - Verify VA Agency Case#
  - Verify Funding Fee Exempt Status
  - Verify/Update VA Funding Fee amount
- **Step 15**: USDA Management (USDA Only)
  - Verify Agency Case No
  - Verify USDA-specific information
- **Step 16**: VA 26-1820 Loan Disbursement (VA Only)
  - Fill required sections on VA disbursement form

**Key Tools Needed:**
- `verify_property_information`
- `update_property_type_riders`
- `verify_fha_case_assignment`
- `verify_va_management_info`
- `verify_usda_management_info`
- `fill_va_disbursement_form`

**Program-Specific Handling:**
- Conditional execution based on loan type (FHA/VA/USDA/Conventional)
- Different forms and requirements per program

---

### 4. **Financial Setup Agent** (Steps 17-20)
**Purpose**: Configure all financial aspects including loan terms, escrow, and fee itemization

**Responsibilities:**
- **Step 17**: RegZ - CD (Closing Disclosure - Basic Setup)
  - Verify Loan Program & Plan Code
  - Verify Disclosure Information
  - Verify Loan Information (Purchase Price, Appraised Value, Dates)
  - Verify Rate Lock information
  - Set Closing Date and related dates (Rescission, Disbursement)
  - Verify Loan Terms and Product details
  - Verify Mortgage Insurance section
- **Step 18**: Tools >> UW Summary
  - Identify LTV & CLTV % of the loan
  - Check for Subordinate Financing
- **Step 19**: Aggregate Escrow Account
  - Set Servicer information
  - Configure escrow setup (Taxes, Insurance, MI)
  - Set up cushion months and due dates
  - Verify Starting/Initial Balance
  - Handle state-specific tax calculations
- **Step 20**: 2015 Itemization
  - Verify Loan Program & Closing Cost Program
  - Itemize all fees (Section 800, 900, etc.)
  - Verify amounts in Borrower or Seller Column
  - Verify PAC (Paid at Closing) vs POC (Paid Outside Closing)
  - Verify fee categorization (APR vs Non-APR)

**Key Tools Needed:**
- `setup_closing_disclosure_basic`
- `verify_loan_terms`
- `calculate_set_dates` (Closing, Rescission, Disbursement, 1st Payment)
- `setup_aggregate_escrow`
- `itemize_fees`
- `verify_fee_categorization`

---

### 5. **Closing Disclosure Agent** (Steps 21-25)
**Purpose**: Complete all pages of the Closing Disclosure and handle fee variances

**Responsibilities:**
- **Step 21**: Fee Variance
  - Identify Required Cure amount
  - Update Applied Cure Amount
  - Apply cures to Lender Credit or Principal
- **Step 22**: Closing Disclosure - 1
  - Verify Disclosure Information
  - Handle COC CD requirements
  - Understand 3-day waiting period rules
  - Verify Closing Information, Loan Information, Property Information
- **Step 23**: Closing Disclosure - 2
  - Verify Loan Costs (Sections A, B, C, D)
  - Verify Other Costs (Sections E, F, G, H, I, J)
- **Step 24**: Closing Disclosure - 3
  - Verify Summaries of Transactions
  - Add Principal reduction (if needed)
  - Add Additional debts/payoffs (if needed)
  - Handle MIP Refund in Refinance
  - Verify Cash to Close calculations
- **Step 25**: Closing Disclosure - 4
  - Verify Loan Disclosures (Assumption, Demand Feature, Late Payment, etc.)
  - Verify Escrow section
  - Verify Adjustable Payment Table (if ARM)

**Key Tools Needed:**
- `calculate_fee_variance`
- `apply_tolerance_cures`
- `verify_closing_disclosure_page_1`
- `verify_closing_disclosure_page_2`
- `verify_closing_disclosure_page_3`
- `verify_closing_disclosure_page_4`
- `add_payoffs_adjustments`

---

### 6. **Compliance & Distribution Agent** (Steps 26-28)
**Purpose**: Final compliance review, milestone completion, and document distribution

**Responsibilities:**
- **Step 26**: Mavent/Compliance Review Report
  - Run Mavent compliance report
  - Check for any failures
  - Escalate issues to supervisor/team lead
  - Wait for approval before proceeding
- **Step 27**: Complete Milestone
  - Mark "Finished" under Milestone Status "Docs Ordered"
  - Update milestone comments with "DOCS Out on [Date]"
  - Ensure no pending queries or Mavent issues
  - Escalate any blocking errors
- **Step 28**: Send Final DOCS
  - Send Closing Package to all parties:
    - Escrow/Title Company
    - Loan Officer (LO)
    - Processors
  - Verify all documents are properly formatted
  - Verify all required attachments included
  - Confirm receipt with all parties

**Key Tools Needed:**
- `run_mavent_compliance_review`
- `check_compliance_failures`
- `complete_docs_ordered_milestone`
- `send_final_documents`
- `verify_document_completeness`
- `notify_parties`

---

## Summary: Complete Agent Architecture

### Current Agents (3):
1. ✅ **Preparation Agent** - Document download & extraction
2. ✅ **Verification Agent** - Cross-cutting verification
3. ✅ **Orderdocs Agent** - Final field validation

### Recommended New Agents (6):
4. 🔨 **Borrower Setup Agent** - Steps 4-7
5. 🔨 **Contacts & Vendor Agent** - Steps 8-10
6. 🔨 **Property & Program Agent** - Steps 11-16
7. 🔨 **Financial Setup Agent** - Steps 17-20
8. 🔨 **Closing Disclosure Agent** - Steps 21-25
9. 🔨 **Compliance & Distribution Agent** - Steps 26-28

---

## Execution Flow

```
┌─────────────────────────────────────────┐
│         Orchestrator Agent              │
└─────────────────────────────────────────┘
              │
              ├─► 1. Preparation Agent (Steps 2-3)
              │      Download & Extract
              │
              ├─► 2. Borrower Setup Agent (Steps 4-7)
              │      Borrower Info, Vesting, LO Info
              │
              ├─► 3. Contacts & Vendor Agent (Steps 8-10)
              │      File Contacts, Vendors, Trustee
              │
              ├─► 4. Property & Program Agent (Steps 11-16)
              │      Property Info, FHA/VA/USDA Forms
              │
              ├─► 5. Financial Setup Agent (Steps 17-20)
              │      Loan Terms, Escrow, Fee Itemization
              │
              ├─► 6. Closing Disclosure Agent (Steps 21-25)
              │      All CD Pages, Fee Variance
              │
              ├─► 7. Verification Agent (Cross-cutting)
              │      Verify all changes
              │
              ├─► 8. Compliance & Distribution Agent (Steps 26-28)
              │      Mavent Review, Milestone, Send Docs
              │
              └─► 9. Orderdocs Agent (Final Check)
                     Verify all fields populated
```

---

## Priority Order for Implementation

### Phase 1: Core Data Entry (High Priority)
1. **Borrower Setup Agent** - Critical for loan identity and borrower info
2. **Contacts & Vendor Agent** - Essential for closing coordination
3. **Property & Program Agent** - Required for property and program setup

### Phase 2: Financial Configuration (High Priority)
4. **Financial Setup Agent** - Core to loan terms and escrow

### Phase 3: Closing Documents (Medium Priority)
5. **Closing Disclosure Agent** - Required for closing but can be partially manual

### Phase 4: Final Steps (Lower Priority - Can be Manual)
6. **Compliance & Distribution Agent** - Currently manual steps, can be automated later

---

## Key Considerations

1. **Dependencies**: Some agents depend on outputs from previous agents
   - Borrower Setup needs Preparation Agent output
   - Financial Setup needs Borrower and Property agents
   - Closing Disclosure needs Financial Setup output

2. **Conditional Logic**: Property & Program Agent needs conditional execution
   - FHA forms (Steps 12-13) only for FHA loans
   - VA forms (Steps 14-16) only for VA loans
   - USDA forms (Step 15) only for USDA loans

3. **State-Specific Rules**: Several agents need state-specific handling
   - Borrower Setup: Vesting rules (TX, CA, NV, CO)
   - Contacts & Vendor: Trustee selection varies by state
   - Financial Setup: Tax calculations vary by state

4. **Complex Calculations**: Financial Setup and Closing Disclosure agents need
   - Date calculations (3-day waiting, rescission, disbursement)
   - Fee variance calculations
   - Escrow setup calculations
   - Cash to close calculations

5. **External Systems**: Some agents need to interact with external systems
   - MERS website for MIN verification
   - Mavent for compliance review
   - Email/notification systems for distribution

---

## Integration Points

Each agent should:
- Read from Encompass (current loan state)
- Read from Preparation Agent output (extracted field values)
- Write to Encompass (updates/changes)
- Output structured results for next agent
- Support dry-run mode for safety
- Provide detailed logging

---

**Generated**: Based on SOP Steps 1-28 Analysis
**Date**: 2024

---

## Fields and Documents Requirements by Agent

Below is a detailed breakdown of all fields and documents required for each sub-agent.

### 1. Preparation Agent ✅

**Fields Required:**
- Extracted entities per file
- Encompass field IDs for mapping
- Document metadata (file names, types, locations)

**Documents to Process:**
- All loan documents from download source
- Document organization metadata

---

### 2. Verification Agent ✅

**Fields Required:**
- All extracted field values from Preparation Agent
- Corresponding Encompass field values
- Field presence flags
- Field value match status

**Documents to Process:**
- Preparation Agent output (extracted values)
- Encompass loan data snapshot
- Verification rules/mappings

---

### 3. Orderdocs Agent ✅

**Fields Required:**
- All required field population status
- Implementation verification flags
- Field completeness indicators

**Documents to Process:**
- Final loan state from Encompass
- Required fields checklist
- Previous agent outputs

---

### 4. Borrower Setup Agent (Steps 4-7)

**Fields Required:**

**Step 4 - Initial Setup & Pre-Verification:**
- POA (Power of Attorney) approval status
- Trust approval status
- Pricing overage adjustments

**Step 5 - Borrower Summary - Origination:**
- Borrower name(s)
- Social Security Number(s)
- Date of birth
- Phone number(s)
- Email address(es)
- Marital status
- MERS MIN number

**Step 6 - Borrower Information - Vesting:**
- Borrower vesting information
- AKA (Also Known As) names
- Vesting type
- Occupancy intent
- Trust information (if applicable)
- POA status
- State-specific vesting requirements (TX, CA, NV, CO)

**Step 7 - Loan Originator Information:**
- Lender name
- Loan officer name
- Loan officer NMLS number
- Loan officer email
- Loan officer phone
- Loan officer state license number

**Documents to Process:**
- Final 1003 (Uniform Residential Loan Application)
- Approval Final document
- Driver's License
- SSN Card
- Trust documents (if applicable)
- POA documents (if applicable)
- State-specific vesting documentation

---

### 5. Contacts & Vendor Agent (Steps 8-10)

**Fields Required:**

**Step 8 - Closing Conditions:**
- Drawn city
- Draw state
- Closing county
- Closing state
- Loan type
- PTF conditions from UW Conditions

**Step 9 - File Contacts:**
- Lender contact information (name, address, phone, email)
- Investor contact information (if applicable)
- Title insurance company details
- Escrow company details
- Settlement agent information
- Hazard insurance company details
- Flood insurance company details (if applicable)

**Step 10 - Closing Vendor Information:**
- Vendor auto-populated data
- Trustee information (state-specific)
- "Docs Prepared By" information

**Documents to Process:**
- UW Conditions document
- Contact information records
- Insurance policies (Hazard, Flood)
- Title insurance documentation
- Escrow company records
- State-specific trustee lists

---

### 6. Property & Program Agent (Steps 11-16)

**Fields Required:**

**Step 11 - Property Information:**
- Property type
- Riders selection
- Project name (PUD/Condo)
- Special endorsements
- Parcel number
- Title report date
- Legal description
- Manufactured housing details (if applicable)

**Step 12 - HUD 92900ALT FHA Loan Transmittal (FHA Only):**
- FHA case assignment number
- FHA case number
- Case assigned date
- SOA (Statement of Account)

**Step 13 - FHA Management - Refi Authorization (FHA Only):**
- Refinance authorization status
- MIP refund amount

**Step 14 - VA Management (VA Only):**
- VA agency case number
- Funding fee exempt status
- VA funding fee amount

**Step 15 - USDA Management (USDA Only):**
- Agency case number
- USDA-specific information fields

**Step 16 - VA 26-1820 Loan Disbursement (VA Only):**
- Required sections for VA disbursement form

**Documents to Process:**
- Title report
- Property appraisal
- Legal description documents
- Manufactured housing documentation (if applicable)
- FHA Case Assignment letter (FHA loans)
- FHA MIP documentation (FHA refi)
- VA Certificate of Eligibility (VA loans)
- VA funding fee documentation (VA loans)
- USDA eligibility documentation (USDA loans)
- VA 26-1820 form (VA loans)
- PUD/Condo project documentation

---

### 7. Financial Setup Agent (Steps 17-20)

**Fields Required:**

**Step 17 - RegZ - CD (Closing Disclosure Basic Setup):**
- Loan program
- Plan code
- Disclosure information
- Purchase price
- Appraised value
- Loan dates (application, rate lock, etc.)
- Rate lock information
- Closing date
- Rescission date
- Disbursement date
- First payment date
- Loan terms (principal, interest rate, term)
- Product details
- Mortgage insurance amount
- Mortgage insurance premium

**Step 18 - UW Summary:**
- LTV (Loan to Value) percentage
- CLTV (Combined Loan to Value) percentage
- Subordinate financing information

**Step 19 - Aggregate Escrow Account:**
- Servicer information
- Tax escrow setup
- Insurance escrow setup
- MI (Mortgage Insurance) escrow setup
- Cushion months
- Due dates (taxes, insurance, MI)
- Starting balance
- Initial balance
- State-specific tax calculations

**Step 20 - 2015 Itemization:**
- Loan program
- Closing cost program
- Section 800 fees
- Section 900 fees
- All other fee sections
- Borrower column amounts
- Seller column amounts
- PAC (Paid at Closing) flags
- POC (Paid Outside Closing) flags
- APR vs Non-APR categorization

**Documents to Process:**
- Rate lock confirmation
- Appraisal report
- Mortgage insurance certificate
- UW Summary report
- Tax bill/assessment
- Insurance policy declarations
- Servicer information
- Fee worksheets/estimates
- Lender fee schedules
- Third-party fee quotes

---

### 8. Closing Disclosure Agent (Steps 21-25)

**Fields Required:**

**Step 21 - Fee Variance:**
- Required cure amount
- Applied cure amount
- Lender credit adjustments
- Principal adjustments

**Step 22 - Closing Disclosure Page 1:**
- Disclosure information
- COC (Change of Circumstance) CD requirements
- 3-day waiting period tracking
- Closing information
- Loan information summary
- Property information summary

**Step 23 - Closing Disclosure Page 2:**
- Section A - Loan Costs: Origination Charges
- Section B - Loan Costs: Services Borrower Did Not Shop For
- Section C - Loan Costs: Services Borrower Did Shop For
- Section D - Loan Costs: Total Loan Costs
- Section E - Other Costs: Taxes and Government Fees
- Section F - Other Costs: Prepaids
- Section G - Other Costs: Initial Escrow Payment
- Section H - Other Costs: Other
- Section I - Other Costs: Total Other Costs
- Section J - Total Closing Costs

**Step 24 - Closing Disclosure Page 3:**
- Transaction summaries (borrower and seller)
- Principal reduction amount (if needed)
- Additional debts/payoffs
- MIP refund (for refinance)
- Cash to close calculations

**Step 25 - Closing Disclosure Page 4:**
- Assumption clause
- Demand feature
- Late payment policy
- Negative amortization
- Partial payments
- Security interest
- Escrow account status
- Escrow property costs breakdown
- Adjustable payment table (if ARM)

**Documents to Process:**
- Initial Closing Disclosure
- Previous CDs (for COC tracking)
- Fee variance worksheets
- Lender credit documentation
- Payoff statements
- MIP refund documentation (refinance)
- ARM adjustment documentation (if ARM)
- All itemized fees and cost documentation

---

### 9. Compliance & Distribution Agent (Steps 26-28)

**Fields Required:**

**Step 26 - Mavent/Compliance Review:**
- Mavent compliance report results
- Compliance failure flags
- Issue escalation status

**Step 27 - Complete Milestone:**
- Milestone status ("Docs Ordered")
- Milestone completion date
- Milestone comments
- Pending query flags
- Blocking error flags

**Step 28 - Send Final DOCS:**
- Recipient list (Escrow/Title, LO, Processors)
- Document formatting verification
- Required attachments checklist
- Receipt confirmation status

**Documents to Process:**
- Complete loan package
- Mavent compliance report
- Milestone tracking system data
- Final closing package (all documents)
- Distribution list
- Receipt confirmations
- Quality control checklist

---

## Cross-Cutting Requirements

**All Agents Need Access To:**
- Encompass loan data (read)
- Encompass loan data (write permissions)
- Preparation Agent output
- Previous agent outputs in the chain
- Loan type/program identifier
- State identifier (for state-specific rules)

**All Agents Should Output:**
- Structured results (JSON/dict format)
- Verification status for each field
- Error/warning messages
- Processing timestamp
- Agent version/identifier
- Dry-run simulation results (if in dry-run mode)

---

## Conditional Processing by Loan Type

**FHA Loans:**
- Property & Program Agent: Steps 12-13 required
- All FHA-specific fields and documents

**VA Loans:**
- Property & Program Agent: Steps 14, 16 required
- All VA-specific fields and documents

**USDA Loans:**
- Property & Program Agent: Step 15 required
- All USDA-specific fields and documents

**Conventional Loans:**
- Property & Program Agent: Step 11 only
- Skip program-specific steps (12-16)

---

## State-Specific Processing

**Agents Requiring State Logic:**
1. **Borrower Setup Agent**: Vesting rules for TX, CA, NV, CO
2. **Contacts & Vendor Agent**: Trustee selection varies by state
3. **Financial Setup Agent**: Tax calculations vary by state

**State Data Required:**
- State code
- State-specific vesting rules
- State-specific trustee lists
- State-specific tax calculation rules


