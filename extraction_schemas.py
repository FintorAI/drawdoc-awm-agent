"""Document extraction schemas for LandingAI.

This module contains JSON schemas for extracting structured data from different
document types. Each schema defines the fields to extract and their descriptions.

REFERENCE: DrawingDoc Verifications.csv
----------------------------------------
This CSV file contains the authoritative list of documents and fields that need
to be extracted. The "Primary document" and "Secondary documents" columns indicate
which document types should have extraction schemas.

Key document types from the CSV (by frequency):
- Last LE / LE (Loan Estimate) - 30+ fields
- Final 1003 / Initial 1003 / 1003 form - 17+ fields
- Closing Disclosure / COC CD / Initial CD / Final CD - 20+ fields
- Loan file - 13+ fields
- Trust Document - 7+ fields
- Title Report / Prelim Title report - 10+ fields
- Purchase Agreement / Purchase Contract - 9+ fields
- 2015 Itemization form - 7+ fields
- Aggregate Escrow Account Form - 9+ fields
- HOI policy / Evidence of Insurance - 5+ fields
- Mortgage Insurance Certificate - 3+ fields
- Appraisal report / Appraisal - 5+ fields
- FHA Case assignment document - 2+ fields
- Escrow wire instruction - 2+ fields
- Credit report - 1+ fields
- ID (Driver's License, etc.) - 4+ fields

Usage:
    from extraction_schemas import get_extraction_schema, get_document_types_from_csv
    
    schema = get_extraction_schema("W-2")
    result = extract_document_data(file_path, schema, "W-2")
    
    # Get all document types referenced in CSV
    csv_docs = get_document_types_from_csv()
"""

from typing import Any
from pathlib import Path
import csv


# W-2 Form Schema - Tax wage and income statement
W2_SCHEMA = {
    "type": "object",
    "properties": {
        "employee_first_name": {
            "type": "string",
            "title": "Employee First Name",
            "description": "The first name of the employee from the W-2 form"
        },
        "employee_middle_name": {
            "type": "string",
            "title": "Employee Middle Name",
            "description": "The middle name or initial of the employee from the W-2 form"
        },
        "employee_last_name": {
            "type": "string",
            "title": "Employee Last Name",
            "description": "The last name of the employee from the W-2 form"
        },
        "employer_name": {
            "type": "string",
            "title": "Employer Name",
            "description": "The name of the employer/company from the W-2 form"
        },
        "tax_year": {
            "type": "string",
            "title": "Tax Year",
            "description": "The tax year for this W-2 form"
        }
    }
}


# ID Document Schema (Driver's License, State ID, etc.)
ID_SCHEMA = {
    "type": "object",
    "properties": {
        "first_name": {
            "type": "string",
            "title": "First Name",
            "description": "The first name from the ID document"
        },
        "middle_name": {
            "type": "string",
            "title": "Middle Name",
            "description": "The middle name or initial from the ID document"
        },
        "last_name": {
            "type": "string",
            "title": "Last Name",
            "description": "The last name from the ID document"
        },
        "date_of_birth": {
            "type": "string",
            "title": "Date of Birth",
            "description": "The date of birth from the ID document"
        },
        "ssn": {
            "type": "string",
            "title": "Social Security Number",
            "description": "The SSN from the ID document if present"
        },
        "address": {
            "type": "string",
            "title": "Address",
            "description": "The address from the ID document"
        },
    }
}

# Title Report Schema
TITLE_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "escrow_company_name": {
            "type": "string",
            "title": "Escrow Company Name",
            "description": "The name of the escrow company from the title report"
        },
        "title_company_name": {
            "type": "string",
            "title": "Title Insurance Company Name",
            "description": "The name of the title insurance company"
        },
        "escrow_number": {
            "type": "string",
            "title": "Escrow Number",
            "description": "The escrow case number"
        },
        "property_address": {
            "type": "string",
            "title": "Property Address",
            "description": "The property address from the title report"
        },
        "parcel_number": {
            "type": "string",
            "title": "Parcel Number",
            "description": "The parcel number from the title report"
        },
    }
}

