"""
Discrepancy Detection Rules

Automatically detects discrepancies between extracted field values and Encompass values,
categorizes them as HARD STOPS vs SOFT (PTF), and generates appropriate condition text.

Based on: 
- Docs Draw SOP (1).docx
- discovery/sop_workflow_analysis.md
- DrawingDoc Verifications.csv
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import re


class DiscrepancySeverity(str, Enum):
    """Severity levels for discrepancies"""
    HARD_STOP = "hard_stop"  # Halt pipeline, escalate immediately
    PTF = "ptf"  # Proceed to Fund - add condition, continue
    INFO = "info"  # Log only, no action needed
    IGNORE = "ignore"  # Known acceptable variance


class DiscrepancyCategory(str, Enum):
    """Categories for PTF conditions"""
    MISSING_DOC = "Missing Document"
    DATA_DISCREPANCY = "Data Discrepancy"
    INSURANCE = "Insurance Issue"
    VESTING = "Vesting Issue"
    PROPERTY = "Property Information"
    BORROWER = "Borrower Information"
    FINANCIAL = "Financial Discrepancy"
    OTHER = "Other"


# ============================================================================
# HARD STOP RULES (From SOP - discovery/sop_workflow_analysis.md lines 768-780)
# ============================================================================

HARD_STOP_FIELDS = {
    "1109": {  # Loan Amount
        "field_name": "Loan Amount",
        "tolerance": 0,  # NO tolerance
        "rule": "Loan Amount mismatch between documents and Encompass",
        "action": "HARD STOP - Contact Team Lead immediately",
        "category": DiscrepancyCategory.FINANCIAL
    },
    "3": {  # Interest Rate
        "field_name": "Interest Rate",
        "tolerance": 0,  # NO tolerance
        "rule": "Interest Rate mismatch between Final Approval and Encompass",
        "action": "HARD STOP - Contact Team Lead immediately",
        "category": DiscrepancyCategory.FINANCIAL
    },
    "578": {  # Hazard Insurance Premium
        "field_name": "Monthly Hazard Insurance",
        "tolerance": 0,  # NO tolerance on UW-approved amounts
        "rule": "Monthly Hazard Insurance discrepancy with UW Final Approval",
        "action": "HARD STOP - Get revised Final Approval from UW (NO PTF allowed)",
        "category": DiscrepancyCategory.INSURANCE
    },
    "231": {  # Property Tax Monthly
        "field_name": "Monthly Property Tax",
        "tolerance": 0,  # NO tolerance on UW-approved amounts
        "rule": "Monthly Property Tax discrepancy with UW Final Approval",
        "action": "HARD STOP - Get revised Final Approval from UW (NO PTF allowed)",
        "category": DiscrepancyCategory.FINANCIAL
    },
    # TODO: Add ARM Lock Desk check field
    # TODO: Add Non-QM Eric Gut review field
    # TODO: Add Pre-Funding QC flag field
}


# ============================================================================
# SOFT DISCREPANCY RULES (Add PTF, Continue)
# ============================================================================

SOFT_DISCREPANCY_FIELDS = {
    "11": {  # Borrower First Name
        "field_name": "Borrower First Name",
        "tolerance": "spelling_match",
        "ignore_middle_initial": True,
        "rule": "Borrower First Name mismatch between documents",
        "ptf_template": "PTF - Verify Borrower First Name: Document shows '{extracted}', Encompass shows '{encompass}'. Source: {source_doc}",
        "category": DiscrepancyCategory.BORROWER,
        "assigned_to": "Loan Processor"
    },
    "12": {  # Borrower Last Name
        "field_name": "Borrower Last Name",
        "tolerance": "spelling_match",
        "rule": "Borrower Last Name mismatch between documents",
        "ptf_template": "PTF - Verify Borrower Last Name: Document shows '{extracted}', Encompass shows '{encompass}'. Source: {source_doc}",
        "category": DiscrepancyCategory.BORROWER,
        "assigned_to": "Loan Processor"
    },
    # "FR0104": {  # Borrower Present Address - REMOVED: Field deprecated in new verification file
    #     "field_name": "Borrower Present Address",
    #     "tolerance": "address_fuzzy",
    #     "rule": "Borrower Present Address format difference",
    #     "ptf_template": "PTF - Verify Borrower Present Address: Document shows '{extracted}', Encompass shows '{encompass}'. Source: {source_doc}",
    #     "category": DiscrepancyCategory.BORROWER,
    #     "assigned_to": "Loan Processor"
    # },
    "15": {  # Subject Property Address
        "field_name": "Subject Property Address",
        "tolerance": "address_fuzzy",  # Allow "Dr" vs "Drive"
        "rule": "Property Address format mismatch (acceptable if suffix only)",
        "ptf_template": "PTF - Property address format mismatch - verify with title report. Document: '{extracted}', Encompass: '{encompass}'",
        "category": DiscrepancyCategory.PROPERTY,
        "assigned_to": "Loan Processor"
    },
    "4004": {  # Co-Borrower First Name
        "field_name": "Co-Borrower First Name",
        "tolerance": "spelling_match",
        "ignore_middle_initial": True,
        "rule": "Co-Borrower First Name mismatch",
        "ptf_template": "PTF - Verify Co-Borrower First Name: Document shows '{extracted}', Encompass shows '{encompass}'. Source: {source_doc}",
        "category": DiscrepancyCategory.BORROWER,
        "assigned_to": "Loan Processor"
    },
}


# ============================================================================
# ACCEPTABLE VARIANCES (From SOP - context/docs_draw_sop.md lines 1382-1391)
# ============================================================================

ACCEPTABLE_VARIANCES = {
    "middle_initial": {
        "rule": "Missing middle initials on HOI/Contract/Appraisal are acceptable",
        "applies_to": ["Contract", "Appraisal", "HOI Policy"],
        "severity": DiscrepancySeverity.IGNORE
    },
    "address_suffix": {
        "rule": "Missing address suffix (DR, AVE, ST) on contract is acceptable",
        "applies_to": ["Contract"],
        "pattern": r"\b(DR|DRIVE|AVE|AVENUE|ST|STREET|RD|ROAD|LN|LANE|BLVD|BOULEVARD)\b",
        "severity": DiscrepancySeverity.IGNORE
    },
    "co_borrower_on_va_appraisal": {
        "rule": "VA appraisals only require veteran borrower name",
        "applies_to": ["Appraisal"],
        "loan_type": "VA",
        "severity": DiscrepancySeverity.IGNORE
    }
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def normalize_string(value: str) -> str:
    """Normalize string for comparison"""
    if not value:
        return ""
    return re.sub(r'\s+', ' ', value.strip().upper())


def compare_addresses(extracted: str, encompass: str) -> Tuple[bool, Optional[str]]:
    """
    Compare addresses with fuzzy matching for acceptable variances
    
    Returns:
        (is_match, difference_description)
    """
    if not extracted or not encompass:
        return False, "One address is empty"
    
    # Normalize both
    ext_norm = normalize_string(extracted)
    enc_norm = normalize_string(encompass)
    
    # Exact match
    if ext_norm == enc_norm:
        return True, None
    
    # Check if only difference is suffix (DR vs DRIVE)
    address_suffixes = {
        "DR": "DRIVE",
        "DRIVE": "DR",
        "AVE": "AVENUE",
        "AVENUE": "AVE",
        "ST": "STREET",
        "STREET": "ST",
        "RD": "ROAD",
        "ROAD": "RD",
        "LN": "LANE",
        "LANE": "LN",
        "BLVD": "BOULEVARD",
        "BOULEVARD": "BLVD",
    }
    
    for short, long in address_suffixes.items():
        if ext_norm.replace(short, long) == enc_norm or ext_norm == enc_norm.replace(short, long):
            return True, None  # Acceptable variance
    
    # Substantive difference
    return False, f"Address mismatch: '{extracted}' vs '{encompass}'"


def compare_names(extracted: str, encompass: str, ignore_middle_initial: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Compare names with tolerance for middle initials
    
    Returns:
        (is_match, difference_description)
    """
    if not extracted or not encompass:
        return False, "One name is empty"
    
    ext_norm = normalize_string(extracted)
    enc_norm = normalize_string(encompass)
    
    # Exact match
    if ext_norm == enc_norm:
        return True, None
    
    # If ignore middle initial, remove single letters
    if ignore_middle_initial:
        ext_no_mi = re.sub(r'\b[A-Z]\b', '', ext_norm).strip()
        enc_no_mi = re.sub(r'\b[A-Z]\b', '', enc_norm).strip()
        
        if ext_no_mi == enc_no_mi:
            return True, None  # Only middle initial difference
    
    # Name mismatch
    return False, f"Name mismatch: '{extracted}' vs '{encompass}'"


