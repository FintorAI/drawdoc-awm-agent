# Sub-Agent Fields, Documents, and Encompass Field Mappings

This document provides a comprehensive breakdown of all fields and documents required for each sub-agent, including specific Encompass Field IDs from the master field data.

---

## 1. Preparation Agent ✅

### Fields Required:
| Field Description | Encompass Field ID |
|---|---|
| Extracted entities per file | N/A - Output from document extraction |
| Encompass field IDs for mapping | N/A - Metadata |
| Document metadata (file names, types, locations) | N/A - File system data |

### Documents to Process:
- All loan documents from download source
- Document organization metadata

---

## 2. Verification Agent ✅

### Fields Required:
| Field Description | Encompass Field ID |
|---|---|
| All extracted field values from Preparation Agent | N/A - From Prep Agent |
| Corresponding Encompass field values | Various (all below) |
| Field presence flags | N/A - Computed |
| Field value match status | N/A - Computed |

### Documents to Process:
- Preparation Agent output (extracted values)
- Encompass loan data snapshot
| Verification rules/mappings

---

## 3. Orderdocs Agent ✅

### Fields Required:
| Field Description | Encompass Field ID |
|---|---|
| All required field population status | N/A - Computed |
| Implementation verification flags | N/A - Computed |
| Field completeness indicators | N/A - Computed |

### Documents to Process:
- Final loan state from Encompass
- Required fields checklist
- Previous agent outputs

---

## 4. Borrower Setup Agent (Steps 4-7)

### Step 4 - Initial Setup & Pre-Verification

| Field Description | Encompass Field ID |
|---|---|
| POA (Power of Attorney) approval status | (Custom field - check with business) |
| Trust approval status | (Custom field - check with business) |
| Pricing overage adjustments | (Custom field - check with business) |

### Step 5 - Borrower Summary - Origination

| Field Description | Encompass Field ID |
|---|---|
| Borrower First Name | 4000 |
| Borrower Middle Name | 4001 |
| Borrower Last Name | 4002 |
| Borrower Suffix Name | 4003 |
| Borrower First/Middle Name | 36 |
| Borrower Last Name/Suffix | 37 |
| Co-Borrower First Name | 4004 |
| Co-Borrower Middle Name | 4005 |
| Co-Borrower Last Name | 4006 |
| Co-Borrower Suffix Name | 4007 |
| Co-Borrower First/Middle Name | 68 |
| Co-Borrower Last Name/Suffix | 69 |
| Borrower SSN | 65 |
| Co-Borrower SSN | 97 |
| Borrower DOB (Date of Birth) | (Check standard field) |
| Co-Borrower DOB | (Check standard field) |
| Borrower Home Phone | 66 |
| Co-Borrower Home Phone | 98 |
| Borrower Business Phone | FE0216 |
| Co-Borrower Business Phone | FE0217 |
| Borrower Email | (Check standard field) |
| Borrower Work Email | 1178 |
| Borrower Marital Status | (Check standard field) |
| MERS MIN Number | 1051 |

### Step 6 - Borrower Information - Vesting

| Field Description | Encompass Field ID |
|---|---|
| Borrower Vesting Type | 4008 |
| Borrower Vesting Type (Co-Mortgagor Pair: 2) | 4008#2 |
| Borrower Vesting Borr 1 Corp/Trust Name | 1859 |
| Borrower Vesting Borr 1 Org State | 1860 |
| Borrower Vesting Borr 1 Org Type | 1861 |
| Borrower Vesting Borr 1 Org Tax ID | 1862 |
| Borrower Vesting Borr Beneficiaries | 2970 |
| Borrower Vesting Borr Final Vesting to Read | 1867 |
| Borrower Ownership Interest Type | FE0155 |
| Borrower Ownership Interest Type (Co-Mortgagor Pair: 2) | FE0155#2 |
| Occupancy Intent / Occupancy Type | 3335 |
| Subject Property Manner Held | 33 |
| AKA names | (Typically stored in custom fields or name variations) |
| State-specific vesting requirements | (State-dependent logic) |

### Step 7 - Loan Originator Information (1003 Page 3)

| Field Description | Encompass Field ID |
|---|---|
| Lender Name | 1264 |
| Lender Phone | 1262 |
| Loan Officer | 317 |
| Loan Officer NMLS ID | 3238 |
| NMLS Loan Originator ID (HMDA) | HMDA.X86 |
| Loan Officer Email | (Check user/contact table) |
| Loan Officer Phone | (Check user/contact table) |
| Loan Officer State License | (Check user/contact table) |
| Broker Lender Name | 315 |
| Broker Lender Address | 319 |
| Broker Lender City | 313 |
| Broker Lender State | 321 |
| Broker Lender Zip | 323 |
| Broker Lender Phone | 324 |
| State Disc - Lender's NMLS Ref # | 3244 |

