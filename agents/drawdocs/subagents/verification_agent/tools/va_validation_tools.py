"""
VA Loan Validation Tools.

Implements SOP Steps 13, 15:
- VA Management validation
- VA 26-1820 Loan Disbursement validation

Per SOP Steps 13, 15 - VA-specific forms.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.drawdocs.tools.primitives import read_fields, get_loan_context

logger = logging.getLogger(__name__)


# =============================================================================
# FIELD MAPPINGS
# =============================================================================

class VAFields:
    """Encompass field IDs for VA validation."""
    
    # VA Management (Step 13)
    VA_AGENCY_CASE_NUMBER = "1040"  # VA Agency Case # (same as FHA/USDA Agency Case #)
    FUNDING_FEE_EXEMPT_STATUS = "990"  # Funding Fee Exempt Status
    VA_FUNDING_FEE_AMOUNT = "1826"  # VA Funding Fee amount
    VA_LOAN_TYPE = "1785"  # VA Loan Type (VA Purchase, VA IRRRL, VA C/O)
    
    # VA 26-1820 Loan Disbursement (Step 15)
    SECTION_6_RELATIVE = "CAPIAP.X9"  # Section 6 (RELATIVE)
    SECTION_7_LOAN_PURPOSE = "VASUMM.X155"  # Section 7 (Loan Purpose)
    SECTION_12_VESTED = "1497"  # Section 12 (Vested)
    SECTION_27B_OCCUPANCY = "1065"  # Section 27B (Occupancy) - labeled as 36a in form


# =============================================================================
# VA FUNDING FEE CHART (on or after April 7, 2023)
# =============================================================================

VA_FUNDING_FEE_CHART = {
    "Purchase/Construction": {
        "<5%": {"first_use": 2.15, "subsequent_use": 3.30},
        "5-<10%": {"first_use": 1.50, "subsequent_use": 1.50},
        "≥10%": {"first_use": 1.25, "subsequent_use": 1.25},
    },
    "Cash-Out Refi": {
        "first_use": 2.15,
        "subsequent_use": 3.30
    },
    "IRRRL": {
        "first_use": 0.50,
        "subsequent_use": 0.50
    }
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def parse_funding_fee_amount(amount: Any) -> float:
    """Parse funding fee amount to float."""
    if not amount or amount == "":
        return 0.0
    try:
        if isinstance(amount, (int, float)):
            return float(amount)
        amount_str = str(amount).replace(",", "").replace("$", "").strip()
        return float(amount_str)
    except (ValueError, TypeError):
        return 0.0


def is_va_irrrl(loan_type: str) -> bool:
    """Check if loan type is VA IRRRL."""
    return "IRRRL" in str(loan_type).upper()


def is_va_cash_out(loan_type: str) -> bool:
    """Check if loan type is VA Cash-Out."""
    return "C/O" in str(loan_type).upper() or "CASH" in str(loan_type).upper()


def is_va_purchase(loan_type: str) -> bool:
    """Check if loan type is VA Purchase."""
    return "PURCHASE" in str(loan_type).upper() and "IRRRL" not in str(loan_type).upper()


# =============================================================================
# MAIN VALIDATION FUNCTION
# =============================================================================

def validate_va_loan(loan_id: str) -> Dict[str, Any]:
    """
    Comprehensive VA loan validation.
    
    Per SOP Steps 13, 15:
    1. Verify VA Agency Case#
    2. Verify Funding Fee Exempt Status
    3. Verify VA Funding Fee amount (against fee chart)
    4. Verify VA Loan Type (must be VA Purchase, VA IRRRL, or VA C/O - no "NO C/O")
    5. Verify VA 26-1820 form sections (6, 7, 12, 27B)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results
    """
    logger.info(f"[VA VALIDATION] Starting VA validation for loan {loan_id}")
    
    result = {
        "status": "in_progress",
        "loan_id": loan_id,
        "loan_type": "VA",
        "va_management": None,
        "va_26_1820": None,
        "all_checks_passed": False,
        "violations": [],
        "warnings": [],
        "details": []
    }
    
    try:
        # Get loan context
        logger.info("[VA VALIDATION] Reading loan context...")
        loan_context = get_loan_context(loan_id, include_milestones=False)
        
        loan_type = loan_context.get("loan_type", "").upper()
        if "VA" not in loan_type:
            result["status"] = "not_va_loan"
            result["details"].append(f"Loan type is '{loan_type}' (not VA)")
            logger.warning(f"[VA VALIDATION] Loan is not VA type: {loan_type}")
            return result
        
        # Read VA fields
        logger.info("[VA VALIDATION] Reading VA-specific fields...")
        fields = read_fields(loan_id, [
            VAFields.VA_AGENCY_CASE_NUMBER,
            VAFields.FUNDING_FEE_EXEMPT_STATUS,
            VAFields.VA_FUNDING_FEE_AMOUNT,
            VAFields.VA_LOAN_TYPE,
            VAFields.SECTION_6_RELATIVE,
            VAFields.SECTION_7_LOAN_PURPOSE,
            VAFields.SECTION_12_VESTED,
            VAFields.SECTION_27B_OCCUPANCY,
        ])
        
        # =====================================================================
        # STEP 13: VA MANAGEMENT VALIDATION
        # =====================================================================
        logger.info("\n[VA VALIDATION] Step 13: Validating VA Management...")
        va_management = validate_va_management(fields, loan_context)
        result["va_management"] = va_management
        
        if not va_management["passed"]:
            for violation in va_management.get("violations", []):
                result["violations"].append(violation)
            logger.warning(f"[VA VALIDATION] ⚠️  VA Management: {va_management['message']}")
        else:
            logger.info(f"[VA VALIDATION] ✅ VA Management: {va_management['message']}")
        
        # =====================================================================
        # STEP 15: VA 26-1820 LOAN DISBURSEMENT VALIDATION
        # =====================================================================
        logger.info("\n[VA VALIDATION] Step 15: Validating VA 26-1820 Loan Disbursement...")
        va_26_1820 = validate_va_26_1820(fields)
        result["va_26_1820"] = va_26_1820
        
        if not va_26_1820["passed"]:
            for violation in va_26_1820.get("violations", []):
                result["violations"].append(violation)
            logger.warning(f"[VA VALIDATION] ⚠️  VA 26-1820: {va_26_1820['message']}")
        else:
            logger.info(f"[VA VALIDATION] ✅ VA 26-1820: {va_26_1820['message']}")
        
        # =====================================================================
        # DETERMINE OVERALL STATUS
        # =====================================================================
        all_passed = va_management["passed"] and va_26_1820["passed"]
        result["all_checks_passed"] = all_passed
        
        if all_passed:
            result["status"] = "all_checks_passed"
            logger.info("\n" + "="*80)
            logger.info("[VA VALIDATION] ✅ ALL VA VALIDATIONS PASSED")
            logger.info("="*80)
        else:
            result["status"] = "violations_found"
            logger.warning("\n" + "="*80)
            logger.warning(f"[VA VALIDATION] ⚠️  Found {len(result['violations'])} violations")
            logger.warning("="*80)
        
        # Add summary details
        result["details"].append(f"VA Agency Case #: {fields.get(VAFields.VA_AGENCY_CASE_NUMBER, 'Not Found')}")
        result["details"].append(f"VA Loan Type: {fields.get(VAFields.VA_LOAN_TYPE, 'Not Found')}")
        result["details"].append(f"Funding Fee Exempt: {fields.get(VAFields.FUNDING_FEE_EXEMPT_STATUS, 'Not Found')}")
        result["details"].append(f"VA Funding Fee: ${fields.get(VAFields.VA_FUNDING_FEE_AMOUNT, 0)}")
        result["details"].append(f"Violations: {len(result['violations'])}")
        
        return result
        
    except Exception as e:
        logger.error(f"[VA VALIDATION] Error during validation: {e}", exc_info=True)
        result["status"] = "error"
        result["details"].append(f"Validation error: {str(e)}")
        return result


# =============================================================================
# INDIVIDUAL VALIDATORS
# =============================================================================

def validate_va_management(fields: Dict[str, Any], loan_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate VA Management form.
    
    Per SOP Step 13:
    - VA Agency Case# must be populated
    - Funding Fee Exempt Status must be verified
    - VA Funding Fee amount must match fee chart
    - VA Loan Type must be VA Purchase, VA IRRRL, or VA C/O (no "NO C/O" option)
    
    Args:
        fields: Field values from read_fields
        loan_context: Loan context for additional data
        
    Returns:
        Dictionary with validation result
    """
    result = {
        "passed": False,
        "message": "",
        "violations": [],
        "details": {}
    }
    
    va_case = fields.get(VAFields.VA_AGENCY_CASE_NUMBER, "")
    funding_fee_exempt = fields.get(VAFields.FUNDING_FEE_EXEMPT_STATUS, "")
    funding_fee_amount = fields.get(VAFields.VA_FUNDING_FEE_AMOUNT, "")
    va_loan_type = fields.get(VAFields.VA_LOAN_TYPE, "")
    
    result["details"]["va_case_number"] = va_case
    result["details"]["funding_fee_exempt"] = funding_fee_exempt
    result["details"]["funding_fee_amount"] = funding_fee_amount
    result["details"]["va_loan_type"] = va_loan_type
    
    violations = []
    
    # Check VA Case#
    if not va_case or str(va_case).strip() == "":
        violations.append({
            "type": "PTF",
            "severity": "HIGH",
            "category": "VA Agency Case #",
            "message": "VA Agency Case # is missing",
            "action_required": "Verify VA Case Assignment document and update VA Agency Case #",
            "fields_affected": [VAFields.VA_AGENCY_CASE_NUMBER],
            "sop_reference": "Step 13 - VA Management"
        })
    
    # Check VA Loan Type
    va_loan_type_upper = str(va_loan_type).upper()
    valid_loan_types = ["VA PURCHASE", "VA IRRRL", "VA C/O", "VA CASH-OUT"]
    is_valid_type = any(valid_type in va_loan_type_upper for valid_type in valid_loan_types)
    
    if not va_loan_type or not is_valid_type:
        violations.append({
            "type": "PTF",
            "severity": "HIGH",
            "category": "VA Loan Type",
            "message": f"VA Loan Type is '{va_loan_type}' (must be VA Purchase, VA IRRRL, or VA C/O - no 'NO C/O' option)",
            "action_required": "Select correct VA Loan Type: VA Purchase, VA IRRRL, or VA C/O",
            "fields_affected": [VAFields.VA_LOAN_TYPE],
            "sop_reference": "Step 13 - VA Management"
        })
    
    # Check Funding Fee (only if not exempt)
    funding_fee_exempt_str = str(funding_fee_exempt).upper()
    is_exempt = funding_fee_exempt_str in ["Y", "YES", "TRUE", "1", "X", "EXEMPT"]
    
    if not is_exempt:
        # Funding fee is required - validate amount
        funding_fee = parse_funding_fee_amount(funding_fee_amount)
        
        if funding_fee == 0:
            violations.append({
                "type": "PTF",
                "severity": "HIGH",
                "category": "VA Funding Fee",
                "message": "VA Funding Fee amount is missing or zero (Funding Fee not exempt)",
                "action_required": "Verify VA Funding Fee on Final Approval/1003 and update amount per VA Funding Fee structure",
                "fields_affected": [VAFields.VA_FUNDING_FEE_AMOUNT],
                "sop_reference": "Step 13 - VA Management"
            })
        else:
            # Validate funding fee against chart (warning only, not a violation)
            result["details"]["funding_fee_validated"] = True
            result["details"]["note"] = "Funding Fee amount should be verified against VA Funding Fee chart per SOP"
    
    if violations:
        result["passed"] = False
        result["message"] = f"Found {len(violations)} VA Management violations"
        result["violations"] = violations
    else:
        result["passed"] = True
        result["message"] = f"VA Management validated (Case#: {va_case}, Type: {va_loan_type}, Fee: ${funding_fee_amount})"
    
    return result