# Appraisal Report Schema
APPRAISAL_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "appraised_value": {
            "type": "number",
            "title": "Appraised Value",
            "description": "The appraised value of the property"
        },
        "property_address": {
            "type": "string",
            "title": "Property Address",
            "description": "The property address from the appraisal"
        },
        "appraisal_date": {
            "type": "string",
            "title": "Appraisal Date",
            "description": "The date of the appraisal"
        },
        "appraiser_name": {
            "type": "string",
            "title": "Appraiser Name",
            "description": "The name of the appraiser"
        },
    }
}

# Final 1003 / Initial 1003 Schema (Uniform Residential Loan Application)
FORM_1003_SCHEMA = {
    "type": "object",
    "properties": {
        "borrower_first_name": {
            "type": "string",
            "title": "Borrower First Name",
            "description": "Borrower's first name from the 1003 form"
        },
        "borrower_middle_name": {
            "type": "string",
            "title": "Borrower Middle Name",
            "description": "Borrower's middle name from the 1003 form"
        },
        "borrower_last_name": {
            "type": "string",
            "title": "Borrower Last Name",
            "description": "Borrower's last name from the 1003 form"
        },
        "borrower_firstmiddle_name": {
            "type": "string",
            "title": "Borrower First/Middle Name",
            "description": "Borrower first/middle name (Field ID: 36)"
        },
        "borrower_business_phone": {
            "type": "string",
            "title": "Borrower Business Phone",
            "description": "Borrower business phone (Field ID: FE0117)"
        },
        "borrower_ssn": {
            "type": "string",
            "title": "Borrower SSN",
            "description": "Borrower Social Security Number (Field ID: 65)"
        },
        "co_borrower_first_name": {
            "type": "string",
            "title": "Co-Borrower First Name",
            "description": "Co-borrower's first name from the 1003 form"
        },
        "co_borrower_last_name": {
            "type": "string",
            "title": "Co-Borrower Last Name",
            "description": "Co-borrower's last name from the 1003 form"
        },
        "property_address": {
            "type": "string",
            "title": "Property Address",
            "description": "Subject property address from the 1003 form"
        },
        "property_city": {
            "type": "string",
            "title": "Property City",
            "description": "Subject property city from the 1003 form"
        },
        "property_state": {
            "type": "string",
            "title": "Property State",
            "description": "Subject property state from the 1003 form"
        },
        "subject_property_type": {
            "type": "string",
            "title": "Subject Property Type",
            "description": "Subject property type (Field ID: 1041 | 1553 | HMDA.X11)"
        },
        "loan_amount": {
            "type": "number",
            "title": "Loan Amount",
            "description": "Loan amount from the 1003 form"
        },
        "loan_number": {
            "type": "string",
            "title": "Loan Number",
            "description": "Loan number (Field ID: 364)"
        },
        "purchase_price": {
            "type": "number",
            "title": "Purchase Price",
            "description": "Purchase price from the 1003 form"
        },
        "loan_purpose": {
            "type": "string",
            "title": "Loan Purpose",
            "description": "Purpose of the loan (Purchase, Refinance, etc.)"
        },
        "loan_type": {
            "type": "string",
            "title": "Loan Type",
            "description": "Type of loan (Conventional, FHA, VA, etc.)"
        },
        "loan_term": {
            "type": "string",
            "title": "Loan Term",
            "description": "Loan term (Field ID: 1347)"
        },
        "loan_info_refi_purpose": {
            "type": "string",
            "title": "Loan Info Refi Purpose",
            "description": "Loan refinance purpose (Field ID: 299)"
        },
        "amortization_type": {
            "type": "string",
            "title": "Amortization Type",
            "description": "Amortization type (Fixed, ARM, etc.)"
        },
        "lien_position": {
            "type": "string",
            "title": "Lien Position",
            "description": "Lien position (Field ID: 420)"
        },
        "agency_case": {
            "type": "string",
            "title": "Agency Case #",
            "description": "Agency case number for FHA/VA (Field ID: 1040)"
        },
        "application_date": {
            "type": "string",
            "title": "Application Date",
            "description": "Loan application date"
        },
    }
}