### Documents to Process:
- Final 1003 (Uniform Residential Loan Application)
- Approval Final document
- Driver's License
- SSN Card
- Trust documents (if applicable)
- POA documents (if applicable)
- State-specific vesting documentation

---

## 5. Contacts & Vendor Agent (Steps 8-10)

### Step 8 - Closing Conditions

| Field Description | Encompass Field ID |
|---|---|
| Subject Property City | 12 |
| Subject Property State | 14 |
| Subject Property County | 13 |
| Closing Date | 748 |
| Est Closing Date | 763 |
| Loan Type | 1172 |
| Loan Program | 1401 |
| PTF conditions from UW Conditions | (Conditions system) |

### Step 9 - File Contacts

| Field Description | Encompass Field ID |
|---|---|
| **Lender Contact Information:** | |
| Lender Name | 1264 |
| Lender Phone | 1262 |
| **Investor Contact Information:** | |
| Investor Name | VEND.X263 |
| **Title Insurance Company:** | |
| Title Insurance Company Name | 411 |
| Title Co Contact | 416 |
| Title Co Phone | 417 |
| **Escrow Company:** | |
| Escrow Company Name | 610 |
| Escrow Co Contact | 611 |
| Escrow Co Phone | 615 |
| **Settlement Agent:** | |
| Doc Signing Company Name | 395 |
| Doc Signing Co Contact Name | VEND.X195 |
| Doc Signing Co Phone | VEND.X196 |
| **Hazard Insurance Company:** | |
| Hazard Insurance Company Name | L252 |
| Hazard Ins Co Phone | VEND.X163 |
| Hazard Ins Contact Zip | VEND.X162 |
| **Flood Insurance Company:** | |
| Flood Insurance Company Name | 1500 |
| Flood Ins Co Contact | VEND.X13 |
| Flood Ins Co Phone | VEND.X19 |

### Step 10 - Closing Vendor Information

| Field Description | Encompass Field ID |
|---|---|
| Appraisal Company Name | 617 |
| Appraisal Co Contact | 618 |
| Appraisal Co Phone | 622 |
| Credit Company Name | 624 |
| Credit Report Agency Phone | 629 |
| Mortgage Insurance Company Name | L248 |
| Mtg Ins Co Contact Name | 707 |
| Mtg Ins Co Phone | 711 |
| Underwriter Name | REGZGFE.X8 |
| Underwriter Contact | 984 |
| Underwriter Phone | 1410 |
| Trustee information (state-specific) | (Varies by state) |
| Docs Prepared By information | (Custom field) |

### Documents to Process:
- UW Conditions document
- Contact information records
- Insurance policies (Hazard, Flood)
- Title insurance documentation
- Escrow company records
- State-specific trustee lists

---

## 6. Property & Program Agent (Steps 11-16)

### Step 11 - Property Information

| Field Description | Encompass Field ID |
|---|---|
| Subject Property Type | 1041, 1553 |
| Subject Property Type (HMDA) | HMDA.X11 |
| Subject Property Address | 11 |
| Subject Property Street 2 | 3893 |
| Subject Property City | 12 |
| Subject Property State | 14 |
| Subject Property Zip | 15 |
| Subject Property County | 13 |
| Subject Property # Units | 16 |
| Subject Property Year Built | 18 |
| Subject Property Legal Desc1 | 17 |
| Subject Property Purchase Price | 136 |
| Appraised Value | 356 |
| Subject Property Est Value | 1821 |
| Subject Property Value For LTV | 358 |
| Subject Property Census Tract | 700 |
| Subject Property MSA # | 699 |
| Subject Property County Code | 1396 |
| Subject Property State Code | 1395 |
| Project Name (PUD/Condo) | (Check property fields) |
| Parcel Number | (Check property fields) |
| Title Report Date | (Check title fields) |
| Manufactured Housing details | (If applicable) |

### Step 12 - HUD 92900ALT FHA Loan Transmittal (FHA Only)

| Field Description | Encompass Field ID |
|---|---|
| Agency Case # | 1040 |
| FHA Case Assignment number | (Check FHA fields) |
| FHA Case # | (Check FHA fields) |
| Case Assigned Date | (Check FHA fields) |
| SOA (Statement of Account) | (Check FHA fields) |

### Step 13 - FHA Management - Refi Authorization (FHA Only)

| Field Description | Encompass Field ID |
|---|---|
| Refinance Authorization status | (Check FHA fields) |
| MIP Refund amount | (Check FHA fields) |

