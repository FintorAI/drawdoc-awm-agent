# Draw Docs & Disclosure Workflow Analysis

## Document Analyzed
- **Source**: `context/sop.md` (4,771 lines)
- **Supporting**: `video_summary.txt`, `docs_draw_agentic_architecture_mvp.md`
- **Date**: November 28, 2025

---

## Executive Summary

This document captures the complete Draw Docs workflow as documented in AWM's SOP, identifies gaps between the current proposed architecture and the actual requirements, and provides recommendations for refining the agentic implementation.

---

## 1. Draw Docs Workflow Overview

### 1.1 Entry Conditions (Prerequisites)

Before a file can enter the Docs Draw process:

| Condition | Description | Verification Source |
|-----------|-------------|---------------------|
| CTC Status | File must be "Clear to Close" by Underwriter | Milestone section in Encompass |
| CD Approved | CD Status must say "CD Approved" | Encompass CD Status |
| CD Acknowledged | Initial CD must be signed/acknowledged by Borrower(s) | Disclosure Tracking tool |
| 3-Day Waiting | TRID CFPB 3-day waiting period must have passed | CD ACK date + 3 business days |
| Docs Ordered Queue | File must be in the "Closer – Docs Ordered" pipeline | Pipeline View |

**TAT (Turnaround Time)**: 6 Business Hours from when loan hits Docs Order queue + CD approved + ACK by Borrower(s)

---

### 1.2 Complete Process Steps (29 Major Steps)

#### STEP 1: Pipeline Selection & Assignment
- Open Encompass → Pipeline View → "Closer – Docs Ordered"
- Verify milestone reads "Clear to Close" in **bold**
- Check Alerts & Messages for any Docs-related notes
- Assign closer name to "Docs Ordered" milestone
- Review any previous department comments

#### STEP 2: Pre-Check - POA & Trust Approval
- Location: `Encompass >> Forms >> Funding Custom Fields`
- Check if file is approved to "Close in a POA"
- Check if file is approved to "Close in a Trust"
- Handle VA Overage (pricing adjustment) if applicable

#### STEP 3: Document Download from e-Folder
**35+ documents required** organized by category:

**Application Section:**
1. Initial 1003
2. Approval Final
3. MI Certificate (if applicable)
4. Borrower IDs (DL, SSN Card)
5. SSN Verification

**Government Section:**
6. FHA Case Assignment (FHA transactions)
7. FHA Refinance Authorization (FHA Refinance)
8. VA Case Assignment & Certificate of Eligibility (VA)

**Credit Section:**
9. Credit Report
10. Payoff (Refinance transactions)

**Property Section:**
11. Title Report
12. Appraisal Report
13. Purchase Agreement & Addendums (Purchase)
14. Tax Summary (Recent)
15. USPS ZIP Search
16. Evidence of Insurance (HO6, HO3, Master) & paid receipt
17. Flood Certificate
18. Flood Insurance (if applicable)
19. Power of Attorney (if applicable)
20. Seller Real Property Disclosure (Nevada only, Non-Builder)

**Disclosures Section:**
21. Initial Loan Estimate
22. Last Disclosed Loan Estimate

**Closing Section:**
23. Appraisal Report Invoice
24. Credit Report Invoice
25. Final Inspection Invoice (if applicable)
26. Invoice Pest Inspection (if applicable)
27. Home Inspection (if available)
28. Closing Disclosure – Initial / COC CD
29. Borrower's acknowledgement of CD / COC CD ACK
30. Final 1003 / 92900 Addendum
31. Escrow Wire Instructions
32. Closing Protection Letter (CPL)
33. Pre-Note VOE
34. Additional Docs to be Signed (if given)
35. Lender fee sheet (if required)

**Important**: Check document tracking section for any Processor/UW comments

#### STEP 4: Borrower Summary – Origination
- Location: `Encompass >> Forms >> Borrower Summary – Origination`
- **Verify against**: Final 1003, Approval Final, Driving License, SSN Card/Verification

| Field | Verification |
|-------|--------------|
| AWM Loan number | Match Final 1003 |
| Borrower's name | Exact match with Approval Final & Final 1003 |
| SSN number | Match across documents |
| DOB | Verify |
| Phone numbers | Verify |
| Marital Status | Verify |
| Email ID | Verify |

**SSA Authorization/Validation** - Only required when:
- SSN discrepancy identified (2 different SSNs, mismatch between credit/pay stubs/W2)
- AUS alert or "Potential Red Flag" issued

**MIN Number Generation:**
1. Click on "MERS MIN" box to generate
2. Verify uniqueness on MERS website: https://www.mersonline.org/
3. Search by SSN for both borrower & co-borrower
4. Upload PDF of MIN/SSN search to Encompass under "MIN-SSN Summary"

#### STEP 5: Borrower Information – Vesting
- Location: `Encompass >> Borrower Information – Vesting Form`

**Verification by Transaction Type:**
- **Purchase**: Verify from 1003 form
- **Refinance**: Verify from Title Report AND 1003 form

**Fields to Update/Verify:**
| Field | Description |
|-------|-------------|
| Vesting | Confirm with Processor via Slack or vesting task |
| AKA Names | Fetch from Credit report, Fraud report, ID card |
| Vesting Type | Individual, Co-Signor, Title Only, Settlor Trustee |
| Occupancy Intent | Will Occupy, Will not, Already Occupy |
| Trustee Of | Select Trust name (if Trust approved) |
| POA Borrower | Verify with Funding Custom Field + POA document |