# Last LE / LE (Loan Estimate) Schema
LOAN_ESTIMATE_SCHEMA = {
    "type": "object",
    "properties": {
        "loan_amount": {
            "type": "number",
            "title": "Loan Amount",
            "description": "Loan amount from the Loan Estimate (Field ID: 1109)"
        },
        "interest_rate": {
            "type": "number",
            "title": "Interest Rate",
            "description": "Interest rate from the Loan Estimate"
        },
        "apr": {
            "type": "number",
            "title": "APR",
            "description": "Annual Percentage Rate from the Loan Estimate"
        },
        "monthly_payment": {
            "type": "number",
            "title": "Monthly Payment",
            "description": "Monthly principal and interest payment (Expenses Proposed Mtg Pymt, Field ID: 228)"
        },
        "expenses_proposed_mtg_pymt": {
            "type": "number",
            "title": "Expenses Proposed Mtg Pymt",
            "description": "Monthly mortgage payment (Field ID: 228)"
        },
        "expenses_proposed_haz_ins": {
            "type": "number",
            "title": "Expenses Proposed Haz Ins",
            "description": "Hazard insurance amount (Field ID: 230)"
        },
        "total_closing_costs": {
            "type": "number",
            "title": "Total Closing Costs",
            "description": "Total closing costs from the Loan Estimate (CD3 Total Closing Cost J, Field ID: CD3.X82)"
        },
        "cd3_total_closing_cost_j": {
            "type": "number",
            "title": "CD3 Total Closing Cost J",
            "description": "Total closing costs (Field ID: CD3.X82)"
        },
        "lender_credits": {
            "type": "number",
            "title": "Lender Credits",
            "description": "Lender credits from the Loan Estimate"
        },
        "cash_to_close": {
            "type": "number",
            "title": "Cash to Close",
            "description": "Total cash required to close"
        },
        "closing_costs_financed": {
            "type": "number",
            "title": "Closing Costs Financed",
            "description": "Closing costs financed (Field ID: LE2.X1)"
        },
        "loan_estimate_down_paymentfunds_from_borrower": {
            "type": "number",
            "title": "Loan Estimate - Down Payment/Funds from Borrower",
            "description": "Down payment/funds from borrower (Field ID: LE2.X2)"
        },
        "loan_estimate_seller_credit_amount": {
            "type": "number",
            "title": "Loan Estimate - Seller Credit Amount",
            "description": "Seller credit amount (Field ID: LE2.X100)"
        },
        "loan_estimate_adjustments_and_other_credits": {
            "type": "number",
            "title": "Loan Estimate Adjustments and Other Credits",
            "description": "Adjustments and other credits (Field ID: LE2.X4)"
        },
        "loan_estimate_funds_for_borrower": {
            "type": "number",
            "title": "Loan Estimate Funds for Borrower",
            "description": "Funds for borrower (Field ID: LE2.X3)"
        },
        "amort_type_arm_descr": {
            "type": "string",
            "title": "Amort Type ARM Descr",
            "description": "ARM description (Field ID: 995)"
        },
        "first_rate_adjustment_cap": {
            "type": "string",
            "title": "First Rate Adjustment Cap",
            "description": "First rate adjustment cap (Field ID: 697)"
        },
        "fees_va_fund_fee_apr": {
            "type": "string",
            "title": "Fees VA Fund Fee APR",
            "description": "VA funding fee APR (Field ID: SYS.X29)"
        },
        "lock_date": {
            "type": "string",
            "title": "Lock Date",
            "description": "Rate lock date (Field ID: 761)"
        },
        "lock_expiration_date": {
            "type": "string",
            "title": "Lock Expiration Date",
            "description": "Rate lock expiration date (Field ID: 762)"
        },
        "std_final_deposit": {
            "type": "number",
            "title": "STD Final Deposit",
            "description": "Final deposit amount (Field ID: CD3.X106)"
        },
    }
}

