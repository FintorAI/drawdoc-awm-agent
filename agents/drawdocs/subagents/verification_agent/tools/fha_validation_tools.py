"""
FHA Loan Validation Tools.

Implements SOP Steps 11-12:
- HUD 92900ALT FHA Loan Transmittal validation
- FHA Management - Refi Authorization validation

Per SOP Steps 11-12 - FHA-specific forms.
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

class FHAFields:
    """Encompass field IDs for FHA validation."""
    
    # HUD 92900ALT FHA Loan Transmittal (Step 11)
    FHA_CASE_NUMBER = "1040"  # FHA Case # (Agency Case #)
    SOA = "1039"  # SOA (Section of Act)
    CASE_ASSIGNED_DATE = "3042"  # Case # Assigned Date
    
    # FHA Management - Refi Authorization (Step 12)
    REFI_AUTHORIZATION_BY = "3080"  # Refi Authorization "By" field (if filled, refi is authorized)
    MIP_REFUND_AMOUNT = "1134"  # MI Premium Refund (MIP Refund amount)
    
    # ADP Code - not yet mapped (can add later)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def parse_date(date_str: Any) -> Optional[datetime]:
    """Parse date string to datetime."""
    if not date_str or date_str == "":
        return None
    try:
        if isinstance(date_str, datetime):
            return date_str
        # Try common date formats
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M:%S"]:
            try:
                return datetime.strptime(str(date_str), fmt)
            except ValueError:
                continue
        return None
    except Exception:
        return None


def is_fha_refinance(loan_context: Dict[str, Any]) -> bool:
    """Check if loan is FHA Refinance."""
    loan_purpose = loan_context.get("loan_purpose", "").upper()
    return "REFI" in loan_purpose or "REFINANCE" in loan_purpose


# =============================================================================
# MAIN VALIDATION FUNCTION
# =============================================================================

def validate_fha_loan(loan_id: str) -> Dict[str, Any]:
    """
    Comprehensive FHA loan validation.
    
    Per SOP Steps 11-12:
    1. Verify FHA Case Assignment (Case#, Date, SOA)
    2. Verify Refi Authorization (for FHA Refinance)
    3. Verify MIP Refund (for FHA Refinance, must be positive, based on FUNDING date)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results
    """
    logger.info(f"[FHA VALIDATION] Starting FHA validation for loan {loan_id}")
    
    result = {
        "status": "in_progress",
        "loan_id": loan_id,
        "loan_type": "FHA",
        "is_refinance": False,
        "case_assignment": None,
        "refi_authorization": None,
        "mip_refund": None,
        "all_checks_passed": False,
        "violations": [],
        "warnings": [],
        "details": []
    }
    
    try:
        # Get loan context
        logger.info("[FHA VALIDATION] Reading loan context...")
        loan_context = get_loan_context(loan_id, include_milestones=False)
        
        loan_type = loan_context.get("loan_type", "").upper()
        if "FHA" not in loan_type:
            result["status"] = "not_fha_loan"
            result["details"].append(f"Loan type is '{loan_type}' (not FHA)")
            logger.warning(f"[FHA VALIDATION] Loan is not FHA type: {loan_type}")
            return result
        
        # Check if refinance
        is_refi = is_fha_refinance(loan_context)
        result["is_refinance"] = is_refi
        
        # Read FHA fields
        logger.info("[FHA VALIDATION] Reading FHA-specific fields...")
        fields = read_fields(loan_id, [
            FHAFields.FHA_CASE_NUMBER,
            FHAFields.SOA,
            FHAFields.CASE_ASSIGNED_DATE,
            FHAFields.REFI_AUTHORIZATION_BY,
            FHAFields.MIP_REFUND_AMOUNT,
        ])
        
        # =====================================================================
        # STEP 11: FHA CASE ASSIGNMENT VALIDATION
        # =====================================================================
        logger.info("\n[FHA VALIDATION] Step 11: Validating FHA Case Assignment...")
        case_assignment = validate_fha_case_assignment(fields)
        result["case_assignment"] = case_assignment
        
        if not case_assignment["passed"]:
            result["violations"].append({
                "type": "PTF",
                "severity": "HIGH",
                "category": "FHA Case Assignment",
                "message": case_assignment["message"],
                "action_required": "Verify FHA Case Assignment document and update Case#, Date, and SOA",
                "fields_affected": [
                    FHAFields.FHA_CASE_NUMBER,
                    FHAFields.CASE_ASSIGNED_DATE,
                    FHAFields.SOA
                ],
                "sop_reference": "Step 11 - HUD 92900ALT FHA Loan Transmittal"
            })
            logger.warning(f"[FHA VALIDATION] ⚠️  Case Assignment: {case_assignment['message']}")
        else:
            logger.info(f"[FHA VALIDATION] ✅ Case Assignment: {case_assignment['message']}")
        
        # =====================================================================
        # STEP 12: REFI AUTHORIZATION & MIP REFUND (FHA Refinance Only)
        # =====================================================================
        if is_refi:
            logger.info("\n[FHA VALIDATION] Step 12: Validating Refi Authorization (FHA Refinance)...")
            refi_auth = validate_refi_authorization(fields)
            result["refi_authorization"] = refi_auth
            
            if not refi_auth["passed"]:
                result["violations"].append({
                    "type": "PTF",
                    "severity": "HIGH",
                    "category": "FHA Refi Authorization",
                    "message": refi_auth["message"],
                    "action_required": "Verify Refinance Authorization document and update Refi Authorization",
                    "fields_affected": [FHAFields.REFI_AUTHORIZATION_BY],
                    "sop_reference": "Step 12 - FHA Management - Refi Authorization"
                })
                logger.warning(f"[FHA VALIDATION] ⚠️  Refi Authorization: {refi_auth['message']}")
            else:
                logger.info(f"[FHA VALIDATION] ✅ Refi Authorization: {refi_auth['message']}")
            
            logger.info("\n[FHA VALIDATION] Step 12: Validating MIP Refund (FHA Refinance)...")
            mip_refund = validate_mip_refund(fields, loan_context)
            result["mip_refund"] = mip_refund
            
            if not mip_refund["passed"]:
                result["violations"].append({
                    "type": "PTF",
                    "severity": "HIGH",
                    "category": "FHA MIP Refund",
                    "message": mip_refund["message"],
                    "action_required": mip_refund.get("action_required", "Verify MIP Refund amount on Refinance Authorization document"),
                    "fields_affected": [FHAFields.MIP_REFUND_AMOUNT],
                    "sop_reference": "Step 12 - FHA Management - Refi Authorization"
                })
                logger.warning(f"[FHA VALIDATION] ⚠️  MIP Refund: {mip_refund['message']}")
            else:
                logger.info(f"[FHA VALIDATION] ✅ MIP Refund: {mip_refund['message']}")
        else:
            logger.info("[FHA VALIDATION] Purchase loan - skipping Refi Authorization and MIP Refund checks")
            result["refi_authorization"] = {"status": "not_applicable", "message": "Purchase loan - Refi Authorization not required"}
            result["mip_refund"] = {"status": "not_applicable", "message": "Purchase loan - MIP Refund not applicable"}
        
        # =====================================================================
        # DETERMINE OVERALL STATUS
        # =====================================================================
        all_passed = case_assignment["passed"]
        if is_refi:
            all_passed = all_passed and refi_auth["passed"] and mip_refund["passed"]
        
        result["all_checks_passed"] = all_passed
        
        if all_passed:
            result["status"] = "all_checks_passed"
            logger.info("\n" + "="*80)
            logger.info("[FHA VALIDATION] ✅ ALL FHA VALIDATIONS PASSED")
            logger.info("="*80)
        else:
            result["status"] = "violations_found"
            logger.warning("\n" + "="*80)
            logger.warning(f"[FHA VALIDATION] ⚠️  Found {len(result['violations'])} violations")
            logger.warning("="*80)
        
        # Add summary details
        result["details"].append(f"FHA Case #: {fields.get(FHAFields.FHA_CASE_NUMBER, 'Not Found')}")
        result["details"].append(f"Case Assigned Date: {fields.get(FHAFields.CASE_ASSIGNED_DATE, 'Not Found')}")
        result["details"].append(f"SOA: {fields.get(FHAFields.SOA, 'Not Found')}")
        if is_refi:
            result["details"].append(f"Refi Authorization: {'Authorized' if refi_auth.get('passed') else 'Not Authorized'}")
            result["details"].append(f"MIP Refund: ${fields.get(FHAFields.MIP_REFUND_AMOUNT, 0)}")
        result["details"].append(f"Violations: {len(result['violations'])}")
        
        return result
        
    except Exception as e:
        logger.error(f"[FHA VALIDATION] Error during validation: {e}", exc_info=True)
        result["status"] = "error"
        result["details"].append(f"Validation error: {str(e)}")
        return result


# =============================================================================
# INDIVIDUAL VALIDATORS
# =============================================================================

def validate_fha_case_assignment(fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate FHA Case Assignment.
    
    Per SOP Step 11:
    - FHA Case# must be populated
    - Case Assigned Date must be populated
    - SOA (Section of Act) must be populated
    
    Args:
        fields: Field values from read_fields
        
    Returns:
        Dictionary with validation result
    """
    result = {
        "passed": False,
        "message": "",
        "details": {}
    }
    
    fha_case = fields.get(FHAFields.FHA_CASE_NUMBER, "")
    case_date = fields.get(FHAFields.CASE_ASSIGNED_DATE, "")
    soa = fields.get(FHAFields.SOA, "")
    
    result["details"]["fha_case_number"] = fha_case
    result["details"]["case_assigned_date"] = case_date
    result["details"]["soa"] = soa
    
    missing_fields = []
    if not fha_case or str(fha_case).strip() == "":
        missing_fields.append("FHA Case #")
    if not case_date or str(case_date).strip() == "":
        missing_fields.append("Case Assigned Date")
    if not soa or str(soa).strip() == "":
        missing_fields.append("SOA")
    
    if missing_fields:
        result["passed"] = False
        result["message"] = f"Missing FHA Case Assignment fields: {', '.join(missing_fields)}"
    else:
        result["passed"] = True
        result["message"] = f"FHA Case Assignment complete (Case#: {fha_case}, Date: {case_date}, SOA: {soa})"
    
    return result


def validate_refi_authorization(fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate FHA Refi Authorization.
    
    Per SOP Step 12:
    - Refi Authorization "By" field must be filled (indicates authorization)
    
    Args:
        fields: Field values from read_fields
        
    Returns:
        Dictionary with validation result
    """
    result = {
        "passed": False,
        "message": "",
        "details": {}
    }
    
    refi_by = fields.get(FHAFields.REFI_AUTHORIZATION_BY, "")
    
    result["details"]["refi_authorization_by"] = refi_by
    
    if not refi_by or str(refi_by).strip() == "" or str(refi_by) == "0":
        result["passed"] = False
        result["message"] = "Refi Authorization not found - 'By' field is empty"
    else:
        result["passed"] = True
        result["message"] = f"Refi Authorization confirmed (By: {refi_by})"
    
    return result


def validate_mip_refund(fields: Dict[str, Any], loan_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate FHA MIP Refund.
    
    Per SOP Step 12:
    - MIP Refund must be positive (+)
    - MIP Refund is based on FUNDING date (not NOTE date)
    - MIP Refund should match Refinance Authorization document
    
    Args:
        fields: Field values from read_fields
        loan_context: Loan context for funding date
        
    Returns:
        Dictionary with validation result
    """
    result = {
        "passed": False,
        "message": "",
        "details": {}
    }
    
    mip_refund = fields.get(FHAFields.MIP_REFUND_AMOUNT, "")
    funding_date = loan_context.get("closing_date", "")  # Using closing date as proxy for funding date
    
    result["details"]["mip_refund_amount"] = mip_refund
    result["details"]["funding_date"] = funding_date
    
    # Parse MIP Refund amount
    try:
        if mip_refund and str(mip_refund).strip() != "":
            mip_amount = float(str(mip_refund).replace(",", "").replace("$", ""))
        else:
            mip_amount = 0
    except (ValueError, TypeError):
        mip_amount = 0
    
    result["details"]["mip_amount_parsed"] = mip_amount
    
    if mip_amount == 0:
        result["passed"] = False
        result["message"] = "MIP Refund amount is missing or zero"
        result["action_required"] = "Verify MIP Refund on Refinance Authorization document and update if applicable"
    elif mip_amount < 0:
        result["passed"] = False
        result["message"] = f"MIP Refund is negative ({mip_amount}) - must be positive (+)"
        result["action_required"] = "MIP Refund must be entered as positive amount (system considers minus by field name)"
    else:
        result["passed"] = True
        result["message"] = f"MIP Refund validated: ${mip_amount:,.2f} (based on FUNDING date, not NOTE date)"
        result["details"]["note"] = "MIP Refund is based on FUNDING date per SOP Step 12"
    
    return result


# =============================================================================
# EXPORT TOOLS
# =============================================================================

__all__ = [
    "validate_fha_loan",
    "validate_fha_case_assignment",
    "validate_refi_authorization",
    "validate_mip_refund",
]