**State-Specific Vesting Rules:**

| State | Special Rule |
|-------|--------------|
| CA, NV | Married + non-borrowing spouse not on title → "Married Man/Woman as his/her Sole and Separate property" |
| Colorado | Marital status NOT required in vesting |
| Texas | No "Joint Tenants" verbiage; Attorney handles separately |

#### STEP 6: Trust Section (When Approved for Trust)
- Verify Trust approval in Funding Custom Field
- Trust paperwork must be certified by UW

**Trust Information to Update:**
1. Trust Name (from Trust document)
2. Trust Date/Year
3. Org. State (where Trust is located)
4. Org. Type (usually "An Inter Vivos Trust")
5. Build Beneficiary (if any on Trust document)
6. Amended/Restated dates (if applicable)

**Trust Vesting Format:**
```
"Borrower name, Trustee / Trustees of the TRUST NAME dated TRUST DATE"
```

**PTF Condition for Trust:**
```
"TRUST Revocable Rider – Title Company to update Settlor(s) information on Trust rider (Section – C) prior of recording."
```

#### STEP 7: 1003 Page-3 (Lender/LO Info)
- Location: `Encompass >> 1003 Page-3 >> Loan Originator Information`
- **Do NOT change anything** - reflects to Final 1003

**Lender Section:**
- Verify: "ALL WESTERN MORTGAGE, INC."

**Loan Officer:**
- Verify: LO Name, NMLS#, Email, Phone, State License
- Source: Mavent report under `Tools >> Compliance Review`
- NMLS must say "PASS"

#### STEP 8: Closing Conditions
- Location: `Encompass >> Forms >> Closing Conditions`

**Fields:**
| Field | Value |
|-------|-------|
| Drawn City | Las Vegas |
| Draw State | NV |
| Closing County | Subject property county |
| Closing State | Subject property state |

**Condition Sets by Loan Type & Purpose** - Add via "Add" button

**Common Conditions:**
1. Title Report Expiration = Effective Date + 60 days
2. CPL Expiration = Effective Date + 30 days
3. Consummation date on or After = Closing/Signing Date
4. Pay 1 YR Hazard at closing = Due Amount from Hazard insurance
5. Property tax installment within 60 days of first payment

**PTF Conditions:**
- Copy from `Encompass >> e-Folder >> UW Conditions >> PTF Conditions`
- Only conditions starting with "PTF"

#### STEP 9: File Contacts
- Location: `Encompass >> Tools >> File Contacts`

**i) Lender:**
```
Name: ALL WESTERN MORTGAGE, INC.
Address: 8345 WEST SUNSET ROAD, SUITE 380, LAS VEGAS, NV 89113
Org. State: Nevada (always)
NMLS: 14210
LIC ID: 204
Phone: 702-369-0905
Email: LO's email
Fax: 702-920-8421
```

**ii) Investor:**
- Select from Business Contact (if applicable)

**iii) Title Insurance Company:**
- Verify with Title Report
- Copy to Settlement Agent if same company

**iv) Escrow Company:**
- Bank ABA & Account from Escrow wire instruction
- License ID#, Contact License#
- Officer Name, Case#, Phone, Email

**v) Settlement Agent:**
- Check "Add to CD Contact Info" = YES

**vi) Buyer's Agent** - Skip (CD Team handles)

**vii) Seller's Agent** - Skip (CD Team handles)

**viii) Hazard Insurance Company:**
- Verify all fields with HOI policy & paid receipt

**ix) Flood Insurance** (if in Flood Zone):
- Verify with Flood Insurance policy & paid receipt
- Max allowable coverage = $250k

**x) Docs Prepared By:**
- AWM for all states EXCEPT Texas
- Texas: "Black Mann & Graham, LLP" from Business Contacts >> Attorney

#### STEP 10: Hazard Insurance Verification

**Dwelling Coverage Calculation:**
```
Dwelling Amount + 125% Replacement Cost = Total Coverage
Total Coverage must >= Loan Amount
```

**Example:**
```
$206,000 (Dwelling) + 125% (Replacement Cost) = $257,500 Total Coverage
```

**Note:** Building Ordinance or Law Coverage should NOT be counted toward replacement cost

**Mortgagee Clause Requirements:**
- Lender name: "ALL WESTERN MORTGAGE, INC"
- Lender address
- AWM Loan #

**Master Policy Handling:**
If missing Property address, Borrower name, or loss payee:
1. Check if PTF/PTD Condition added by UW
2. If not, request from processor + add PTF condition
3. Do NOT hold docs - proceed with PTF

#### STEP 11: Flood Insurance Verification (If Applicable)
- Verify Flood Zone from Flood Certificate (Code: A, V)
- Verify borrower info on Flood Cert
- Max Coverage limit = $250k
- If loan amount > $250k → Coverage = $250k
- If loan amount < $250k → Coverage >= Loan amount

**Cross-verify Zone/Map# between:**
- Flood Certificate
- Flood Insurance
- Appraisal Report

#### STEP 12: Closing Vendor Information
- Location: `Encompass >> Forms >> Closing Vendor Information`
- Auto-populated from File Contacts

**Trustee by State:**
| State | Trustee |
|-------|---------|
| NV, CA, AZ, WA, UT, OR | Same as Title Company |
| Colorado | County name & address (Business contacts >> No Category) |
| Texas | Thomas E Black Jr. (Business contacts >> Attorney) |
| Florida, Michigan | NO Trustee |

#### STEP 13: Property Information
- Location: `Encompass >> Forms >> Property Information`