### Step 14 - VA Management (VA Only)

| Field Description | Encompass Field ID |
|---|---|
| VA Agency Case # | (Check VA fields) |
| VA Veteran Loan Code | 958 |
| Funding Fee Exempt Status | (Check VA fields) |
| VA Funding Fee amount | (Check VA fields) |
| VA Loan Summ Credit Score | VASUMM.X23 |
| VA Loan Summ Total Disc Points Chrgd Amt | VASUMM.X45 |
| VA Loan Summ 1st Time Use VA Loan Program | VASUMM.X49 |
| VA Management Tool - Cash-Out Refinance Type | VASUMM.X125 |

### Step 15 - USDA Management (USDA Only)

| Field Description | Encompass Field ID |
|---|---|
| Agency Case No | (Check USDA fields) |
| USDA-specific information fields | (Check USDA fields) |

### Step 16 - VA 26-1820 Loan Disbursement (VA Only)

| Field Description | Encompass Field ID |
|---|---|
| Required sections for VA disbursement form | (Check VA form fields) |

### Documents to Process:
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

## 7. Financial Setup Agent (Steps 17-20)

### Step 17 - RegZ - CD (Closing Disclosure Basic Setup)

| Field Description | Encompass Field ID |
|---|---|
| Loan Program | 1401 |
| Loan Type | 1172 |
| Amortization Type | 608 |
| Loan Term | 4 |
| Loan Amount | 1109 |
| Total Loan Amount | 2 |
| Purchase Price | 136 |
| Appraised Value | 356 |
| Note Rate | 3 |
| Qual Rate | 1014 |
| Lock Expiration Date | 762 |
| Closing Date | 748 |
| Est Closing Date | 763 |
| Date Prepared | 363 |
| Loan Created Date | 2025 |
| Mortgage Loan Commitment Date | 3094 |
| Commitment Expiration Date | 4529 |
| Rate Lock Validation Status | 4788 |
| Disclosure Information | (Various disclosure fields) |
| Product Details | (Product-specific fields) |
| Mortgage Insurance Amount | (MI fields) |
| Mortgage Insurance Premium | (MI fields) |
| Insurance Mtg Ins Pymt 1 | 1766 |
| Insurance Mtg Ins Pymt 2 | 1770 |

### Step 18 - UW Summary

| Field Description | Encompass Field ID |
|---|---|
| LTV (Loan to Value) percentage | (Calculated field) |
| CLTV (Combined Loan to Value) percentage | (Calculated field) |
| HMDA CLTV | HMDA.X98 |
| Down Payment Amount | 1335 |
| Down Payment % | 1771 |
| Subordinate Financing | (Check sub financing fields) |
| Sub Fin Additional Mtgs | 1732 |
| Sub Fin Second Mtg Loan Amt | 428 |

### Step 19 - Aggregate Escrow Account

| Field Description | Encompass Field ID |
|---|---|
| Servicer information | (Check servicer fields) |
| Tax escrow setup | (Escrow fields) |
| Insurance escrow setup | (Escrow fields) |
| MI (Mortgage Insurance) escrow setup | (Escrow fields) |
| Impound Types | 2294 |
| Impounds Waived | 2293 |
| Insurance Mtg Ins Cancel at % | 1205 |
| Insurance Mtg Ins Mnths Prepaid | 2978 |
| Insurance Mtg Ins Mos Prepaid | 1209 |
| Insurance Mtg Ins Period 1 | 1198 |
| Insurance Mtg Ins Period 2 | 1200 |
| Insurance Mtg Ins Periodic Factor 1 | 1199 |
| Insurance Mtg Ins Periodic Factor 2 | 1201 |
| Cushion months | (Escrow calculation) |
| Due dates (taxes, insurance, MI) | (Escrow fields) |
| Starting/Initial balance | (Escrow fields) |

### Step 20 - 2015 Itemization

| Field Description | Encompass Field ID |
|---|---|
| Loan Program | 1401 |
| Closing Cost Program | (Fee configuration) |
| Section 800 fees | Various NEWHUD2.X fields |
| Section 900 fees | Various NEWHUD2.X fields |
| Borrower PAC (Paid at Closing) amounts | Various NEWHUD2.X fields |
| Borrower POC (Paid Outside Closing) amounts | Various NEWHUD2.X fields |
| Seller PAC amounts | Various NEWHUD2.X fields |
| Seller POC amounts | Various NEWHUD2.X fields |
| APR vs Non-APR categorization | Various APR indicator fields |
| Fees Line 801 (Origination Fee) | 454, NEWHUD.X fields |
| Fees Line 802 (Loan Discount) | 1061 |
| Fee Details - Line 701-1320 | NEWHUD2.X209-4598 |