# Closing Disclosure Schema
CLOSING_DISCLOSURE_SCHEMA = {
    "type": "object",
    "properties": {
        "closing_date": {
            "type": "string",
            "title": "Closing Date",
            "description": "Date of closing from the Closing Disclosure (Field ID: 748)"
        },
        "loan_amount": {
            "type": "number",
            "title": "Loan Amount",
            "description": "Loan amount from the Closing Disclosure (Field ID: 1109)"
        },
        "apr": {
            "type": "number",
            "title": "APR",
            "description": "Annual Percentage Rate from the Closing Disclosure (Field ID: 799)"
        },
        "total_closing_costs": {
            "type": "number",
            "title": "Total Closing Costs",
            "description": "Total closing costs from the Closing Disclosure (CD3 Total Closing Cost J, Field ID: CD3.X82)"
        },
        "cd3_total_closing_cost_j": {
            "type": "number",
            "title": "CD3 Total Closing Cost J",
            "description": "Total closing costs (Field ID: CD3.X82)"
        },
        "closing_disclosure_j_total_closing_costs_borrower_paid": {
            "type": "number",
            "title": "Closing disclosure - J. Total Closing Costs (BORROWER Paid)",
            "description": "Total closing costs borrower paid (Field ID: CD2.XSTJ)"
        },
        "cash_to_close": {
            "type": "number",
            "title": "Cash to Close",
            "description": "Total cash required to close (Closing Disclosure - Total Cash To Close, Field ID: CD1.X69)"
        },
        "closing_disclosure_total_cash_to_close": {
            "type": "number",
            "title": "Closing Disclosure - Total Cash To Close",
            "description": "Total cash to close (Field ID: CD1.X69)"
        },
        "lender_credits": {
            "type": "number",
            "title": "Lender Credits",
            "description": "Lender credits from the Closing Disclosure (Closing disclosure Lender Credits At closing, Field ID: CD2.X1)"
        },
        "closing_disclosure_lender_credits_at_closing": {
            "type": "number",
            "title": "Closing disclosure Lender Credits At closing",
            "description": "Lender credits at closing (Field ID: CD2.X1)"
        },
        "loan_costs": {
            "type": "number",
            "title": "Loan Costs",
            "description": "Loan costs (Field ID: CD2.XSTD)"
        },
        "other_costs": {
            "type": "number",
            "title": "Other Costs",
            "description": "Other costs (Field ID: CD2.XSTI)"
        },
        "late_charge": {
            "type": "string",
            "title": "Late Charge %",
            "description": "Late charge percentage (Field ID: 674)"
        },
        "impounds_waived": {
            "type": "string",
            "title": "Impounds Waived",
            "description": "Impounds waived indicator (Field ID: 2293)"
        },
        "negative_amortization": {
            "type": "string",
            "title": "Negative Amortization",
            "description": "Negative amortization indicator (Field ID: CD4.X2)"
        },
        "partial_payments_apply_partial_payment": {
            "type": "string",
            "title": "Partial Payments - Apply Partial Payment",
            "description": "Partial payments indicator (Field ID: CD4.X3)"
        },
    }
}

# Trust Document Schema
TRUST_DOCUMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "trust_name": {
            "type": "string",
            "title": "Trust Name",
            "description": "Name of the trust from the trust document"
        },
        "trust_date": {
            "type": "string",
            "title": "Trust Date",
            "description": "Date the trust was established"
        },
        "trust_state": {
            "type": "string",
            "title": "Trust State",
            "description": "State where the trust was established"
        },
        "trust_type": {
            "type": "string",
            "title": "Trust Type",
            "description": "Type of trust (e.g., Inter Vivos Trust)"
        },
        "beneficiaries": {
            "type": "string",
            "title": "Beneficiaries",
            "description": "Trust beneficiaries if listed"
        },
        "trustee_name": {
            "type": "string",
            "title": "Trustee Name",
            "description": "Name of the trustee"
        },
    }
}