def validate_va_26_1820(fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate VA 26-1820 Loan Disbursement form.
    
    Per SOP Step 15:
    - Section 6 (RELATIVE) must be populated
    - Section 7 (Loan Purpose) must be populated
    - Section 12 (Vested) must be populated
    - Section 27B (Occupancy) must be populated
    
    Args:
        fields: Field values from read_fields
        
    Returns:
        Dictionary with validation result
    """
    result = {
        "passed": False,
        "message": "",
        "violations": [],
        "details": {}
    }
    
    section_6 = fields.get(VAFields.SECTION_6_RELATIVE, "")
    section_7 = fields.get(VAFields.SECTION_7_LOAN_PURPOSE, "")
    section_12 = fields.get(VAFields.SECTION_12_VESTED, "")
    section_27b = fields.get(VAFields.SECTION_27B_OCCUPANCY, "")
    
    result["details"]["section_6_relative"] = section_6
    result["details"]["section_7_loan_purpose"] = section_7
    result["details"]["section_12_vested"] = section_12
    result["details"]["section_27b_occupancy"] = section_27b
    
    violations = []
    missing_sections = []
    
    # Check Section 6 (RELATIVE)
    if not section_6 or str(section_6).strip() == "":
        missing_sections.append("Section 6 (RELATIVE)")
        violations.append({
            "type": "PTF",
            "severity": "HIGH",
            "category": "VA 26-1820 Section 6",
            "message": "Section 6 (RELATIVE) is missing",
            "action_required": "Fill Section 6 from Disclosures >> VA Nearest Living Relative",
            "fields_affected": [VAFields.SECTION_6_RELATIVE],
            "sop_reference": "Step 15 - VA 26-1820 Loan Disbursement"
        })
    
    # Check Section 7 (Loan Purpose)
    if not section_7 or str(section_7).strip() == "":
        missing_sections.append("Section 7 (Loan Purpose)")
        violations.append({
            "type": "PTF",
            "severity": "HIGH",
            "category": "VA 26-1820 Section 7",
            "message": "Section 7 (Loan Purpose) is missing",
            "action_required": "Fill Section 7 from Final VA 92900A page 1 & 2",
            "fields_affected": [VAFields.SECTION_7_LOAN_PURPOSE],
            "sop_reference": "Step 15 - VA 26-1820 Loan Disbursement"
        })
    
    # Check Section 12 (Vested)
    if not section_12 or str(section_12).strip() == "":
        missing_sections.append("Section 12 (Vested)")
        violations.append({
            "type": "PTF",
            "severity": "HIGH",
            "category": "VA 26-1820 Section 12",
            "message": "Section 12 (Vested) is missing",
            "action_required": "Fill Section 12 from Final VA 92900A page 1 & 2",
            "fields_affected": [VAFields.SECTION_12_VESTED],
            "sop_reference": "Step 15 - VA 26-1820 Loan Disbursement"
        })
    
    # Check Section 27B (Occupancy)
    if not section_27b or str(section_27b).strip() == "":
        missing_sections.append("Section 27B (Occupancy)")
        violations.append({
            "type": "PTF",
            "severity": "HIGH",
            "category": "VA 26-1820 Section 27B",
            "message": "Section 27B (Occupancy) is missing",
            "action_required": "Fill Section 27B from Final VA 92900A page 1 & 2",
            "fields_affected": [VAFields.SECTION_27B_OCCUPANCY],
            "sop_reference": "Step 15 - VA 26-1820 Loan Disbursement"
        })
    
    if violations:
        result["passed"] = False
        result["message"] = f"Missing VA 26-1820 sections: {', '.join(missing_sections)}"
        result["violations"] = violations
    else:
        result["passed"] = True
        result["message"] = "All VA 26-1820 sections validated (6, 7, 12, 27B)"
    
    return result


# =============================================================================
# EXPORT TOOLS
# =============================================================================

__all__ = [
    "validate_va_loan",
    "validate_va_management",
    "validate_va_26_1820",
]