### Documents to Process:
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

## 8. Closing Disclosure Agent (Steps 21-25)

### Step 21 - Fee Variance

| Field Description | Encompass Field ID |
|---|---|
| Required cure amount | (Calculated from tolerance analysis) |
| Applied cure amount | (Fee variance fields) |
| Lender credit adjustments | 4794 (Non-Specific Lender Credit) |
| Principal adjustments | (Adjustment fields) |

### Step 22 - Closing Disclosure Page 1

| Field Description | Encompass Field ID |
|---|---|
| Disclosure information | CD1.X fields |
| COC CD Changed Circumstance Checkbox | CD1.X61 |
| COC CD Changed Circumstance Rcvd Date | CD1.X62 |
| 3-day waiting period tracking | (Calculated from disclosure dates) |
| Closing information | CD1.X fields |
| Loan information summary | CD1.X fields |
| Property information summary | CD1.X fields |

### Step 23 - Closing Disclosure Page 2

| Field Description | Encompass Field ID |
|---|---|
| CD Last Disclosed Loan Costs | CD2.XLDLC |
| CD Last Disclosed Other Costs | CD2.XLDOC |
| CD Last Disclosed Lender Credits | CD2.XLDLCR |
| Loan Costs (Section A-D) | CD2.X fields |
| Section A - Loan Costs: Origination Charges | CD2.XSTA (subtotal) |
| Section B - Services Borrower Did Not Shop For | CD2.XSTB (subtotal) |
| Section C - Services Borrower Did Shop For | CD2.XSTC (subtotal) |
| Section D - Total Loan Costs | CD2.XSTD |
| Other Costs (Section E-J) | CD2.X fields |
| Total Closing Costs | CD2.X fields |
| Loan Costs | CD2.XSTD |

### Step 24 - Closing Disclosure Page 3

| Field Description | Encompass Field ID |
|---|---|
| Cash | CD3.X40 |
| Cash To Close | CD3.X23 |
| Loan Amount | CD3.X81 |
| From To Borrower | CD3.X48 |
| From To Seller | CD3.X49 |
| Transaction summaries | CD3.X fields |
| Principal reduction amount | (Adjustment fields) |
| Additional debts/payoffs | CD3.X fields (Payoff sections) |
| MIP refund (for refinance) | (MIP refund fields) |
| Cash to close calculations | CD3.X23, CD3.X110 |
| STD Final Cash To Close | CD3.X110 |
| STD LE Cash To Close | CD3.X101 |

### Step 25 - Closing Disclosure Page 4

| Field Description | Encompass Field ID |
|---|---|
| Assumption | LE3.X12, CD4.X fields |
| Demand feature | CD4.X fields |
| Late payment | CD4.X fields |
| Negative Amortization | CD4.X2 |
| Partial payments | CD4.X fields |
| Security interest | CD4.X fields |
| Escrow account status | CD4.X fields |
| Escrow property costs breakdown | CD4.X fields |
| Adjustable payment table (if ARM) | CD4.X fields |
| Ignore 1st ARM Adjustment | CD4.X31 |
| Seasonal Payments | CD4.X27 |
| Seasonal Payment From Year | CD4.X28 |
| Subsequent Changes | CD4.X33 |
| Step Payments | CD4.X25 |
| Step Payment | CD4.X26 |

### Documents to Process:
- Initial Closing Disclosure
- Previous CDs (for COC tracking)
- Fee variance worksheets
- Lender credit documentation
- Payoff statements
- MIP refund documentation (refinance)
- ARM adjustment documentation (if ARM)
- All itemized fees and cost documentation

---

## 9. Compliance & Distribution Agent (Steps 26-28)

### Step 26 - Mavent/Compliance Review

| Field Description | Encompass Field ID |
|---|---|
| Mavent compliance report results | (External system - Mavent) |
| Compliance failure flags | (Mavent integration fields) |
| Issue escalation status | (Custom workflow fields) |

### Step 27 - Complete Milestone

| Field Description | Encompass Field ID |
|---|---|
| Milestone Status - Docs Out | Log.MS.Status.Docs Out |
| Milestone Date - Docs Out | Log.MS.Date.Docs Out |
| Milestone Comments - Docs Out | Log.MS.Comments.Docs Out |
| Milestone Expected Completion Date - Docs Out | Log.MS.ExpectedDate.Docs Out |
| Milestone Duration Docs Out | Log.MS.Duration.Docs Out |
| Milestone Status - Completion | Log.MS.Status.Completion |
| Date Completed | MS.CLO |
| Completion Due Date | MS.CLO.DUE |
| Last Finished Milestone | Pipeline.LastCompletedMilestone |
| Last Finished Milestone Date | MS.STATUSDATE |
| Next Expected Milestone | Log.MS.Stage |
| Next Expected Milestone Date | Pipeline.NextMilestoneDate |
| Pending query flags | (Conditions system) |
| Blocking error flags | (Validation system) |