# Purchase Agreement Schema
PURCHASE_AGREEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "purchase_price": {
            "type": "number",
            "title": "Purchase Price",
            "description": "Purchase price from the purchase agreement"
        },
        "property_address": {
            "type": "string",
            "title": "Property Address",
            "description": "Property address from the purchase agreement"
        },
        "seller_name": {
            "type": "string",
            "title": "Seller Name",
            "description": "Name of the seller from the purchase agreement"
        },
        "buyer_name": {
            "type": "string",
            "title": "Buyer Name",
            "description": "Name of the buyer from the purchase agreement"
        },
        "closing_date": {
            "type": "string",
            "title": "Closing Date",
            "description": "Expected closing date from the purchase agreement"
        },
        "seller_credit_amount": {
            "type": "number",
            "title": "Seller Credit Amount",
            "description": "Seller credit amount if any"
        },
    }
}

# Aggregate Escrow Account Form Schema
AGGREGATE_ESCROW_SCHEMA = {
    "type": "object",
    "properties": {
        "closing_disclosure_projected_calculation_column_1_estimated_escrow_amount": {
            "type": "string",
            "title": "Closing Disclosure - Projected Calculation - Column 1 - Estimated Escrow Amount",
            "description": "Estimated escrow amount (Field ID: CD1.X12)"
        },
        "fees_flood_ins_premium_borr": {
            "type": "string",
            "title": "Fees Flood Ins Premium Borr",
            "description": "Flood insurance premium borrower (Field ID: 643)"
        },
        "fees_hazard_ins_per_mo": {
            "type": "string",
            "title": "Fees Hazard Ins Per Mo",
            "description": "Hazard insurance per month (Field ID: 235)"
        },
        "fees_mortgage_ins_premium_borr": {
            "type": "string",
            "title": "Fees Mortgage Ins Premium Borr",
            "description": "Mortgage insurance premium borrower (Field ID: 337)"
        },
        "fees_tax_borr": {
            "type": "string",
            "title": "Fees Tax Borr",
            "description": "Tax borrower (Field ID: 655)"
        },
    }
}

# 2015 Itemization Form Schema
ITEMIZATION_2015_SCHEMA = {
    "type": "object",
    "properties": {
        "closing_cost_program": {
            "type": "string",
            "title": "Closing Cost Program",
            "description": "Closing cost program (Field ID: 1785)"
        },
        "fees_mortgage_ins_of_mos": {
            "type": "string",
            "title": "Fees Mortgage Ins # of Mos",
            "description": "Mortgage insurance number of months (Field ID: 1296)"
        },
        "fees_section_1000_borrower_paid_total_amount": {
            "type": "string",
            "title": "Fees Section 1000 Borrower Paid Total Amount",
            "description": "Section 1000 borrower paid total (Field ID: NEWHUD.X1719)"
        },
        "loan_program": {
            "type": "string",
            "title": "Loan Program",
            "description": "Loan program (Field ID: 1401)"
        },
    }
}

# HOI Policy Schema (Homeowner's Insurance Policy)
HOI_POLICY_SCHEMA = {
    "type": "object",
    "properties": {
        "expenses_proposed_haz_ins": {
            "type": "string",
            "title": "Expenses Proposed Haz Ins",
            "description": "Proposed hazard insurance (Field ID: 230)"
        },
        "fees_homeowners_ins_premium_paid_to": {
            "type": "string",
            "title": "Fees Homeowners Ins Premium Paid To",
            "description": "Homeowners insurance premium paid to (Field ID: SYS.X308)"
        },
    }
}