**Property Type Verification:**
- Compare Encompass vs. Appraisal Report
- Determines correct RIDER selection

**Riders by Property Type/Occupancy:**
| Condition | Rider Required |
|-----------|----------------|
| Property Type = PUD | PUD Rider |
| Property Type = Condo | Condo Rider |
| Occupancy = Investment | 1-4 Family Rider |
| Occupancy = Secondary | Second Home Rider |
| Property Type = Manufacturing Home | MH Rider + Affixation of Affidavit |
| Trust Approved | Revocable Trust Rider |
| 203K Program | 203K Rehabilitation Rider |
| Second Lien | Second Lien Rider |

**Property Type Logic:**
- SFR(Detached) + NO HOA fees → AUS = "Detached"
- SFR(Detached) + HOA fees → AUS = "PUD"
- 2-4 Units → AUS = "Detached" (even if Attached on Appraisal)
- 2-4 Units → 1-4 Family Rider compulsory (except FHA Primary)

**Other Fields:**
- PUD/Condo Name: From Title Report (Exhibit A) or Appraisal Neighborhood
- Flood Zone: From Flood Cert
- Parcel Number: From Tax Summary/Cert/Title
- Title Report Date: Effective date
- Legal Description: Click "Copy from Page 1 of 1003" or "See Prelim"
- Special Endorsements: By property type (see table below)

**Standard Endorsements:**
```
SFR/Detached/Attached: 8.1, 9.10-06
PUD: 8.1, 9.10-06, 5.1-06, 115.4
Condo: 8.1, 9.10-06, 4.1-06, 116.2
ARM + Detached: 8.1, 9.10-06, 111.5
ARM + PUD: 8.1, 9.10-06, 111.5, 5.1-06, 115.4
ARM + Condo: 8.1, 9.10-06, 111.5, 4.1-06, 116.2
Manufacture: 8.1, 9.10-06, ALTA7
Manufacture + PUD: 8.1, 9.10-06, ALTA7, 5.1-06, 115.4
```

**Texas Endorsements (Different):**
```
SFR/Detached/Attached: T-19, T-36
PUD: T-19, T-36, T-17
Condo: T-19, T-36, T-28
ARM + Detached: T-19, T-36, T-33
ARM + PUD: T-19, T-36, T-17, T-33
ARM + Condo: T-19, T-36, T-28, T-33
Manufacture: T-19, T-36, T-31, T-31.1, ALTA 7
Manufacture + PUD: T-19, T-36, T-17, T-31, T-31.1, ALTA 7
TX Home Equity: T-19, T-36, T-42, T-42.1
TX Home Equity + PUD: T-19, T-36, T-42, T-42.1, T-17
TX Home Equity + Condo: T-19, T-36, T-42, T-42.1, T-28
TX Home Equity + Manufacture: T-19, T-36, T-31, T-42, T-42.1, T-31.1, ALTA 7
TX Home Equity + Manufacture + PUD: T-19, T-36, T-17, T-31, T-42, T-42.1, T-31.1, ALTA 7
```

#### STEP 14: FHA-Specific Forms (FHA Only)

**HUD 92900ALT FHA Loan Transmittal:**
- Location: `Encompass >> Forms >> HUD 92900ALT FHA Loan Transmittal`
- FHA Case#: From FHA Case Assignment document
- Case Assigned Date: From FHA Case Assignment document
- SOA (Section of Act): From FHA Case Assignment document
- ADP Code: Based on loan program (reference ADP Code list)

**FHA Management:**
- Location: `Encompass >> Forms >> FHA Management >> Tracking >> Refi Authorization`
- MIP Refund (Refinance only): From Refinance Authorization document
- Consider MIP Refund for FUNDING month, not NOTE date
- MIP Refund should be positive (+)

#### STEP 15: VA-Specific Forms (VA Only)

**VA Management:**
- Location: `Encompass >> Forms >> VA Management`
- VA Agency Case#: From VA Case Assignment, Final Approval, Final 1003/92900A
- Funding Fee Exempt Status: From Certificate of Eligibility
- VA Funding Fee Amount: From Final Approval/1003, verified against fee chart

**VA Funding Fee Chart (on or after April 7, 2023):**
Same % for Regular Military, Reserves, and National Guard

| Type | Down Payment | First Use | Subsequent Use |
|------|--------------|-----------|----------------|
| Purchase/Construction | <5% | 2.15% | 3.30% |
| Purchase/Construction | 5-<10% | 1.50% | 1.50% |
| Purchase/Construction | ≥10% | 1.25% | 1.25% |
| Cash-Out Refi | N/A | 2.15% | 3.30% |
| IRRRL | N/A | 0.50% | 0.50% |

**VA 26-1820 Loan Disbursement:**
- Location: `Encompass >> Forms >> VA 26-1820 Loan Disbursement`
- Section 6: Relative (from VA Nearest Living Relative disclosure)
- Section 7: Loan Purpose (from Final VA 92900A)
- Section 12: Vested (from Final VA 92900A)
- Section 27B: Occupancy (from Final VA 92900A)
- Line 20: Annual Real Estate Taxes
- Line 21(a): Hazard Face Amount & Annual Premium
- Line 21(b): Flood Face Amount & Annual Premium (if applicable)

#### STEP 16: USDA-Specific Forms (USDA Only)

**USDA Management:**
- Location: `Encompass >> Forms >> USDA Management`
- Agency Case No: From USDA Commitment form (9 digits)
- Verify: Borrower name, Mortgage Clause, Loan Amount
- Funding fee factor for Upfront Guarantee Fee and Annual Renewal Premium