def compare_amounts(extracted: Any, encompass: Any, tolerance: float = 0) -> Tuple[bool, Optional[str]]:
    """
    Compare monetary amounts with optional tolerance
    
    Args:
        tolerance: Maximum acceptable difference (0 = no tolerance)
    
    Returns:
        (is_match, difference_description)
    """
    try:
        # Convert to float
        ext_val = float(str(extracted).replace('$', '').replace(',', ''))
        enc_val = float(str(encompass).replace('$', '').replace(',', ''))
        
        diff = abs(ext_val - enc_val)
        
        if diff <= tolerance:
            return True, None
        
        return False, f"Amount mismatch: ${ext_val:,.2f} vs ${enc_val:,.2f} (diff: ${diff:,.2f})"
    
    except (ValueError, TypeError):
        return False, f"Cannot compare amounts: '{extracted}' vs '{encompass}'"


def generate_ptf_condition_text(
    field_id: str,
    field_name: str,
    extracted_value: str,
    encompass_value: str,
    source_doc: str,
    custom_message: Optional[str] = None
) -> str:
    """
    Generate PTF condition text automatically
    
    Uses templates from SOFT_DISCREPANCY_FIELDS or creates a generic one
    """
    rule = SOFT_DISCREPANCY_FIELDS.get(field_id)
    
    if rule and "ptf_template" in rule:
        return rule["ptf_template"].format(
            extracted=extracted_value,
            encompass=encompass_value,
            source_doc=source_doc
        )
    
    # Generic PTF
    if custom_message:
        return f"PTF - {custom_message}"
    
    return f"PTF - Discrepancy on {field_name}: Document shows '{extracted_value}', Encompass shows '{encompass_value}'. Verify with source document ({source_doc})."