# Mortgage Insurance Details Schema
MORTGAGE_INSURANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "expenses_proposed_mtg_ins": {
            "type": "string",
            "title": "Expenses Proposed Mtg Ins",
            "description": "Proposed mortgage insurance (Field ID: 232)"
        },
        "fees_va_fund_fee_borr": {
            "type": "string",
            "title": "Fees VA Fund Fee Borr",
            "description": "VA funding fee borrower (Field ID: 1050)"
        },
        "insurance_mtg_ins_upfront_factor": {
            "type": "string",
            "title": "Insurance Mtg Ins Upfront Factor",
            "description": "Mortgage insurance upfront factor (Field ID: 1107)"
        },
    }
}

# Loan File Schema
LOAN_FILE_SCHEMA = {
    "type": "object",
    "properties": {
        "amortization_type": {
            "type": "string",
            "title": "Amortization Type",
            "description": "Amortization type (Field ID: 608)"
        },
        "borrower_first_name": {
            "type": "string",
            "title": "Borrower First Name",
            "description": "Borrower first name (Field ID: 4000)"
        },
        "cd_changed_circumstance_chkbx": {
            "type": "string",
            "title": "CD Changed Circumstance Chkbx",
            "description": "CD changed circumstance checkbox (Field ID: CD1.X61)"
        },
        "closing_date": {
            "type": "string",
            "title": "Closing Date",
            "description": "Closing date (Field ID: 748)"
        },
        "investor_name": {
            "type": "string",
            "title": "Investor Name",
            "description": "Investor name (Field ID: VEND.X263)"
        },
        "lender_case": {
            "type": "string",
            "title": "Lender Case #",
            "description": "Lender case number (Field ID: 305)"
        },
        "loan_number": {
            "type": "string",
            "title": "Loan Number",
            "description": "Loan number (Field ID: 364)"
        },
        "loan_purpose": {
            "type": "string",
            "title": "Loan Purpose",
            "description": "Loan purpose (Field ID: 384)"
        },
        "loan_type": {
            "type": "string",
            "title": "Loan Type",
            "description": "Loan type (Field ID: 1172)"
        },
        "ltv": {
            "type": "string",
            "title": "LTV",
            "description": "Loan-to-value ratio (Field ID: 353)"
        },
        "occupancy_type": {
            "type": "string",
            "title": "Occupancy Type",
            "description": "Occupancy type (Field ID: 3335)"
        },
        "subject_property_state": {
            "type": "string",
            "title": "Subject Property State",
            "description": "Subject property state (Field ID: 14)"
        },
        "total_loan_amount": {
            "type": "string",
            "title": "Total Loan Amount",
            "description": "Total loan amount (Field ID: 2)"
        },
    }
}

# FHA Case Assignment Document Schema
FHA_CASE_SCHEMA = {
    "type": "object",
    "properties": {
        "agency_case": {
            "type": "string",
            "title": "Agency Case #",
            "description": "Agency case number (Field ID: 1040)"
        },
    }
}

# Escrow Wire Instruction Schema
ESCROW_WIRE_SCHEMA = {
    "type": "object",
    "properties": {
        "overwire_amount": {
            "type": "string",
            "title": "Overwire Amount",
            "description": "Overwire amount (Field ID: 2005)"
        },
    }
}

# Credit Report Schema
CREDIT_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "also_known_as_aka": {
            "type": "string",
            "title": "Also Known As (AKA)",
            "description": "Also known as or AKA name"
        },
    }
}