**Technology Fee:** $25 charged on commitments dated on/after January 1, 2020
- Disclosed in Section B, 0% tolerance
- Paid to: ALL WESTERN MORTGAGE, INC.
- APR Fee: Yes

#### STEP 17: RegZ-CD
- Location: `Encompass >> Forms >> RegZ-CD`

**Closing DOCS Section:**
- Loan Program & Plan Code: Per transaction
- Texas State: Select "TX HOME EQUITY" for Cash-Out Refi + Primary
- Investor: Select if applicable

**Disclosure Information:**
- Disclosed APR: Verify with Last disclosed CD APR

**Loan Information:**
| Field | Verification Source |
|-------|---------------------|
| Purchase Price | Purchase Agreement/addendum |
| Appraised Value | Appraisal Report |
| 1st Payment Date | One month after NOTE/Closing Date |
| CD Date Issued | Same as Closing Date |
| Application Date | Initial 1003 |
| Rate Lock Date | Last LE |
| Lock Expiration | Last LE |
| Document Date | Same as Closing/NOTE Date |

**Closing Date Verification:**
- Must be AFTER 3 days of CD acknowledgement
- Sundays and Federal Holidays NOT counted in 3-day waiting

**Rescission Date (Refinance Primary Only):**
- Rescission includes Monday-Saturday (exclude Sunday & Federal holidays)
- Example: Closing 01/26/2019 (Saturday) → Rescission ends 01/30/2019 (Wednesday)

**Disbursement Date:**
- Dry State: Next day after Closing
- Wet State: Same day as Closing
- Refinance Primary: Next day after Rescission date
- Includes Monday-Friday only

**Other Fields:**
- Purpose of Loan: Purchase/Refinance/Construction/Home Equity
- Property will be: Primary/Secondary/Investment
- Loan Type: Conventional/FHA/VA/USDA
- Lien Position Type: First/Second
- Amortization Type: Fixed/ARM
- Days Per Year: 365 (always)
- Sync With Prepaid Interest Date: CHECKED

#### STEP 18: Mortgage Insurance (RegZ-CD)

**Conventional (>80% LTV):**
- Upfront PMI: Single Premium only
- 1st Renewal: % and months from MI Certificate (usually 120 months)
- 2nd Renewal: Usually 0.20%, remaining loan term
- Renewal Calc Type: Declining Renewals UNCHECKED
- Cancel at: 78.000 (except 2+ units → remove cutoff)

**FHA:**
- UFMIP: 1.75% (always)
- Renewal Calc Type: "Calculate based on remaining balance"
- MI Renewal %: Per FHA chart, verify with Approval Final/1003
- Click "GET MI" button before docs issued

**VA:**
- Funding Fee: Per chart, verify with Last LE, Initial/COC CD

**Late Charge:**
| Loan Type | Days Late | Charge |
|-----------|-----------|--------|
| Conventional | 15 | 5% |
| FHA, VA, USDA | 15 | 4% |

#### STEP 19: UW Summary
- Location: `Encompass >> Tools >> Underwriter Summary`
- Identify LTV & CLTV %
- Check for Subordinate Financing
- Check Approval Expiration Date

#### STEP 20: Aggregate Escrow Account
- Location: `Encompass >> Forms >> Aggregate Escrow Account`

**Fields:**
| Field | Value |
|-------|-------|
| Servicer | AWM (All Western Mortgage Inc.) |
| 1st Payment Date | One month after Closing Date |
| Taxes | Monthly & Yearly from Tax Summary, verify with Final Approval |
| Insurance | Monthly & Yearly from HOI policy |
| MI | When applicable |
| Cushion | 2 months (Taxes & Insurance), 0 (MI) |
| Starting Balance | Must be POSITIVE |
| Aggregate Adjustment | NEGATIVE or ZERO |

**Tax Calculation by State (New Construction/Builder):**
| State | Formula |
|-------|---------|
| Nevada, Arizona | 1% of Sales Price / 12 = Monthly |
| California | 1.25% of Sales Price / 12 = Monthly (or Tax Summary, whichever higher) |
| Colorado | Mill Levy Rate or 1% of Sales Price (per UW Approval) |
| Other (Non-Builder, Resale, Refinance) | Higher of Tax Cert or Title Report |

**Impound Verification:**
- FHA, VA: Impounds REQUIRED for taxes AND insurance
- Conventional: Optional, but required if LTV > 80%
- California: No impounds option up to 90% LTV (Conventional only)
- Flood Insurance: ALWAYS impounded (even if Impound = NO)

#### STEP 21: 2015 Itemization
- Location: `Encompass >> Forms >> 2015 Itemization`

**Fee Sections:**

| Section | Fees | CD Section |
|---------|------|------------|
| 800 | Origination, Processing, UW, Investor fees | Sec-A |
| 802 | Lender Credits, Credit for Rate, Discount Points | Sec-A/Sec-J |
| 803-835 | Appraisal, Credit Report, Tax Service, UFMIP | Sec-B |
| 900 | Prepaids: Interest, HOI, Flood, Taxes | Sec-F |
| 1000 | Escrow Reserves | Sec-G |
| 1100 | Title Charges | Sec-B or Sec-C |
| 1200 | Recording & Transfer | Sec-E |
| 1300 | Settlement Charges | Sec-H |
| 1400 | Lender/Seller Credits, MIP Refund | Sec-J |