# ============================================================================
# SPECIAL RULES
# ============================================================================

TRUST_PTF_TEMPLATE = """PTF - TRUST Revocable Rider - Title Company to update Settlor(s) information on Trust rider (Section C) prior to recording."""

FHA_92900A_MISSING_PAGE3_PTF = """PTF - Missing Signed Page-3 of Final 92900-A for FHA file. Obtain signed copy."""

HOI_RENEWAL_PTF_TEMPLATE = """PTF - Current Year HOI Policy is expiring within 2 Months of First Payment date. Expiration Date of Current policy is: {expiration_date}"""


def should_ignore_discrepancy(
    field_id: str,
    source_doc: str,
    loan_type: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Check if discrepancy should be ignored per SOP acceptable variances
    
    Returns:
        (should_ignore, reason)
    """
    # Middle initial differences on certain docs
    if field_id in ["4001", "4005"] and source_doc in ["Contract", "Appraisal", "HOI Policy"]:
        return True, "Middle initials acceptable to omit on third-party docs"
    
    # Co-Borrower on VA appraisal
    if field_id in ["4004", "4005", "4006"] and source_doc == "Appraisal" and loan_type == "VA":
        return True, "VA appraisals only require veteran borrower name"
    
    return False, None


# ============================================================================
# INSURANCE VALIDATION RULES
# ============================================================================

def validate_insurance_coverage(
    dwelling_coverage: float,
    loan_amount: float
) -> Tuple[bool, Optional[str]]:
    """
    Check if dwelling coverage meets requirements
    
    Returns:
        (is_valid, error_message)
    """
    if dwelling_coverage < loan_amount:
        return False, f"HARD STOP - Insufficient Dwelling Coverage: ${dwelling_coverage:,.2f} < Loan Amount ${loan_amount:,.2f}. Request updated HOI policy."
    
    return True, None


REQUIRED_MORTGAGEE_CLAUSE = "ALL WESTERN MORTGAGE, INC."


def validate_mortgagee_clause(mortgagee: str) -> Tuple[bool, Optional[str]]:
    """
    Verify mortgagee clause is correct
    
    Returns:
        (is_valid, error_or_ptf)
    """
    if not mortgagee:
        return False, "PTF - Mortgagee Clause missing on HOI policy. Must be 'ALL WESTERN MORTGAGE, INC.'"
    
    if REQUIRED_MORTGAGEE_CLAUSE.lower() not in mortgagee.lower():
        return False, f"PTF - Mortgagee Clause incorrect: Found '{mortgagee}', should be '{REQUIRED_MORTGAGEE_CLAUSE}'"
    
    return True, None