# Document type registry - maps document types to their schemas
DOCUMENT_SCHEMAS = {
    "W-2": W2_SCHEMA,
    "W2": W2_SCHEMA,  # Alternative naming
    "W-2 Form": W2_SCHEMA,
    # ID Documents
    "ID": ID_SCHEMA,
    "Driver License": ID_SCHEMA,
    "Driver's License": ID_SCHEMA,
    "State ID": ID_SCHEMA,
    # Title Documents
    "Title Report": TITLE_REPORT_SCHEMA,
    "Prelim Title Report": TITLE_REPORT_SCHEMA,
    "Preliminary Title Report": TITLE_REPORT_SCHEMA,
    "Title report": TITLE_REPORT_SCHEMA,
    # Appraisal Documents
    "Appraisal Report": APPRAISAL_REPORT_SCHEMA,
    "Appraisal": APPRAISAL_REPORT_SCHEMA,
    "Appraisal report": APPRAISAL_REPORT_SCHEMA,
    # 1003 Forms
    "Final 1003": FORM_1003_SCHEMA,
    "Initial 1003": FORM_1003_SCHEMA,
    "1003": FORM_1003_SCHEMA,
    "1003 form": FORM_1003_SCHEMA,
    "Uniform Residential Loan Application": FORM_1003_SCHEMA,
    # Loan Estimate
    "Last LE": LOAN_ESTIMATE_SCHEMA,
    "LE": LOAN_ESTIMATE_SCHEMA,
    "LE (Loan Estimate)": LOAN_ESTIMATE_SCHEMA,
    "Loan Estimate": LOAN_ESTIMATE_SCHEMA,
    # Closing Disclosure
    "Closing Disclosure": CLOSING_DISCLOSURE_SCHEMA,
    "COC CD": CLOSING_DISCLOSURE_SCHEMA,
    "Initial CD": CLOSING_DISCLOSURE_SCHEMA,
    "Final CD": CLOSING_DISCLOSURE_SCHEMA,
    # Trust Documents
    "Trust Document": TRUST_DOCUMENT_SCHEMA,
    "Trust Agreement": TRUST_DOCUMENT_SCHEMA,
    # Purchase Documents
    "Purchase Agreement": PURCHASE_AGREEMENT_SCHEMA,
    "Purchase Contract": PURCHASE_AGREEMENT_SCHEMA,
    # Aggregate Escrow Account Form
    "Aggregate Escrow Account Form": AGGREGATE_ESCROW_SCHEMA,
    "Aggregate Escrow Account form": AGGREGATE_ESCROW_SCHEMA,
    "Aggregate Escrow Statement": AGGREGATE_ESCROW_SCHEMA,
    # 2015 Itemization Form
    "2015 Itemization form": ITEMIZATION_2015_SCHEMA,
    "2015 Itemization Form": ITEMIZATION_2015_SCHEMA,
    # HOI Policy
    "HOI Policy": HOI_POLICY_SCHEMA,
    "HOI policy": HOI_POLICY_SCHEMA,
    "Evidence of Insurance": HOI_POLICY_SCHEMA,
    "Hazard Insurance policy": HOI_POLICY_SCHEMA,
    # Mortgage Insurance
    "Mortgage Insurance details": MORTGAGE_INSURANCE_SCHEMA,
    "Mortgage Insurance Certificate": MORTGAGE_INSURANCE_SCHEMA,
    # Loan File
    "Loan file": LOAN_FILE_SCHEMA,
    "Loan File": LOAN_FILE_SCHEMA,
    # FHA Case
    "FHA Case assignment document": FHA_CASE_SCHEMA,
    "FHA Case Assignment number document": FHA_CASE_SCHEMA,
    # Escrow Wire
    "Escrow wire instruction": ESCROW_WIRE_SCHEMA,
    "Escrow Wire Instruction": ESCROW_WIRE_SCHEMA,
    # Credit Report
    "Credit report": CREDIT_REPORT_SCHEMA,
    "Credit Report": CREDIT_REPORT_SCHEMA,
}