**APR Fees:**
- Origination fees: APR
- Discount Points: APR
- UFMIP: APR
- Monthly MI: APR
- Appraisal (R3 AMC only): APR
- Credit Report: Non-APR
- Title fees: Per CFPB list
- Recording/Transfer: Non-APR
- Sec-F fees: Non-APR (except Prepaid Interest)
- Sec-G fees: Non-APR (except Monthly MI)
- Sec-H fees: Non-APR

**Title Fee Logic:**
- Title Company on Service Provider List = Company closing with → Sec-B (10% tolerance)
- Title Company on Service Provider List ≠ Company closing with → Sec-C (no tolerance)

#### STEP 22: Fee Variance (Tolerance Cures)
- Location: `Encompass >> Tools >> Fee Variance Worksheet`

**Tolerance Cure Calculation:**
1. Required Cure Amount: Auto-calculated or manual
2. Applied Cure Amount: Auto-calculated from Line 3
3. Cure applied to Lender Credit
4. Cure Applied to Principal (POC) - only when needed

**Cure Baseline:**
- No fee changes throughout LE/CD → Compare LE vs. Current Itemization
- Fee increased on Initial/COC CD → Compare Last Disclosed CD vs. Current Itemization

#### STEP 23: CD Page 1
- Location: `Encompass >> Forms >> Closing Disclosure – 1`

**Closing Information:**
- CD Date Issued: Same as Closing Date
- Settlement Agent: Verify name
- File#: Escrow order number from Title Report

**Loan Information:**
- Loan Term: In years (do NOT check "Construction Period included in Loan terms")
- Purpose: Purchase/Refinance/Construction/Home Equity
- Product: Fixed Rate/Adjustable Rate

**Property:**
- Address: Verify against ALL documents (final call is Docs Team)
- Valid per: Tax Certificate, USPS, County records
- Appraised Value: From Appraisal Report & Last CD
- Sales Price: From Purchase Contract & Last CD

**Loan Type:**
- Loan ID#: AWM Loan number
- MIC#: FHA/VA Case# or MI Cert# (Conv >80%)

**Transaction Information:**
- Borrower Info: Name & present address from Final 1003/Approval
- Seller Info: From File Contacts
- Lender Info: From File Contacts or Business Contacts

**Loan Terms:**
- Loan Amount, Interest Rate, Monthly P&I: Verify with Last LE, Initial/COC CD, Approval Final
- "Can this amount increase after closing": Always NO
- Prepayment Penalty: Always NO (except SGCP Investment)
- Balloon Payment: Always NO

**Projected Payments:**
- Monthly MI (if applicable)
- Estimated Escrow: From Aggregate Escrow
- Estimated Taxes, Insurance & Assessments: Per Impound setup

#### STEP 24: CD Page 2
- Location: `Encompass >> Forms >> Closing Disclosure – 2`

**Loan Costs:**
- Section A: Origination Charges
- Section B: Services Borrower Did Not Shop For
- Section C: Services Borrower Did Shop For
- Section D: Total Loan Costs

**Other Costs:**
- Section E: Taxes & Government Fees
- Section F: Prepaids
- Section G: Initial Escrow Payment at Closing
- Section H: Other
- Section I: Total Other Costs
- Section J: Total Closing Costs + Lender Credits

#### STEP 25: CD Page 3
- Location: `Encompass >> Forms >> Closing Disclosure – 3`

**Summaries of Transactions:**
- Section K & M: Due from/to Borrower & Seller at Closing
- Line 4: Principal Reduction or Additional Payoffs/Debts
- Section L & N: Paid by/on behalf of Borrower; Due from Seller
- Line 1: Deposit/EMD
- Line 4 (Sec-L): Subordinate Financing
- Line 5 (Sec-L) & Line 8 (Sec-N): Seller Credit

**MIP Refund (FHA Refinance):**
- Click Payoffs & Payments
- Adjustment Type: "Rebate Credit"
- Description: "MIP Refund"
- Amount: From Refinance Authorization

**Payoff Requirements:**
- Full creditor name
- Full account number
- Must be on CD AND Lender Instructions to Escrow

**Cash to Close:**
- Verify UW's Cash to Close condition
- Check IPC Max Credit limits
- Verify minimum/maximum investment requirement

#### STEP 26: CD Page 4
- Location: `Encompass >> Forms >> Closing Disclosure – 4`

**Loan Disclosures:**

| Disclosure | FHA/VA/USDA | Conventional |
|------------|-------------|--------------|
| Assumption | Will allow | Will NOT allow (except ARM with certain investors) |
| Demand Feature | Does not have | Does not have |
| Negative Amortization | Does not have | Does not have |
| Partial Payments | Does not accept | Does not accept |

**ARM Assumptions (Will allow):**
Chase, SGCP, Wellsfargo, Caliber Non-Agency ARM, Rushmore, TIAA

**Escrow Section:**
- Auto-checked based on Aggregate Escrow setup
- Will have / Will not have
- If no impounds: "you declined it"

**AP Table (ARM Only):**
- Auto-populated from RegZ-CD
- Verify with Last LE and Initial CD

#### STEP 27: CD Page 5
- Location: `Encompass >> Forms >> Closing Disclosure – 5`

**Loan Calculations:**
- APR verification: Cannot increase >0.125% from COC CD (else 3-day wait required)

**3-Day Wait Triggers:**
1. APR increase >0.125%
2. Loan product change (Jumbo↔Conforming, Conv↔Govt, FHA↔VA, Fixed↔ARM)
3. Prepayment penalty added