### Step 28 - Send Final DOCS

| Field Description | Encompass Field ID |
|---|---|
| Recipient list | (Email/distribution system) |
| Loan Officer | 317 |
| Loan Processor | 362 |
| Loan Closer | 1855 |
| Escrow Company Name | 610 |
| Escrow Co Contact | 611 |
| Title Insurance Company Name | 411 |
| Title Co Contact | 416 |
| Document formatting verification | (Document generation system) |
| Required attachments checklist | (Document system) |
| Receipt confirmation status | (Email tracking system) |

### Documents to Process:
- Complete loan package
- Mavent compliance report
- Milestone tracking system data
- Final closing package (all documents)
- Distribution list
- Receipt confirmations
- Quality control checklist

---

## Cross-Cutting Requirements

### All Agents Need Access To:

| Field Description | Encompass Field ID |
|---|---|
| Loan Number | 364 |
| Loan Status | 1393 |
| Loan Folder Name | LoanFolder |
| Active Loan | Loan.Active |
| Core Milestone | CoreMilestone |
| Loan Type | 1172 |
| Loan Program | 1401 |
| Loan Purpose | 19 |
| Occupancy (P/S/I) | 1811 |
| Subject Property State | 14 |
| Borrower Name | 36, 37 or 4000, 4002 |
| CoBorrower Name | 68, 69 or 4004, 4006 |
| Loan Last Modified | LoanLastModified |
| Date File Started | MS.START |

### All Agents Should Output:
- Structured results (JSON/dict format)
- Verification status for each field
- Error/warning messages
- Processing timestamp
- Agent version/identifier
- Dry-run simulation results (if in dry-run mode)

---

## Conditional Processing by Loan Type

### FHA Loans:
- Property & Program Agent: Steps 12-13 required
- All FHA-specific fields and documents
- Agency Case # (1040)

### VA Loans:
- Property & Program Agent: Steps 14, 16 required
- All VA-specific fields and documents
- VA Veteran Loan Code (958)
- VASUMM.X fields

### USDA Loans:
- Property & Program Agent: Step 15 required
- All USDA-specific fields and documents
- Agency Case # (1040)

### Conventional Loans:
- Property & Program Agent: Step 11 only
- Skip program-specific steps (12-16)

---

## State-Specific Processing

### Agents Requiring State Logic:

**1. Borrower Setup Agent:**
- Vesting rules for TX, CA, NV, CO
- State-specific vesting requirements
- Use Subject Property State (14)

**2. Contacts & Vendor Agent:**
- Trustee selection varies by state
- Use Subject Property State (14)
- State-specific vendor lists

**3. Financial Setup Agent:**
- Tax calculations vary by state
- Use Subject Property State (14)
- State-specific escrow rules

### State Data Required:
- Subject Property State (14)
- Subject Property State Code (1395)
- State-specific vesting rules
- State-specific trustee lists
- State-specific tax calculation rules

---

## Notes on Field ID Format

- **Standard fields**: Numeric (e.g., 1051, 356, 4000)
- **Extended fields**: Prefix notation (e.g., FE0155, FR0112)
- **Custom fields**: CX prefix (e.g., CX.DOC.REQ.APPROVAL.LO)
- **HMDA fields**: HMDA.X prefix (e.g., HMDA.X86)
- **Closing Disclosure fields**: CD1.X, CD2.X, CD3.X, CD4.X
- **Loan Estimate fields**: LE1.X, LE2.X, LE3.X
- **Milestone/Log fields**: Log.MS prefix or MS prefix
- **Pipeline fields**: Pipeline prefix
- **Vendor fields**: VEND.X prefix
- **VA Summary fields**: VASUMM.X prefix
- **Disclosure fields**: DISCLOSURE.X prefix
- **New HUD fields**: NEWHUD.X, NEWHUD2.X prefix

**Co-Borrower fields**: Many fields have a #2 suffix for co-borrower data (e.g., 4000#2 for Co-Borrower First Name)

---

**Generated**: Based on SUBCAGENTS_ARCHITECTURE.md and master_field_data.csv analysis
**Date**: November 28, 2025
**Master Field Data**: 4865 fields mapped