def get_extraction_schema(document_type: str) -> dict[str, Any]:
    """Get the extraction schema for a specific document type.
    
    Args:
        document_type: The type of document (e.g., "W-2", "Bank Statement", "1003")
        
    Returns:
        JSON schema dict for extracting data from that document type
        
    Raises:
        ValueError: If document type is not supported
        
    Example:
        >>> schema = get_extraction_schema("W-2")
        >>> result = extract_document_data(file_path, schema, "W-2")
    """
    # Normalize document type (case-insensitive lookup)
    normalized_type = document_type.strip()
    
    # Try exact match first
    if normalized_type in DOCUMENT_SCHEMAS:
        return DOCUMENT_SCHEMAS[normalized_type]
    
    # Try case-insensitive match
    for key, schema in DOCUMENT_SCHEMAS.items():
        if key.lower() == normalized_type.lower():
            return schema
    
    # Document type not found
    available_types = list(DOCUMENT_SCHEMAS.keys())
    raise ValueError(
        f"No extraction schema found for document type '{document_type}'. "
        f"Available types: {', '.join(available_types)}"
    )


def list_supported_document_types() -> list[str]:
    """Get list of all supported document types.
    
    Returns:
        List of document type names that have extraction schemas
        
    Example:
        >>> types = list_supported_document_types()
        >>> print(f"Supported: {', '.join(types)}")
    """
    return list(DOCUMENT_SCHEMAS.keys())


def get_document_types_from_csv() -> list[str]:
    """Get all document types referenced in DrawingDoc Verifications.csv.
    
    This function parses the CSV file to extract all unique document types
    mentioned in the "Primary document" and "Secondary documents" columns.
    
    Returns:
        List of document type names from the CSV
        
    Example:
        >>> csv_docs = get_document_types_from_csv()
        >>> print(f"Documents in CSV: {len(csv_docs)}")
    """
    csv_path = Path(__file__).parent / "DrawingDoc Verifications.csv"
    
    if not csv_path.exists():
        return []
    
    documents = set()
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Get primary document
                primary = row.get('Primary document', '').strip()
                if primary:
                    documents.add(primary)
                
                # Get secondary documents (split by semicolon and comma)
                secondary = row.get('Secondary documents', '').strip()
                if secondary:
                    for doc in secondary.replace(';', ',').split(','):
                        doc = doc.strip()
                        if doc and doc not in ['', 'N/A']:
                            documents.add(doc)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return []
    
    # Filter out non-document types (system references, etc.)
    filtered = []
    exclude_prefixes = [
        'Encompass Tools',
        'File Contacts',
        'Mavent report',
        'SOP requirement',
        'Fee classification',
        'Documents tab',
        'Lender location',
    ]
    
    for doc in sorted(documents):
        if not any(doc.startswith(prefix) for prefix in exclude_prefixes):
            filtered.append(doc)
    
    return filtered


def get_fields_for_document_type(document_type: str) -> list[dict]:
    """Get all fields that should be extracted from a specific document type.
    
    This function reads DrawingDoc Verifications.csv and returns all fields
    where the document type appears in "Primary document" or "Secondary documents".
    
    Args:
        document_type: The document type to look up (e.g., "Final 1003", "W-2")
        
    Returns:
        List of dictionaries with field information:
        [
            {
                "name": "Field Name",
                "id": "Encompass Field ID",
                "primary": True/False,
                "notes": "Verification notes"
            },
            ...
        ]
        
    Example:
        >>> fields = get_fields_for_document_type("Final 1003")
        >>> print(f"Found {len(fields)} fields for Final 1003")
    """
    csv_path = Path(__file__).parent / "DrawingDoc Verifications.csv"
    
    if not csv_path.exists():
        return []
    
    fields = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                field_name = row.get('Name', '').strip()
                field_id = row.get('ID', '').strip()
                primary_doc = row.get('Primary document', '').strip()
                secondary_docs = row.get('Secondary documents', '').strip()
                notes = row.get('Notes', '').strip()
                
                # Check if document type matches
                is_primary = document_type.lower() in primary_doc.lower() if primary_doc else False
                is_secondary = document_type.lower() in secondary_docs.lower() if secondary_docs else False
                
                if is_primary or is_secondary:
                    fields.append({
                        "name": field_name,
                        "id": field_id,
                        "primary": is_primary,
                        "notes": notes,
                    })
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return []
    
    return fields