**Other Disclosures:**
- Check: "state law may protect you from liability for the unpaid balance"

**Contact Information:**
- Lender, Real Estate Broker (B & S), Settlement Agent
- Click "Copy From 1003" if blank
- Mortgage Broker: Always blank

**Confirm Receipt:**
- Signature type: "By Name" (always)

#### STEP 28: Compliance Review (Mavent)
- Location: `Encompass >> Tools >> Compliance Review`

**Process:**
1. Click "Order" button
2. Wait for report generation
3. Check for any failures
4. If FAIL: Inform supervisor/team lead for review
5. Must PASS before ordering docs

**Mavent must be run AFTER docs are issued**

#### STEP 29: Update Milestone & Order Docs

**Update Milestone:**
- Location: Milestone Status "Docs Ordered"
- Check "Finished" box
- Add comment: "DOCS Out on [Date]"
- No queries or Mavent issues pending

**Order Docs:**
1. Go to RegZ-CD form → Click "Order Docs"
2. Order Type: "Closing"
3. Review Data Audits (clear related ones)
4. Select "All Closing Docs"
5. **Remove from package:**
   - Data Entry Proof Sheet
   - Data Entry Proof Sheet – Fees
   - Seller CD
   - NV Repayment Ability Verification Worksheet (Nevada)
   - Final 1003 & 92900A (if without CTC)
   - Loan Modification Agreement Disclosure (ARM)
   - CHASE-prefixed docs (Chase investor)

**Add Additional Docs:**
- Additional docs to be signed
- POA (if applicable)
- Attorney Package (Texas)
- Evidence of Insurance
- Invoices (Appraisal, Credit, Inspection)
- Payoffs
- Hold Harmless Disclosure (if without CTC)

**Send to All Parties:**
- To: LO, Processor, Title/Escrow Company, docs@allwestern.com
- Subject: "Loan Docs: [AWM Loan#]_[Borrower Name]"

---

## 2. Error Handling & Conditions

### 2.1 PTF (Prior to Funding) Conditions

PTF conditions are used to flag issues for resolution before funding:

**When to Add PTF:**
- Document discrepancies (address mismatch, name mismatch)
- Missing documents
- Incomplete information
- Insurance issues

**Simple Fix Rule:**
- If simple fix needed → Add PTF, proceed with docs
- If major fix needed → Contact processors/LOs, HOLD docs

### 2.2 Hard Stops (Immediate Escalation Required)

| Issue | Action |
|-------|--------|
| Loan Amount mismatch | HARDSTOP - contact Team Lead |
| Interest Rate mismatch | HARDSTOP - contact Team Lead |
| Monthly Hazard/Tax discrepancy with UW | HARDSTOP - get revised Final Approval |
| Insufficient Dwelling Coverage | HARDSTOP - request updated HOI |
| Approval Expiration passed | HARDSTOP - request UW update |
| Random fees in Section A | HARDSTOP - manager approval required |
| Pre-Funding QC flagged | HARDSTOP - wait for QC clearance |
| ARM loan not approved by Lock Desk | HARDSTOP - wait for approval |
| Non-QM not reviewed by Eric Gut | HARDSTOP - wait for review |

### 2.3 Condition Categories

**Condition Assignment by Department:**
- Loan Processor: Third-party docs (Appraisal, Contract, HOI)
- Underwriter: Credit issues, income issues

---

## 3. State-Specific Rules

### 3.1 Texas

**Attorney Handling:**
- BM&G: El Paso branch (fee: $225)
- Cain & Kiel: Proctor, Plano, Patrick Moore branches (fee: $325)
- PPDocs, Inc: Proctor, Plano, P Moore branches (alternate)

**Attorney Package Review:**
1. Verify basic info (Note date, Names, Loan#, Address)
2. Update Attorney fee on CD per Invoice
3. Review Closing Conditions on package
4. Team Lead 2nd level review required

**Home Equity (Cash-Out Refi + Primary):**
- 12-Day Notice required
- Deed of Trust Form No. 3044.1
- Texas Home Equity Affidavit Form 3185
- Special endorsements: T-42, T-42.1

**NBS Requirements:**
- Primary: Spouse MUST be in vesting as NBS or Co-Borrower
- If on Title Report Schedule A: Must be on Contract/Addendum
- Secondary/Investment: NBS not required if vesting is "Sole & Separate"

**Manufactured Home:**
- Check if "yet to be converted to real property"
- If not converted: Add specific conditions + T-31 endorsement

**Vesting:**
- No "Joint Tenants" verbiage
- Reference only marital status

### 3.2 Florida

**Florida Branch Credit Report Cap:**
- Maximum: $48.30 (even if invoice higher)
- Lower invoice amount: Charge per invoice
- Only applies to Florida Branch loans (not other branches in FL state)

**HHF DPA Program:**
- Transfer tax / Documentary Stamp / Intangible TAX exempted

### 3.3 Nevada

- Remove NV Repayment Ability Verification Worksheet from package
- Prosperity Branch: No cushions, no SIDS impounds

### 3.4 California

- Tax Calculation: 1.25% of Sales Price / 12 (or Tax Summary, whichever higher)
- No impounds option up to 90% LTV (Conventional only)

### 3.5 Colorado

- Marital status NOT required in vesting
- Trustee: County name & address
- Tax Calculation: Mill Levy Rate or 1% (per UW)

### 3.6 Illinois

- Anti-Predatory Lending Database update required after docs out
- Email notification to LO with ILAPLD portal instructions

### 3.7 Community Property States

**List:** AZ, CA, ID, LA, NV, NM, TX, WA, WI

**NBS Signing Requirements (Refinance Primary Rescindable):**
- Sign/acknowledge CD
- Sign NORTC
- Sign security instrument

**Exception:** If QCD executed and recorded + vesting shows sole/separate → NBS not required

---

## 4. Loan-Type Specific Rules

### 4.1 FHA

- MIP Refund: Based on FUNDING date (not NOTE date)
- ADP Code: Verify with property type, special for Buydown (796)
- Streamline without Appraisal: Appraised value = Original Property Value from Refi Auth
- Click "GET MI" button before docs issued
- 92900-A signed page-3: Add PTF if missing

### 4.2 VA

- IRRRL: All borrower fees must be "Financed" not "PTC"
- Cash-Out: Include VA Cash Out Refinance Comparison form
- Max cash back (IRRRL): $500
- Attorney review fee: NOT charged to Veteran (itemize from Seller/Lender credit)
- Credit report fee: No cap per updated VA guideline

### 4.3 USDA

- Technology fee: $25 (commitment on/after 1/1/2020)
- Disclosed in Sec-B, 0% tolerance, APR fee

### 4.4 ARM Loans

- Lock Desk approval required before docs released
- Click "Get Index" button
- Check APR increase (>0.250% → escalate)
- Check Pricing change (credit for rate/discount) → escalate
- Remove Loan Modification Agreement Disclosure from package

### 4.5 Non-QM

- Eric Gut review required before release
- Usually fail High Cost on Mavent
- Investors: Acra, SG Capital, Onslow, Verus, Maxex, Deephaven
- ATR/QM Eligibility: "Exempt" = Non-QM

### 4.6 DPA Loans

- 2nd level review required for Investor fees
- Screenshot of Investor Loan Program + Reservation form required

### 4.7 Private Money / Bridge to Sale

- Non-MOM loans (no MERS)
- Balloon Note & Balloon Rider required
- 3-4 month term: Include Addendum to Note (Late Penalty)

### 4.8 Construction Loans

- Draw Schedule: Max 6 draws (additional $375/draw if exceeded)
- Construction Completion Date: 12 months from Closing
- AWM Construction Loan Program Disclosure required
- Addendum to Construction Note required

### 4.9 Buydown Loans

- Buydown Agreement required
- Buydown calculator for calculations
- Buydown funds in Sec-H, Paid to AWM
- Temporary Buydown Disclosure (from custom forms)
- Buydown Letter of Servicing required
- FHA with Buydown: ADP Code = 796
- Borrower paid buydown: Eric Gut review required

---

## 5. Branch-Specific Rules

### 5.1 Prosperity Branch (Nevada)
- No cushion months for HOI/Taxes
- No SIDS impounds

### 5.2 Florida Branch
- Credit report cap: $48.30

### 5.3 Proctor, Plano, P Moore Branch
- Final CD approval from LO/Processor before docs released
- Patrick Moore: Must be copied on all emails + approval required
- PPDocs, Inc. or Cain & Kiel attorney

### 5.4 El Paso Branch
- BM&G attorney (fee: $225)

### 5.5 Ray Lockery Branch
- Credit report not to exceed $195 (before 1/6/2025) or $260 (on/after)
- LOs: Jonathan Hunter Ross, William Denight, Jennifer Mims, Ray Lockery, Jeanne Leach, Heather Leach, Hunter Ross

### 5.6 NOTE LLC Files
- Yellow color in pipeline
- Email domains: @notemortgage.com
- Conventional: Close in NOTE LLC name (ALT-Lender = NOTE LLC)
- Government: Close in AWM name (no ALT-Lender)
- Use NOTE LLC Closing Conditions sets
- Replace Wire Fraud disclosure & Funding Letter with NOTE LLC versions
- MERS ORG ID: 1017344 (Conv), 1006909 (Govt)

---

## 6. Investor-Specific Rules

### 6.1 SGCP (Investment Occupancy)
- Prepayment Penalty applies
- Use calculator to verify amount

### 6.2 CHASE
- Exclude CHASE-prefixed docs from closing package
- ARM: Assumption = Will allow

### 6.3 Pentagon Federal Credit Union
- 4506-C Line 5a: TALX Corporation address

### 6.4 Bayview/Lakeview DSCR
- Closing Manager 2nd level review required
- Business Loan Rider (Bayview format) mandatory
- Guarantor signature on rider
- Use Investor-based PPP rider and Addendum

### 6.5 ARC DSCR
- Business Loan Rider required (if LLC)
- Guaranty Agreement required

### 6.6 CHFA
- HOI Deductible max: $5,000
- NBS not allowed
- CHFA 2nd DOT: AWM mailing info on upper left corner

### 6.7 TDHCA
- HOI Deductible: 2% of Dwelling or $2,500 (whichever higher)

### 6.8 THDA
- HOI Deductible: 1% of Loan Amount or $2,500 (whichever higher)

### 6.9 Metro DPA + Lakeview
- Flood Cert fee & Tax service fee: Paid to "Master Servicer"

### 6.10 US MRBP (NV HIP/HAL)
- HIP First Time Home Buyers: Compliance fee $225
- Other HIP & HAL: Compliance fee $275
- Tax Exempt Financing Rider NOT required (Govt HIP)

---

## 7. Disclosure Workflow (Summary)

Based on available information, Disclosure workflow appears simpler:

### Key Differences from Draw Docs:
1. **No document verifications** - just field existence checks
2. **Simpler process** overall
3. **Additional step**: Mortgage Insurance calculation

### CD Team Responsibilities:
- Buyer's Agent updates
- Seller's Agent updates
- Initial CD preparation
- COC CD preparation
- Tolerance cures

### Disclosure Process Elements Mentioned in SOP:
- Initial CD must be signed/acknowledged
- 3-day waiting period tracking
- COC CD for changes
- APR impact assessment
- Fee tolerance monitoring

---

## 8. Gap Analysis: SOP vs. Proposed Architecture

### 8.1 Coverage Summary

| SOP Section | Proposed Architecture | Gap Level |
|-------------|----------------------|-----------|
| Entry Conditions | ✅ Docs Prep Agent | Low |
| Document Download | ✅ download_documents tool | Low |
| Borrower Summary | ⚠️ Phase 1 | Medium - Missing MIN/MERS verification |
| Vesting | ⚠️ Phase 1 | High - Complex state rules |
| Trust Handling | ❌ Not explicit | High |
| Closing Conditions (PTF) | ❌ Not explicit | Critical |
| File Contacts | ⚠️ Phase 2 | Medium |
| Insurance Verification | ⚠️ Partially covered | Medium - Coverage calc needed |
| Property Information | ✅ Phase 3 | Low |
| Loan-Type Forms | ⚠️ Phase 3 | Medium - Need form handlers |
| RegZ-CD | ✅ Phase 4 | Low |
| Aggregate Escrow | ⚠️ Phase 4 | Medium - State calcs needed |
| 2015 Itemization | ✅ Phase 4 | Low |
| Fee Variance | ⚠️ Audit Agent | Medium - Cure logic needed |
| CD Pages 1-5 | ✅ Phase 5 | Low |
| Mavent/Compliance | ✅ Audit Agent | Low |
| Order Docs | ✅ Order Docs Flow | Low |
| State Rules | ❌ Not explicit | Critical |
| Error Handling | ⚠️ log_issue | Medium |
| Branch/Investor Rules | ❌ Not covered | High |

### 8.2 Critical Gaps

1. **Conditions Engine** - PTF conditions are central to the workflow
2. **State Rules Engine** - TX alone has 10+ unique requirements
3. **Trust Handling Module** - Separate complex workflow
4. **External Integrations** - MERS, USPS, Mavent, Investor portals
5. **Branch/Investor Configuration** - 120+ special rules

---

## 9. Recommendations

### 9.1 Architecture Additions

1. **Add Conditions Agent/Module**
   - Read UW conditions
   - Add new PTF conditions
   - Condition set templates
   - Condition assignment logic

2. **Create State Rules Engine**
   - Configurable rules per state
   - Endorsement selection
   - Vesting rules
   - Tax calculations
   - Attorney handling

3. **Separate Loan-Type Handlers**
   - FHA Handler (92900ALT, MIP, Case#)
   - VA Handler (Funding Fee, 26-1820, COE)
   - USDA Handler (Commitment, Tech Fee)
   - Conventional Handler (MI Cert, Cancel@78%)

4. **Build Insurance Verification Module**
   - Coverage calculations
   - Mortgagee clause validation
   - Flood zone handling

5. **Add Branch/Investor Configuration Layer**
   - Rule overrides by branch
   - Investor-specific requirements
   - Fee exceptions

6. **Define Hard Stop vs. Soft Stop Logic**
   - Escalation matrix
   - Auto-PTF vs. manual intervention
   - Approval workflows

### 9.2 Tool Additions

```python
# Suggested new tools

# Conditions Management
add_ptf_condition(loan_id, condition_text, assign_to_dept)
get_uw_conditions(loan_id, condition_type="PTF")
get_condition_sets(loan_type, purpose)

# External Verifications
verify_min_uniqueness(min_number, ssn_list)  # MERS
validate_property_address(address)  # USPS
run_mavent_compliance(loan_id)

# State-Specific
get_state_endorsements(state, property_type, amortization_type, is_home_equity)
get_state_tax_calculation(state, is_new_construction, sales_price, tax_summary_amount)
get_state_vesting_rules(state)
get_state_trustee(state, county)

# Insurance
calculate_dwelling_coverage(dwelling, erc_percent)
verify_mortgagee_clause(hoi_doc, expected_lender, loan_number)

# Branch/Investor
get_branch_exceptions(branch_id)
get_investor_requirements(investor_id, loan_type)
```

### 9.3 Phase Refinement

**Docs Prep Agent** - Add:
- MIN verification step
- Document completeness check with specific 35-doc list
- Branch/Investor identification

**Docs Draw Core Agent** - Add:
- State rules application per phase
- Condition generation logic
- Hard stop detection

**Audit & Compliance Agent** - Add:
- Fee variance/cure calculation
- Mavent integration
- Pre-Funding QC check

**Order & Distribution** - Add:
- Document filtering by state/loan type
- Branch-specific approval workflows
- Additional docs attachment logic

---

## 10. Next Steps

1. **Validate with Client** - Confirm understanding of workflow
2. **Prioritize Gaps** - Which are MVP vs. Phase 2
3. **Define Field Mappings** - Encompass field IDs for all forms
4. **Build State Rules Config** - Start with TX (most complex)
5. **Create Condition Templates** - Standard PTF conditions
6. **Design Test Scenarios** - Edge cases per loan type
7. **Prototype Critical Paths** - FHA, VA, Conventional flows

---

*Document generated from SOP analysis on November 28, 2025*

